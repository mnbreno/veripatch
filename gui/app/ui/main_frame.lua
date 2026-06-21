-- VeriPatch main application frame (wxLua)

local ipc = require("app.ipc.client")
local ViewModel = require("app.ui.view_model")
local config = require("app.config")

local MainFrame = {}
MainFrame.__index = MainFrame

function MainFrame.new(parent, backend_config)
  local self = setmetatable({}, MainFrame)
  self.parent = parent
  self.backend_config = backend_config or {}
  self.frame = nil
  self.os_label = nil
  self.sources_list = nil
  self.updates_list = nil
  self.status_label = nil
  self.apply_btn = nil
  self.update_all_btn = nil
  self.refresh_btn = nil
  self.elevate_btn = nil
  self.elevated = false
  self.log_output = nil
  self.ipc_client = ipc.new(
    backend_config.python_cmd or "python",
    backend_config.args or {"-m", "veripatch"},
    backend_config.cwd
  )
  return self
end

function MainFrame:_resolve_icon_path()
  local configured = os.getenv("VERIPATCH_ICON")
  if configured and configured ~= "" then
    return configured
  end
  local gui_root = self.backend_config.gui_root
  if gui_root and gui_root ~= "" then
    local sep = package.config:sub(1, 1)
    if gui_root:sub(-1) == sep or gui_root:sub(-1) == "/" or gui_root:sub(-1) == "\\" then
      return gui_root .. "assets" .. sep .. "veripatch.ico"
    end
    return gui_root .. sep .. "assets" .. sep .. "veripatch.ico"
  end
  return nil
end

function MainFrame:_set_frame_icon(wx)
  local icon_path = self:_resolve_icon_path()
  if not icon_path then
    return
  end
  local handle = io.open(icon_path, "rb")
  if not handle then
    return
  end
  handle:close()

  local icon = wx.wxIcon()
  if icon:LoadFile(icon_path, wx.wxBITMAP_TYPE_ICO) then
    self.frame:SetIcon(icon)
  end
end

function MainFrame:_set_actions_enabled(enabled)
  if self.refresh_btn then
    self.refresh_btn:Enable(enabled)
  end
  if self.elevate_btn then
    self.elevate_btn:Enable(enabled)
  end
  if self.apply_btn then
    self.apply_btn:Enable(enabled)
  end
  if self.update_all_btn then
    self.update_all_btn:Enable(enabled)
  end
end

function MainFrame:build()
  local wx = require("wx")

  self.frame = wx.wxFrame(
    self.parent or wx.NULL,
    wx.wxID_ANY,
    "VeriPatch - Official Source Updates",
    wx.wxDefaultPosition,
    wx.wxSize(720, 700) -- Increased height to accommodate log
  )
  self:_set_frame_icon(wx)

  local panel = wx.wxPanel(self.frame, wx.wxID_ANY)
  local sizer = wx.wxBoxSizer(wx.wxVERTICAL)

  local os_box = wx.wxStaticBox(panel, wx.wxID_ANY, "System Information")
  local os_sizer = wx.wxStaticBoxSizer(os_box, wx.wxVERTICAL)
  self.os_label = wx.wxStaticText(panel, wx.wxID_ANY, "Detecting operating system...")
  os_sizer:Add(self.os_label, 0, wx.wxALL, 5)

  local src_box = wx.wxStaticBox(panel, wx.wxID_ANY, "Official Update Sources")
  local src_sizer = wx.wxStaticBoxSizer(src_box, wx.wxVERTICAL)
  self.sources_list = wx.wxListBox(panel, wx.wxID_ANY)
  src_sizer:Add(self.sources_list, 1, wx.wxEXPAND + wx.wxALL, 5)

  local upd_box = wx.wxStaticBox(panel, wx.wxID_ANY, "Available Updates")
  local upd_sizer = wx.wxStaticBoxSizer(upd_box, wx.wxVERTICAL)
  self.updates_list = wx.wxListBox(panel, wx.wxID_ANY)
  upd_sizer:Add(self.updates_list, 2, wx.wxEXPAND + wx.wxALL, 5)

  local btn_sizer = wx.wxBoxSizer(wx.wxHORIZONTAL)
  self.refresh_btn = wx.wxButton(panel, wx.wxID_ANY, "Refresh")
  self.elevate_btn = wx.wxButton(panel, wx.wxID_ANY, "Request Elevation")
  self.apply_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.apply_button_label(true))
  self.update_all_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.update_all_button_label())
  btn_sizer:Add(self.refresh_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.elevate_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.apply_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.update_all_btn, 0)

  self.status_label = wx.wxStaticText(panel, wx.wxID_ANY, ViewModel.STATUS.READY)

  local log_box = wx.wxStaticBox(panel, wx.wxID_ANY, "Process Output")
  local log_sizer = wx.wxStaticBoxSizer(log_box, wx.wxVERTICAL)
  self.log_output = wx.wxTextCtrl(panel, wx.wxID_ANY, "",
    wx.wxDefaultPosition, wx.wxDefaultSize, wx.wxTE_MULTILINE + wx.wxTE_READONLY + wx.wxHSCROLL)
  self.log_output:SetFont(wx.wxFont(10, wx.wxFONTFAMILY_TELETYPE, wx.wxFONTSTYLE_NORMAL, wx.wxFONTWEIGHT_NORMAL))
  log_sizer:Add(self.log_output, 1, wx.wxEXPAND + wx.wxALL, 5)

  sizer:Add(os_sizer, 0, wx.wxEXPAND + wx.wxALL, 5)
  sizer:Add(src_sizer, 1, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(upd_sizer, 2, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(btn_sizer, 0, wx.wxALL, 5)
  sizer:Add(self.status_label, 0, wx.wxALL, 5)
  sizer:Add(log_sizer, 2, wx.wxEXPAND + wx.wxALL, 5) -- Add log sizer

  panel:SetSizer(sizer)

  self.refresh_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:refresh()
  end)

  self.elevate_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:request_elevation()
  end)

  self.apply_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:apply_updates()
  end)

  self.update_all_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:update_all()
  end)

  self.frame:Connect(wx.wxEVT_CLOSE_WINDOW, function()
    self.ipc_client:close()
    self.frame:Destroy()
  end)

  return self.frame
end

function MainFrame:show()
  self.ipc_client:start()
  self.frame:Show(true)
  self:refresh()
end

function MainFrame:set_status(msg)
  if self.status_label then
    self.status_label:SetLabel(msg)
  end
end

function MainFrame:_set_listbox_items(listbox, rows)
  listbox:Clear()
  for _, row in ipairs(rows) do
    listbox:Append(row)
  end
end

function MainFrame:refresh()
  self:set_status(ViewModel.STATUS.CONNECTING)

  local os_result, os_err = self.ipc_client:call("detect_os")
  local os_text, os_status = ViewModel.format_os_label(os_result, os_err)
  self.os_label:SetLabel(os_text)
  if os_status then
    self:set_status(os_status)
    return
  end
  self.elevated = os_result.elevated == true

  local src_result, src_err = self.ipc_client:call("list_sources")
  local source_rows = ViewModel.format_source_rows(src_result, src_err)
  self:_set_listbox_items(self.sources_list, source_rows)

  local upd_result, upd_err = self.ipc_client:call("check_updates")
  local update_rows, upd_status = ViewModel.format_update_rows(upd_result, upd_err)
  self:_set_listbox_items(self.updates_list, update_rows)
  self:set_status(upd_status or ViewModel.STATUS.LOADED)
end

function MainFrame:append_log(msg)
  if self.log_output then
    self.log_output:AppendText(msg .. "\n")
    -- Scroll to bottom automatically
    self.log_output:ShowPosition(self.log_output:GetLastPosition())
  end
end

function MainFrame:request_elevation()
  self:set_status("Checking elevation...")
  local result, err = self.ipc_client:call("request_elevation", { spawn = true })
  local status = ViewModel.format_elevation_status(result, err)
  self:set_status(status)
  self:append_log(status)
  if result and result.elevated then
    self.elevated = true
  end
end

function MainFrame:apply_updates()
  self:_run_apply(true, false)
end

function MainFrame:update_all()
  local wx = require("wx")

  if not self.elevated then
    local answer = wx.wxMessageBox(
      ViewModel.confirm_elevation_message(),
      "Elevation Required",
      wx.wxYES_NO + wx.wxICON_WARNING
    )
    if answer == wx.wxYES then
      self:request_elevation()
    else
      self:set_status("Update cancelled — elevation required")
    end
    return
  end

  local answer = wx.wxMessageBox(
    ViewModel.confirm_update_all_message(),
    ViewModel.update_all_button_label(),
    wx.wxYES_NO + wx.wxICON_QUESTION + wx.wxNO_DEFAULT
  )
  if answer ~= wx.wxYES then
    self:set_status("Update cancelled")
    return
  end

  self:_run_apply(false, true)
end

function MainFrame:_run_apply(dry_run, confirmed)
  self:clear_log()
  if not dry_run then
    local ok, reason = ViewModel.can_apply_real(
      self.elevated,
      confirmed,
      config.APPLY_CONFIRMATION_TOKEN
    )
    if not ok then
      self:set_status(reason)
      self:append_log(reason)
      return
    end
  end

  self:_set_actions_enabled(false)
  self:set_status(dry_run and "Applying updates (dry run)..." or "Installing all updates...")
  self:append_log(dry_run and "Initiating dry-run update..." or "Initiating update for all packages...")

  local params = ViewModel.build_apply_params(
    dry_run,
    confirmed,
    config.APPLY_CONFIRMATION_TOKEN
  )
  local result, err = self.ipc_client:call("apply_updates_stream", params, function(line)
    self:append_log(line)
  end)

  self:_set_actions_enabled(true)
  self:set_status(ViewModel.format_apply_status(result, err, dry_run))
  if err then
    self:append_log("ERROR: " .. err)
  else
    self:append_log("Update process completed.")
    if not dry_run and result and result.success then
      self:refresh()
    end
  end
end

function MainFrame:clear_log()
  if self.log_output then
    self.log_output:Clear()
  end
end

return MainFrame
