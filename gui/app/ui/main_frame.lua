-- VeriPatch main application frame (wxLua)

local ipc = require("app.ipc.client")
local ViewModel = require("app.ui.view_model")
local config = require("app.config")
local text = require("app.ui.text")
local win_silent = require("app.win_silent")
local wx = require("wx")

local MainFrame = {}
MainFrame.__index = MainFrame

local function dip_size(frame, width, height)
  if frame and frame.FromDIP then
    local size = frame:FromDIP(wx.wxSize(width, height))
    return size:GetWidth(), size:GetHeight()
  end
  return width, height
end

local function dip_int(frame, value)
  if frame and frame.FromDIP then
    return frame:FromDIP(value)
  end
  return value
end

local function to_wx_string(value)
  return text.to_wx_string(wx, value)
end

local function append_utf8(text_ctrl, msg)
  local line = text.repair_mojibake(tostring(msg)) .. "\n"
  if wx.wxString and wx.wxString.FromUTF8 then
    text_ctrl:AppendText(wx.wxString.FromUTF8(line))
  else
    text_ctrl:AppendText(line)
  end
end

local function set_control_tooltip(control, tooltip_id)
  if not control or not tooltip_id then
    return
  end
  local tip = ViewModel.control_tooltip(tooltip_id)
  if tip == "" then
    return
  end
  if control.SetToolTip then
    control:SetToolTip(to_wx_string(tip))
  end
  if control.SetHelpText then
    control:SetHelpText(to_wx_string(tip))
  end
end

local function set_section_title_font(static_box, frame)
  if not static_box or not static_box.GetStaticBox then
    return
  end
  local box = static_box:GetStaticBox()
  if not box then
    return
  end
  local base_font = wx.wxSystemSettings.GetFont(wx.wxSYS_DEFAULT_GUI_FONT)
  local title_font = wx.wxFont(
    base_font:GetPointSize() + 1,
    base_font:GetFamily(),
    base_font:GetStyle(),
    wx.wxFONTWEIGHT_BOLD,
    base_font:GetUnderlined(),
    base_font:GetFaceName()
  )
  box:SetFont(title_font)
end

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
  self.update_selected_btn = nil
  self.update_all_btn = nil
  self.update_cursor_btn = nil
  self.refresh_btn = nil
  self.elevate_btn = nil
  self.elevated = false
  self.log_output = nil
  self.update_items = {}
  self.blockers = {}
  self.last_check = nil
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

function MainFrame:_set_frame_icon()
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
  if self.update_selected_btn then
    self.update_selected_btn:Enable(enabled)
  end
  if self.update_all_btn then
    self.update_all_btn:Enable(enabled)
  end
  if self.update_cursor_btn then
    self.update_cursor_btn:Enable(enabled)
  end
end

function MainFrame:build()
  self.frame = wx.wxFrame(
    self.parent or wx.NULL,
    wx.wxID_ANY,
    ViewModel.UI.WINDOW_TITLE,
    wx.wxDefaultPosition,
    wx.wxSize(760, 760)
  )
  local frame_w, frame_h = dip_size(self.frame, 760, 760)
  self.frame:SetSize(wx.wxSize(frame_w, frame_h))
  self:_set_frame_icon()

  local panel = wx.wxPanel(self.frame, wx.wxID_ANY)
  local default_font = wx.wxSystemSettings.GetFont(wx.wxSYS_DEFAULT_GUI_FONT)
  panel:SetFont(default_font)
  local sizer = wx.wxBoxSizer(wx.wxVERTICAL)

  local os_box = wx.wxStaticBox(panel, wx.wxID_ANY, ViewModel.UI.SECTION_SYSTEM)
  local os_sizer = wx.wxStaticBoxSizer(os_box, wx.wxVERTICAL)
  set_section_title_font(os_sizer, self.frame)
  self.os_label = wx.wxStaticText(panel, wx.wxID_ANY, "Detecting your computer...")
  os_sizer:Add(self.os_label, 0, wx.wxALL, 5)

  local src_box = wx.wxStaticBox(panel, wx.wxID_ANY, ViewModel.UI.SECTION_SOURCES)
  local src_sizer = wx.wxStaticBoxSizer(src_box, wx.wxVERTICAL)
  set_section_title_font(src_sizer, self.frame)
  self.sources_list = wx.wxListBox(panel, wx.wxID_ANY)
  set_control_tooltip(self.sources_list, "sources_list")
  src_sizer:Add(self.sources_list, 1, wx.wxEXPAND + wx.wxALL, 5)

  local upd_box = wx.wxStaticBox(panel, wx.wxID_ANY, ViewModel.UI.SECTION_UPDATES)
  local upd_sizer = wx.wxStaticBoxSizer(upd_box, wx.wxVERTICAL)
  set_section_title_font(upd_sizer, self.frame)
  self.updates_list = wx.wxCheckListBox(panel, wx.wxID_ANY)
  set_control_tooltip(self.updates_list, "updates_list")
  upd_sizer:Add(self.updates_list, 2, wx.wxEXPAND + wx.wxALL, 5)

  local btn_sizer = wx.wxBoxSizer(wx.wxHORIZONTAL)
  self.refresh_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.refresh_button_label())
  self.elevate_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.elevate_button_label())
  self.apply_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.apply_button_label(true))
  self.update_selected_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.update_selected_button_label())
  self.update_all_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.update_all_button_label())
  self.update_cursor_btn = wx.wxButton(panel, wx.wxID_ANY, ViewModel.update_cursor_later_button_label())
  set_control_tooltip(self.refresh_btn, "refresh")
  set_control_tooltip(self.elevate_btn, "elevate")
  set_control_tooltip(self.apply_btn, "preview")
  set_control_tooltip(self.update_selected_btn, "update_selected")
  set_control_tooltip(self.update_all_btn, "update_all")
  set_control_tooltip(self.update_cursor_btn, "update_cursor")
  btn_sizer:Add(self.refresh_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.elevate_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.apply_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.update_selected_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.update_all_btn, 0, wx.wxRIGHT, 5)
  btn_sizer:Add(self.update_cursor_btn, 0)

  self.status_label = wx.wxStaticText(panel, wx.wxID_ANY, ViewModel.STATUS.READY)
  self.status_label:Wrap(dip_int(self.frame, 700))
  set_control_tooltip(self.status_label, "status")
  if self.status_label.SetName then
    self.status_label:SetName("Status")
  end

  local log_box = wx.wxStaticBox(panel, wx.wxID_ANY, ViewModel.UI.SECTION_LOG)
  local log_sizer = wx.wxStaticBoxSizer(log_box, wx.wxVERTICAL)
  set_section_title_font(log_sizer, self.frame)
  self.log_output = wx.wxTextCtrl(panel, wx.wxID_ANY, "",
    wx.wxDefaultPosition, wx.wxDefaultSize, wx.wxTE_MULTILINE + wx.wxTE_READONLY + wx.wxHSCROLL)
  set_control_tooltip(self.log_output, "activity_log")
  if self.log_output.SetName then
    self.log_output:SetName("Activity log")
  end
  local log_font = wx.wxFont(
    dip_int(self.frame, 10),
    wx.wxFONTFAMILY_TELETYPE,
    wx.wxFONTSTYLE_NORMAL,
    wx.wxFONTWEIGHT_NORMAL
  )
  self.log_output:SetFont(log_font)
  log_sizer:Add(self.log_output, 1, wx.wxEXPAND + wx.wxALL, 5)

  sizer:Add(os_sizer, 0, wx.wxEXPAND + wx.wxALL, 5)
  sizer:Add(src_sizer, 1, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(upd_sizer, 2, wx.wxEXPAND + wx.wxLEFT + wx.wxRIGHT, 5)
  sizer:Add(btn_sizer, 0, wx.wxALL, 5)
  sizer:Add(self.status_label, 0, wx.wxALL, 5)
  sizer:Add(log_sizer, 2, wx.wxEXPAND + wx.wxALL, 5)

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

  self.update_selected_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:update_selected()
  end)

  self.update_all_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:update_all()
  end)

  self.update_cursor_btn:Connect(wx.wxEVT_COMMAND_BUTTON_CLICKED, function()
    self:update_cursor_later()
  end)

  self.frame:Connect(wx.wxEVT_CLOSE_WINDOW, function()
    self.ipc_client:close()
    self.frame:Destroy()
  end)

  self.update_cursor_btn:Show(false)
  return self.frame
end

function MainFrame:show()
  self.ipc_client:start()
  self.frame:Show(true)
  self:refresh()
end

function MainFrame:set_status(msg)
  if self.status_label then
    self.status_label:SetLabel(to_wx_string(msg))
  end
end

function MainFrame:_set_listbox_items(listbox, rows)
  listbox:Clear()
  for _, row in ipairs(rows) do
    listbox:Append(to_wx_string(row))
  end
end

function MainFrame:_set_update_items(items)
  self.update_items = items or {}
  self.updates_list:Clear()
  for _, item in ipairs(self.update_items) do
    self.updates_list:Append(to_wx_string(item.display))
  end
end

function MainFrame:_sync_cursor_button()
  local show_cursor = ViewModel.cursor_update_available(self.update_items, self.blockers)
  if self.update_cursor_btn then
    self.update_cursor_btn:Show(show_cursor)
    if self.frame and self.frame.Layout then
      self.frame:Layout()
    end
  end
end

function MainFrame:_checked_indices()
  local checked = {}
  local count = self.updates_list:GetCount()
  for index = 0, count - 1 do
    if self.updates_list:IsChecked(index) then
      table.insert(checked, index)
    end
  end
  return checked
end

function MainFrame:refresh()
  self:set_status(ViewModel.STATUS.CONNECTING)

  local os_result, os_err = self.ipc_client:call("detect_os")
  local os_text, os_status = ViewModel.format_os_label(os_result, os_err)
  self.os_label:SetLabel(to_wx_string(os_text))
  if os_status then
    self:set_status(os_status)
    return
  end
  self.elevated = os_result.elevated == true

  local src_result, src_err = self.ipc_client:call("list_sources")
  local source_rows = ViewModel.format_source_rows(src_result, src_err)
  self:_set_listbox_items(self.sources_list, source_rows)

  local upd_result, upd_err = self.ipc_client:call("check_updates")
  self.last_check = upd_result
  self.blockers = (upd_result and upd_result.blockers) or {}
  self.update_items = ViewModel.parse_update_items(upd_result)
  local update_rows, upd_status = ViewModel.format_update_rows(upd_result, upd_err)
  if #self.update_items > 0 then
    self:_set_update_items(self.update_items)
  else
    self:_set_listbox_items(self.updates_list, update_rows)
  end
  self:_sync_cursor_button()
  self:set_status(upd_status or ViewModel.STATUS.LOADED)
end

function MainFrame:append_log(msg)
  if self.log_output then
    append_utf8(self.log_output, msg)
    self.log_output:ShowPosition(self.log_output:GetLastPosition())
  end
end

function MainFrame:request_elevation()
  self:set_status(ViewModel.STATUS.ELEVATION_PENDING)
  local used_ps1_launcher = false
  if win_silent.is_windows() and self.backend_config.project_root then
    local spawned = win_silent.spawn_elevated_backend(
      self.backend_config.project_root,
      self.ipc_client.port,
      self.backend_config.python_cmd
    )
    if spawned then
      used_ps1_launcher = true
      if self:_wait_for_elevated_backend() then
        return
      end
    end
  end

  local result, err = self.ipc_client:call(
    "request_elevation",
    { spawn = not used_ps1_launcher }
  )
  local status = ViewModel.format_elevation_status(result, err)
  self:set_status(status)
  self:append_log(status)
  if result and result.elevated then
    self.elevated = true
  elseif self:_wait_for_elevated_backend() then
    return
  end
end

function MainFrame:_wait_for_elevated_backend()
  self.ipc_client:reset_backend_session()
  for _ = 1, 40 do
    win_silent.sleep_ms(500, wx)
    local os_result = self.ipc_client:poll_elevated()
    if os_result and os_result.elevated then
      self.elevated = true
      local status = ViewModel.format_elevation_status({ elevated = true })
      self:set_status(status)
      self:append_log(status)
      local os_text = ViewModel.format_os_label(os_result)
      self.os_label:SetLabel(to_wx_string(os_text))
      return true
    end
  end
  return false
end

function MainFrame:_ensure_elevated()
  if self.elevated then
    return true
  end
  local answer = wx.wxMessageBox(
    ViewModel.confirm_elevation_message(),
    ViewModel.UI.DIALOG_ELEVATION_TITLE,
    wx.wxYES_NO + wx.wxICON_WARNING
  )
  if answer ~= wx.wxYES then
    self:set_status(ViewModel.STATUS.ELEVATION_CANCELLED)
    return false
  end

  self:request_elevation()
  if self.elevated then
    return true
  end
  self:set_status("Administrator approval is required. Approve the security prompt, then try again.")
  return false
end

function MainFrame:_resolve_cursor_skip()
  if not ViewModel.should_prompt_cursor_gate(self.update_items, self.blockers) then
    return {}
  end
  local answer = wx.wxMessageBox(
    ViewModel.cursor_gate_message(),
    "Cursor Is Running",
    wx.wxYES_NO + wx.wxICON_WARNING + wx.wxNO_DEFAULT
  )
  if answer == wx.wxYES then
    return { ViewModel.CURSOR_PACKAGE_ID }
  end
  self:set_status("Update cancelled — close Cursor or skip it")
  return nil
end

function MainFrame:apply_updates()
  self:_run_apply(true, false, {})
end

function MainFrame:update_selected()
  if not self:_ensure_elevated() then
    return
  end

  local checked = self:_checked_indices()
  local package_ids = ViewModel.selected_package_ids(self.update_items, checked)
  if #package_ids == 0 then
    self:set_status("Select at least one update to install")
    return
  end

  if ViewModel.should_prompt_cursor_gate(self.update_items, self.blockers) then
    for _, package_id in ipairs(package_ids) do
      if package_id == ViewModel.CURSOR_PACKAGE_ID then
        local gate = wx.wxMessageBox(
          ViewModel.cursor_gate_message(),
          ViewModel.update_selected_button_label(),
          wx.wxYES_NO + wx.wxICON_QUESTION + wx.wxNO_DEFAULT
        )
        if gate ~= wx.wxYES then
          self:set_status("Update cancelled")
          return
        end
        break
      end
    end
  end

  local answer = wx.wxMessageBox(
    ViewModel.confirm_update_selected_message(#package_ids),
    ViewModel.update_selected_button_label(),
    wx.wxYES_NO + wx.wxICON_QUESTION + wx.wxNO_DEFAULT
  )
  if answer ~= wx.wxYES then
    self:set_status("Update cancelled")
    return
  end

  self:_run_apply(false, true, { package_ids = package_ids })
end

function MainFrame:update_all()
  if not self:_ensure_elevated() then
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

  local skip_package_ids = self:_resolve_cursor_skip()
  if skip_package_ids == nil then
    return
  end

  self:_run_apply(false, true, { skip_package_ids = skip_package_ids })
end

function MainFrame:update_cursor_later()
  if not self:_ensure_elevated() then
    return
  end

  local answer = wx.wxMessageBox(
    ViewModel.confirm_update_cursor_message(),
    ViewModel.update_cursor_later_button_label(),
    wx.wxYES_NO + wx.wxICON_QUESTION + wx.wxNO_DEFAULT
  )
  if answer ~= wx.wxYES then
    self:set_status("Cursor update cancelled")
    return
  end

  self:_run_apply(false, true, {
    package_ids = { ViewModel.CURSOR_PACKAGE_ID },
  })
end

function MainFrame:_run_apply(dry_run, confirmed, options)
  options = options or {}
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
  local action_label = "Installing updates..."
  if dry_run then
    action_label = "Previewing updates (no changes)..."
  elseif options.package_ids and #options.package_ids == 1
      and options.package_ids[1] == ViewModel.CURSOR_PACKAGE_ID then
    action_label = "Installing Cursor update..."
  elseif options.package_ids then
    action_label = string.format("Installing %d selected update(s)...", #options.package_ids)
  end
  self:set_status(action_label)

  local log_line = dry_run and "Starting preview (no changes will be made)..." or "Starting install..."
  self:append_log(log_line)

  local params = ViewModel.build_apply_params(
    dry_run,
    confirmed,
    config.APPLY_CONFIRMATION_TOKEN,
    options
  )
  local result, err = self.ipc_client:call("apply_updates_stream", params, function(line)
    self:append_log(line)
  end)

  self:_set_actions_enabled(true)
  local status = ViewModel.format_apply_status(result, err, dry_run)
  self:set_status(status)
  if err then
    self:append_log("ERROR: " .. err)
  elseif result and result.errors then
    for _, error_line in ipairs(result.errors) do
      self:append_log("FAILED: " .. error_line)
    end
  end
  if not err then
    local summary = ViewModel.format_apply_summary(result)
    if summary then
      self:append_log("Summary: " .. summary)
    end
    self:append_log("Update process completed.")
    if not dry_run and result and (result.success or (result.summary and (result.summary.updated or 0) > 0)) then
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
