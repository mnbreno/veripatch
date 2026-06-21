#!/usr/bin/env lua
-- VeriPatch GUI entry point (wxLua)
-- Requires wxLua with wxWidgets bindings installed

local function find_backend_dir()
  local src = debug.getinfo(1, "S").source:match("@?(.*)")
  local gui_dir = src:match("(.*[/\\])") or "./"
  return gui_dir .. "../backend"
end

-- Add gui/ to package.path for app.* modules
local script_path = debug.getinfo(1, "S").source:match("@?(.*)")
local gui_root = script_path:match("(.*[/\\])") or "./"
package.path = gui_root .. "?.lua;" .. gui_root .. "?/init.lua;" .. package.path

local wx_ok, wx = pcall(require, "wx")
if not wx_ok then
  io.stderr:write(
    "VeriPatch GUI requires wxLua.\n" ..
    "Install wxLua for your platform: https://github.com/pkulchenko/wxlua\n" ..
    "Error: " .. tostring(wx) .. "\n"
  )
  os.exit(1)
end

local MainFrame = require("app.ui.main_frame")

local app = wx.wxApp()
app:Init()

local backend_cwd = find_backend_dir()
local frame = MainFrame.new(nil, {
  python_cmd = os.getenv("VERIPATCH_PYTHON") or "python",
  args = {"-m", "veripatch"},
  cwd = backend_cwd,
})

frame:build()
frame:show()

app:MainLoop()
