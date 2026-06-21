-- VeriPatch main application frame (wxLua)

local ipc = require("app.ipc.client")

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
    wx.wxSize(720, 520)
  )

  local panel = wx.wxPanel(self.frame, wx.wxID_ANY)
  local sizer = wx.wxBoxSizer(wx.wxVERTICAL)

  -- OS info section
  local os_box = wx.wxStaticBox(panel, wx.wxID_ANY, "System Information")
  local os_sizer = wx.wxStaticBoxSizer(os_box, wx.wxVERTICAL)
  self.os_label = wx.wxStaticText(panel, wx.wxID_ANY, "Detecting operating system...")
  os_sizer:Add(self.os_label, 0, wx.wxALL, 5)

  -- Official sources section
  local src_box = wx.wxStaticBox(panel, wx.wxID_ANY, "Official Update Sources")
  local src_sizer = wx.wxStaticBoxSizer(src_box, wx.wxVERTICAL)
  self.sources_list = wx.wxListBox(panel, wx.wxID_ANY)
  src_sizer:Add(self.sources_list, 1, wx.wxEXPAND + wx.wxALL, 5)

  -- Available updates section
  local upd_box = wx.wxStaticBox(panel, wx.wxID_ANY, "Available Updates")
  local upd_sizer = wx.wxStaticBoxSizer(upd_box, wx.wxVERTICAL)
  self.updates_list = wx.wxListBox(panel, wx.wxID_ANY)
  upd_sizer:Add(self.updates_list, 2, wx.wxEXPAND + wx.wxALL, 5)

  -- Action buttons
  local btn_sizer = wx.wxBoxSizer(wx.wxHORIZONTAL)
  local refresh_btn = wx.wxButton(panel, wx.wxID_ANY, "Refresh")
  self.apply_btn = wx.wxButton(panel, wx.wxID_ANY, "Apply (Dry Run)")
  btn_sizer:Add(refresh_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.apply_btn, 0)

  self.status_label = wx.wxStaticText(panel, wx.wxID_ANY, "Ready")

  sizer:Add(os_sizer, 0, wx.wxEXPAND + wx.wxALL, 5)
  sizer:Add(src_sizer, 1, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(upd_sizer, 2, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(btn_sizer, 0, wx.wxALL, 5)
  sizer:Add(self.status_label, 0, wx.wxALL, 5)

  panel:SetSizer(sizer)

  refresh_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:refresh()
  end)

  self.apply_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:apply_dry_run()
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

function MainFrame:refresh()
  self:set_status("Connecting to backend...")

  local os_result, os_err = self.ipc_client:call("detect_os")
  if not os_result then
    self.os_label:SetLabel("Backend error: " .. tostring(os_err))
    self:set_status("Failed to detect OS")
    return
  end

  local os = os_result.os
  local elevated = os_result.elevated and "Yes" or "No"
  local os_text = string.format(
    "OS: %s | Version: %s | Arch: %s | Elevated: %s",
    os.os_type or "?",
    os.version or "?",
    os.architecture or "?",
    elevated
  )
  if os.distro_name then
    os_text = os_text .. " | Distro: " .. os.distro_name
  end
  self.os_label:SetLabel(os_text)

  self.sources_list:Clear()
  local src_result, src_err = self.ipc_client:call("list_sources")
  if src_result and src_result.sources then
    for _, source in ipairs(src_result.sources) do
      self.sources_list:Append(source.name .. " (" .. source.id .. ")")
    end
  else
    self.sources_list:Append("Failed to load sources: " .. tostring(src_err))
  end

  self.updates_list:Clear()
  local upd_result, upd_err = self.ipc_client:call("check_updates")
  if upd_result and upd_result.updates and upd_result.updates.items then
    for _, item in ipairs(upd_result.updates.items) do
      self.updates_list:Append(item.title .. " [" .. item.source_id .. "]")
    end
    self:set_status("Updates loaded (stub data in foundation release)")
  else
    self.updates_list:Append("Failed to check updates: " .. tostring(upd_err))
    self:set_status("Update check failed")
  end
end

function MainFrame:apply_dry_run()
  self:set_status("Applying updates (dry run)...")
  local result, err = self.ipc_client:call("apply_updates", { dry_run = true })
  if result then
    local count = result.items and #result.items or 0
    self:set_status(string.format("Dry run complete: %s (%d items)", result.message, count))
  else
    self:set_status("Dry run failed: " .. tostring(err))
  end
end

return MainFrame
