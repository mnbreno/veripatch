#!/usr/bin/env lua
-- VeriPatch GUI entry point (wxLua)
-- Requires wxLua with wxWidgets bindings installed

local function script_dir()
  local src = debug.getinfo(1, "S").source:match("@?(.*)")
  return src:match("(.*[/\\])") or "./"
end

local gui_root = script_dir()
package.path = gui_root .. "?.lua;" .. gui_root .. "?/init.lua;" .. package.path

local win_silent = require("app.win_silent")

local function normalize_path(path, wx)
  return win_silent.normalize_path(path, wx)
end

local function resolve_python_cmd()
  local configured = os.getenv("VERIPATCH_PYTHON")
  if configured and configured ~= "" then
    return configured
  end

  if package.config:sub(1, 1) == "\\" then
    local local_app = os.getenv("LOCALAPPDATA")
    if local_app and local_app ~= "" then
      local candidates = {
        local_app .. "\\Programs\\Python\\Python314\\python.exe",
        local_app .. "\\Programs\\Python\\Python313\\python.exe",
        local_app .. "\\Programs\\Python\\Python312\\python.exe",
        local_app .. "\\Programs\\Python\\Python311\\python.exe",
      }
      for _, candidate in ipairs(candidates) do
        local handle = io.open(candidate, "rb")
        if handle then
          handle:close()
          return candidate
        end
      end
    end
  end

  return "python"
end

local wx_ok, wx = pcall(require, "wx")
if not wx_ok then
  io.stderr:write(
    "VeriPatch GUI requires wxLua.\n" ..
    "Install wxLua for your platform: https://github.com/pkulchenko/wxlua\n" ..
    "Error: " .. tostring(wx) .. "\n"
  )
  os.exit(1)
end

if wx.wxSystemOptions and wx.wxSystemOptions.SetOption then
  wx.wxSystemOptions.SetOption("msw.force-shell-dpi-aware", "1")
end

local MainFrame = require("app.ui.main_frame")

local app = wx.wxApp:new()

local backend_cwd = normalize_path(gui_root .. "../backend")
local frame = MainFrame.new(nil, {
  python_cmd = resolve_python_cmd(),
  args = {"-m", "veripatch"},
  cwd = backend_cwd,
  gui_root = normalize_path(gui_root),
})

frame:build()
frame:show()

app:MainLoop()

frame.ipc_client:close()
