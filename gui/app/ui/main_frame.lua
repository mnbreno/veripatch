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
  self.apply_dry_run = true
  self.apply_confirmed = false
  self.elevated = false
  self.log_output = nil -- New member for log display
  self.ipc_client = ipc.new(
    backend_config.python_cmd or "python",
    backend_config.args or {"-m", "veripatch"},
    backend_config.cwd
  )
  return self
end

function MainFrame:build()
  local wx = require("wx")

  self.frame = wx.wxFrame(
    self.parent,
    wx.wxID_ANY,
    "VeriPatch - Official Source Updates",
    wx.wxDefaultPosition,
    wx.wxSize(720, 700) -- Increased height to accommodate log
  )

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
  local refresh_btn = wx.wxButton(panel, wx.wxID_ANY, "Refresh")
  self.apply_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.apply_button_label(true))
  btn_sizer:Add(refresh_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.apply_btn, 0)

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

  refresh_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:refresh()
  end)

  self.apply_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:apply_updates()
  end)

  self.frame:Connect(wx.wxEVT_CLOSE_WINDOW, function()
    self.ipc_client:close()
    self.frame:Destroy()
  end)

  return self.frame
end

function MainFrame:show()
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

function MainFrame:apply_updates()
  self:clear_log()
  local dry_run = self.apply_dry_run
  if not dry_run then
    local ok, reason = ViewModel.can_apply_real(
      self.elevated,
      self.apply_confirmed,
      config.APPLY_CONFIRMATION_TOKEN
    )
    if not ok then
      self:set_status(reason)
      self:append_log(reason)
      return
    end
  end

  self:set_status(dry_run and "Applying updates (dry run)..." or "Applying updates...")
  self:append_log(dry_run and "Initiating dry-run update..." or "Initiating real update...")

  local params = ViewModel.build_apply_params(
    dry_run,
    self.apply_confirmed,
    config.APPLY_CONFIRMATION_TOKEN
  )
  local result, err = self.ipc_client:call("apply_updates_stream", params, function(line)
    self:append_log(line)
  end)

  self:set_status(ViewModel.format_apply_status(result, err, dry_run))
  if err then
    self:append_log("ERROR: " .. err)
  else
    self:append_log("Update process completed.")
  end
end

function MainFrame:clear_log()
  if self.log_output then
    self.log_output:Clear()
  end
end

return MainFrame
