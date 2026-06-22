-- VeriPatch wxLua GUI IPC client
-- Talks to the Python backend over TCP (preferred) or stdio one-shot fallback.

local ipc = {}
local win_silent = require("app.win_silent")
local wx_module = nil

local function get_wx()
  if wx_module then
    return wx_module
  end
  local ok, wx = pcall(require, "wx")
  if ok then
    wx_module = wx
  end
  return wx_module
end

local function shell_quote(value)
  local text = tostring(value)
  if text:find('[%s&|<>^"]') or text == "" then
    return '"' .. text:gsub('"', '""') .. '"'
  end
  return text
end

local function stderr_redirect()
  if package.config:sub(1, 1) == "\\" then
    return " 2>nul"
  end
  return " 2>/dev/null"
end

local function json_encode(value)
  if type(value) ~= "table" then
    error("json_encode expects a table")
  end
  local parts = {}
  for k, v in pairs(value) do
    local key
    if type(k) == "number" then
      key = tostring(k)
    else
      key = string.format("%q", k)
    end
    local val
    if type(v) == "string" then
      val = string.format("%q", v)
    elseif type(v) == "number" or type(v) == "boolean" then
      val = tostring(v)
    elseif type(v) == "table" then
      val = json_encode(v)
    else
      val = "null"
    end
    table.insert(parts, key .. ":" .. val)
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

local function json_decode_simple(line)
  local ok, cjson = pcall(require, "cjson")
  if ok then
    return cjson.decode(line)
  end
  ok, dkjson = pcall(require, "dkjson")
  if ok then
    return dkjson.decode(line)
  end
  error("No JSON library available (cjson or dkjson required for GUI IPC)")
end

local function encode_json(value)
  local ok, cjson = pcall(require, "cjson")
  if ok then
    return cjson.encode(value)
  end
  ok, dkjson = pcall(require, "dkjson")
  if ok then
    return dkjson.encode(value)
  end
  return json_encode(value)
end

local function encode_request(request)
  return encode_json(request) .. "\n"
end

local function encode_params(params)
  return encode_json(params or {})
end

local function normalize_path(path)
  return win_silent.normalize_path(path, get_wx())
end

local function resolve_ipc_port(cwd)
  local env_port = os.getenv("VERIPATCH_IPC_PORT")
  if env_port and env_port ~= "" then
    return tonumber(env_port)
  end
  local port_file = os.getenv("VERIPATCH_IPC_PORT_FILE") or ".veripatch/ipc.port"
  if cwd and cwd ~= "" then
    if cwd:sub(-1) == "/" or cwd:sub(-1) == "\\" then
      port_file = cwd .. port_file
    else
      port_file = cwd .. "/" .. port_file
    end
  end
  local handle = io.open(port_file, "r")
  if not handle then
    return nil
  end
  local port = tonumber(handle:read("*l"))
  handle:close()
  return port
end

local function sleep_ms(ms)
  win_silent.sleep_ms(ms, get_wx())
end

local function write_ipc_port(cwd, port)
  if not cwd or not port then
    return
  end
  local port_file = os.getenv("VERIPATCH_IPC_PORT_FILE") or ".veripatch/ipc.port"
  local sep = package.config:sub(1, 1)
  if cwd:sub(-1) ~= "/" and cwd:sub(-1) ~= "\\" then
    port_file = cwd .. sep .. port_file
  else
    port_file = cwd .. port_file
  end
  local dir = port_file:match("^(.*)[/\\][^/\\]+$")
  if dir then
    win_silent.mkdir_p(dir, get_wx())
  end
  local handle = io.open(port_file, "w")
  if not handle then
    return
  end
  handle:write(tostring(port))
  handle:close()
end

local function backend_prefix(self)
  if not self.cwd or self.cwd == "" then
    return ""
  end
  if package.config:sub(1, 1) == "\\" then
    return "cd /d " .. shell_quote(self.cwd) .. " && "
  end
  return "cd " .. shell_quote(self.cwd) .. " && "
end

local function backend_command(self)
  local cmd_parts = { shell_quote(self.cmd) }
  for _, arg in ipairs(self.args) do
    table.insert(cmd_parts, shell_quote(arg))
  end
  return table.concat(cmd_parts, " ")
end

local function socket_read_some(client)
  local raw = client:Read(4096)
  if not raw or raw == "" then
    return ""
  end

  local count = #raw
  if client.LastCount then
    local ok, read_count = pcall(function()
      return client:LastCount()
    end)
    if ok and read_count and read_count > 0 and read_count <= count then
      count = read_count
    end
  end

  return raw:sub(1, count):gsub("%z", "")
end

local function pop_json_line(buffer)
  buffer = buffer:gsub("^[\r\n%s]+", "")
  if buffer == "" then
    return nil, ""
  end

  local start = buffer:find("{", 1, true)
  if not start then
    return nil, buffer
  end
  buffer = buffer:sub(start)

  local line_end = buffer:find("\n", 1, true)
  if not line_end then
    return nil, buffer
  end

  local line = buffer:sub(1, line_end - 1):gsub("%z", "")
  local rest = buffer:sub(line_end + 1)
  return line, rest
end

local function socket_read_line(client, buffer)
  buffer = buffer or ""

  while true do
    local line
    line, buffer = pop_json_line(buffer)
    if line and line ~= "" then
      return line, buffer
    end

    local chunk = socket_read_some(client)
    if chunk == "" then
      if client.WaitForRead then
        local ok = pcall(function()
          client:WaitForRead(5, 0)
        end)
        if ok then
          chunk = socket_read_some(client)
        end
      end
      if chunk == "" then
        return nil, buffer
      end
    end
    buffer = buffer .. chunk
  end
end

local function socket_connect(host, port, timeout_sec)
  local wx = require("wx")
  local addr = wx.wxIPV4address()
  addr:Hostname(host)
  addr:Service(port)

  local client = wx.wxSocketClient()
  client:SetTimeout(timeout_sec or 30)
  if not client:Connect(addr) then
    client:Close()
    return nil, "Failed to connect to backend on " .. host .. ":" .. port
  end
  return client
end

local function socket_send_request(client, request_id, method, params)
  local payload = encode_json({
    jsonrpc = "2.0",
    method = method,
    params = params or {},
    id = request_id,
  }) .. "\n"
  client:Write(payload, #payload)
end

function ipc.new(backend_cmd, backend_args, backend_cwd)
  local cwd = normalize_path(backend_cwd)
  local port = resolve_ipc_port(cwd)
    or tonumber(os.getenv("VERIPATCH_IPC_PORT"))
    or 8765
  local self = {
    cmd = backend_cmd or "python",
    args = backend_args or {"-m", "veripatch"},
    cwd = cwd,
    request_id = 0,
    port = port,
    host = os.getenv("VERIPATCH_IPC_HOST") or "127.0.0.1",
    use_rpc = true,
    _backend_started = false,
  }
  setmetatable(self, { __index = ipc })
  return self
end

function ipc:_try_connect()
  local client, _err = socket_connect(self.host, self.port, 2)
  if not client then
    return false
  end
  client:Close()
  return true
end

function ipc:_ping_backend()
  local client, _err = socket_connect(self.host, self.port, 2)
  if not client then
    return false
  end

  socket_send_request(client, 1, "ping", {})
  local line = socket_read_line(client, "")
  client:Close()
  if not line or line == "" then
    return false
  end

  local ok, response = pcall(json_decode_simple, line)
  return ok
    and type(response) == "table"
    and type(response.result) == "table"
    and response.result.status == "ok"
end

function ipc:_spawn_backend()
  if os.getenv("VERIPATCH_BACKEND_MANAGED") == "1" then
    for _ = 1, 20 do
      sleep_ms(300)
      if self:_ping_backend() then
        self.use_rpc = true
        return true
      end
    end
    return false
  end

  if package.config:sub(1, 1) == "\\" and self.cwd and self.cwd ~= "" then
    local project_root = self.cwd:match("^(.*)[/\\][^/\\]+$")
    if project_root then
      if win_silent.spawn_backend(project_root, self.port, self.cmd) then
        write_ipc_port(self.cwd, self.port)
        for _ = 1, 10 do
          sleep_ms(300)
          if self:_ping_backend() then
            self.use_rpc = true
            return true
          end
        end
        return false
      end
    end
  end

  if package.config:sub(1, 1) == "\\" then
    win_silent.spawn_pythonw_backend(self.cwd, self.cmd, self.args, self.port)
  else
    local cmd_parts = { shell_quote(self.cmd) }
    for _, arg in ipairs(self.args) do
      table.insert(cmd_parts, shell_quote(arg))
    end
    table.insert(cmd_parts, "--port")
    table.insert(cmd_parts, tostring(self.port))
    table.insert(cmd_parts, "--write-port-file")
    os.execute(backend_prefix(self) .. table.concat(cmd_parts, " ") .. " >/dev/null 2>&1 &")
  end
  write_ipc_port(self.cwd, self.port)

  for _ = 1, 10 do
    sleep_ms(300)
    if self:_ping_backend() then
      self.use_rpc = true
      return true
    end
  end
  return false
end

function ipc:ensure_backend()
  if self._backend_ready then
    return true
  end
  if self:_ping_backend() then
    self._backend_ready = true
    self.use_rpc = true
    return true
  end
  if self._spawn_attempted then
    return false
  end
  self._spawn_attempted = true
  if self:_spawn_backend() then
    self._backend_ready = true
    return true
  end
  self.use_rpc = false
  return false
end

function ipc:start()
  return self:ensure_backend()
end

function ipc:reset_backend_session()
  self._backend_ready = false
  self._spawn_attempted = false
end

function ipc:mark_backend_managed()
  self._spawn_attempted = true
end

function ipc:close()
  return true
end

function ipc:_call_socket(method, params, on_progress)
  local client, connect_err = socket_connect(self.host, self.port, 30)
  if not client then
    return nil, connect_err
  end

  self.request_id = self.request_id + 1
  local request_id = self.request_id
  socket_send_request(client, request_id, method, params)

  local buffer = ""
  while true do
    local line
    line, buffer = socket_read_line(client, buffer)
    if not line or line == "" then
      client:Close()
      return nil, "Empty response from backend"
    end

    local ok_decode, response = pcall(json_decode_simple, line)
    if not ok_decode or type(response) ~= "table" then
      -- Skip malformed socket chunks and keep reading.
    elseif response.method == "apply_progress" then
      if on_progress then
        on_progress(response.params and response.params.line or "")
      end
    elseif response.id == request_id or response.result ~= nil or response.error ~= nil then
      client:Close()
      if response.error then
        return nil, response.error.message or "RPC error"
      end
      return response.result
    end
  end
end

function ipc:_call_rpc(method, params, on_progress)
  local params_json = encode_params(params)
  local params_file = os.tmpname()
  local params_handle = io.open(params_file, "w")
  if not params_handle then
    return nil, "Failed to create RPC params file"
  end
  params_handle:write(params_json)
  params_handle:close()

  local rpc_args = {
    "rpc",
    method,
    "--params-file",
    params_file,
    "--host",
    self.host,
    "--port",
    tostring(self.port),
  }
  if method == "apply_updates_stream" then
    table.insert(rpc_args, "--stream-json")
  end

  local cmd_parts = { shell_quote(self.cmd) }
  for _, arg in ipairs(self.args) do
    table.insert(cmd_parts, shell_quote(arg))
  end
  for _, arg in ipairs(rpc_args) do
    table.insert(cmd_parts, shell_quote(arg))
  end
  local full_cmd = backend_prefix(self) .. table.concat(cmd_parts, " ")

  local handle = io.popen(full_cmd .. stderr_redirect(), "r")
  if not handle then
    os.remove(params_file)
    return nil, "Failed to invoke RPC bridge"
  end

  if method == "apply_updates_stream" then
    while true do
      local line = handle:read("*l")
      if not line then
        handle:close()
        os.remove(params_file)
        return nil, "Empty response from backend"
      end
      local response = json_decode_simple(line)
      if response.method == "apply_progress" and on_progress then
        on_progress(response.params.line)
      elseif response.result ~= nil or response.error ~= nil then
        handle:close()
        os.remove(params_file)
        if response.error then
          return nil, response.error.message or "RPC error"
        end
        return response.result
      end
    end
  end

  local line = handle:read("*l")
  handle:close()
  os.remove(params_file)
  if not line then
    return nil, "Empty response from backend"
  end

  local response = json_decode_simple(line)
  if response.error then
    return nil, response.error.message or "RPC error"
  end
  if response.result ~= nil then
    return response.result
  end
  return response
end

function ipc:call(method, params, on_progress)
  if self.use_rpc then
    if not self:ensure_backend() then
      self.use_rpc = false
    end
  end

  if self.use_rpc then
    local ok, result, err = pcall(function()
      return self:_call_socket(method, params, on_progress)
    end)
    if ok then
      if result ~= nil or err ~= nil then
        return result, err
      end
      return nil, "Invalid response from backend"
    end
    return nil, "Backend connection failed: " .. tostring(result)
  end

  self.request_id = self.request_id + 1
  local request = {
    jsonrpc = "2.0",
    method = method,
    params = params or {},
    id = self.request_id,
  }
  local payload = encode_request(request)
  local full_cmd = backend_prefix(self) .. backend_command(self)
  local handle = io.popen(
    'echo ' .. payload:gsub('"', '\\"') .. ' | ' .. full_cmd .. stderr_redirect(),
    "r"
  )
  if not handle then
    return nil, "Failed to invoke backend"
  end

  if method == "apply_updates_stream" then
    while true do
      local line = handle:read("*l")
      if not line then
        handle:close()
        return nil, "Empty response from backend"
      end
      local response = json_decode_simple(line)
      if response.method == "apply_progress" and on_progress then
        on_progress(response.params.line)
      elseif response.id == request.id then
        handle:close()
        if response.error then
          return nil, response.error.message or "RPC error"
        end
        return response.result
      end
    end
  end

  local line = handle:read("*l")
  handle:close()
  if not line then
    return nil, "Empty response from backend"
  end

  local response = json_decode_simple(line)
  if response.error then
    return nil, response.error.message or "RPC error"
  end
  return response.result
end

return ipc
