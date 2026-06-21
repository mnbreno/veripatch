-- VeriPatch wxLua GUI IPC client
-- Communicates with Python backend via line-delimited JSON-RPC over stdio

local ipc = {}

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

local function encode_request(request)
  local ok, cjson = pcall(require, "cjson")
  if ok then
    return cjson.encode(request) .. "\n"
  end
  ok, dkjson = pcall(require, "dkjson")
  if ok then
    return dkjson.encode(request) .. "\n"
  end
  return json_encode(request) .. "\n"
end

local function backend_command(self)
  local cmd_parts = { self.cmd }
  for _, arg in ipairs(self.args) do
    table.insert(cmd_parts, arg)
  end
  return table.concat(cmd_parts, " ")
end

function ipc.new(backend_cmd, backend_args, backend_cwd)
  local self = {
    cmd = backend_cmd or "python",
    args = backend_args or {"-m", "veripatch"},
    cwd = backend_cwd,
    request_id = 0,
  }
  setmetatable(self, { __index = ipc })
  return self
end

function ipc:start()
  return true
end

function ipc:close()
  return true
end

function ipc:call(method, params, on_progress)
  self.request_id = self.request_id + 1
  local request = {
    jsonrpc = "2.0",
    method = method,
    params = params or {},
    id = self.request_id,
  }
  local payload = encode_request(request)
  local full_cmd = backend_command(self)
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
