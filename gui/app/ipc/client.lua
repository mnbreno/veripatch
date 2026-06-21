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
  -- Minimal decoder for IPC responses (stdlib-only fallback)
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

function ipc.new(backend_cmd, backend_args, backend_cwd)
  local self = {
    cmd = backend_cmd or "python",
    args = backend_args or {"-m", "veripatch"},
    cwd = backend_cwd,
    proc = nil,
    request_id = 0,
  }
  setmetatable(self, { __index = ipc })
  return self
end

function ipc:start()
  if self.proc then
    return true
  end
  local cmd_line = self.cmd
  for _, arg in ipairs(self.args) do
    cmd_line = cmd_line .. " " .. arg
  end
  local ok, proc = pcall(io.popen, cmd_line .. stderr_redirect(), "w")
  if not ok or not proc then
    return false, "Failed to start backend process"
  end
  self.proc = proc
  return true
end

function ipc:close()
  if self.proc then
    self.proc:close()
    self.proc = nil
  end
end

function ipc:call(method, params)
  self.request_id = self.request_id + 1
  local request = {
    jsonrpc = "2.0",
    method = method,
    params = params or {},
    id = self.request_id,
  }

  local ok, cjson = pcall(require, "cjson")
  local payload
  if ok then
    payload = cjson.encode(request) .. "\n"
  else
    ok, dkjson = pcall(require, "dkjson")
    if ok then
      payload = dkjson.encode(request) .. "\n"
    else
      payload = json_encode(request) .. "\n"
    end
  end

  -- Use subprocess for request/response (reliable one-shot IPC)
  local cmd_parts = { self.cmd }
  for _, arg in ipairs(self.args) do
    table.insert(cmd_parts, arg)
  end

  local full_cmd = table.concat(cmd_parts, " ")
  local handle = io.popen(
    'echo ' .. payload:gsub('"', '\\"') .. ' | ' .. full_cmd .. stderr_redirect(),
    "r"
  )
  if not handle then
    return nil, "Failed to invoke backend"
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
