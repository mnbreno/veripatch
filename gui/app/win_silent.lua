-- Windows helpers to run shell actions without visible console windows.

local M = {}

function M.is_windows()
  return package.config:sub(1, 1) == "\\"
end

function M.normalize_path(path, wx)
  if not path or path == "" then
    return path
  end
  if not M.is_windows() then
    return path
  end

  path = path:gsub("/", "\\")
  if wx and wx.wxFileName then
    local ok, full = pcall(function()
      local fn = wx.wxFileName()
      fn:Assign(path)
      fn:Normalize()
      return fn:GetFullPath()
    end)
    if ok and full and full ~= "" then
      return full
    end
  end

  if path:match("^%a:[/\\]") or path:match("^\\\\") then
    return path
  end
  return path
end

function M.mkdir_p(dir_path, wx)
  if not dir_path or dir_path == "" then
    return false
  end
  if wx and wx.wxFileName and wx.wxS_DIR_DEFAULT and wx.wxPATH_MKDIR_FULL then
    local ok = pcall(function()
      local fn = wx.wxFileName(dir_path)
      fn:Mkdir(wx.wxS_DIR_DEFAULT, wx.wxPATH_MKDIR_FULL)
    end)
    if ok then
      return true
    end
  end
  if M.is_windows() then
    local ok = os.execute('if not exist "' .. dir_path:gsub('"', '""') .. '" mkdir "' .. dir_path:gsub('"', '""') .. '"')
    return ok == 0 or ok == true
  end
  local ok = os.execute('mkdir -p "' .. dir_path:gsub('"', '\\"') .. '"')
  return ok == 0 or ok == true
end

function M.run_hidden(command_line)
  if not M.is_windows() then
    os.execute(command_line .. " >/dev/null 2>&1 &")
    return true
  end

  local escaped = command_line:gsub('"', '""')
  local vbs_path = os.tmpname() .. ".vbs"
  local handle = io.open(vbs_path, "w")
  if not handle then
    return false
  end
  handle:write(
    'CreateObject("WScript.Shell").Run "' .. escaped .. '", 0, False'
  )
  handle:close()

  os.execute('wscript.exe //B //Nologo "' .. vbs_path:gsub('"', '""') .. '"')
  os.execute("ping 127.0.0.1 -n 1 -w 150 >nul")
  os.remove(vbs_path)
  return true
end

function M.sleep_ms(ms, wx)
  if wx and wx.wxMilliSleep then
    wx.wxMilliSleep(ms)
    return
  end
  if M.is_windows() then
    os.execute(string.format(
      'powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Milliseconds %d"',
      ms
    ))
    return
  end
  os.execute("sleep " .. tostring(ms / 1000))
end

function M.spawn_backend(project_root, port, python_exe)
  if not project_root or project_root == "" then
    return false
  end
  local vbs = project_root .. "\\scripts\\start-backend-hidden.vbs"
  local handle = io.open(vbs, "r")
  if not handle then
    return false
  end
  handle:close()

  local cmd = string.format(
    'wscript.exe //B //Nologo "%s" %d "%s" "%s"',
    vbs:gsub('"', '""'),
    port or 8765,
    project_root:gsub('"', '""'),
    (python_exe or ""):gsub('"', '""')
  )
  return M.run_hidden(cmd)
end

function M.spawn_pythonw_backend(cwd, python_cmd, args, port)
  local pythonw = tostring(python_cmd or "python.exe"):gsub("python%.exe$", "pythonw.exe")
  if pythonw == tostring(python_cmd or "") then
    pythonw = pythonw:gsub("python$", "pythonw.exe")
  end

  local arg_list = {}
  for _, arg in ipairs(args or {}) do
    table.insert(arg_list, "'" .. tostring(arg):gsub("'", "''") .. "'")
  end
  table.insert(arg_list, "'--port'")
  table.insert(arg_list, tostring(port or 8765))
  table.insert(arg_list, "'--write-port-file'")

  local ps = string.format(
    "powershell.exe -NoProfile -WindowStyle Hidden -Command \"Set-Location '%s'; Start-Process -FilePath '%s' -ArgumentList %s -WindowStyle Hidden\"",
    cwd:gsub("'", "''"),
    pythonw:gsub("'", "''"),
    table.concat(arg_list, ",")
  )
  return M.run_hidden(ps)
end

return M
