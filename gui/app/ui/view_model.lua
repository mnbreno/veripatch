-- VeriPatch GUI view-model (pure logic, no wx dependencies)

local config = require("app.config")
local text = require("app.ui.text")

local ViewModel = {}

ViewModel.CURSOR_PACKAGE_ID = "Anysphere.Cursor"

ViewModel.STATUS = {
  READY = "Ready",
  CONNECTING = "Checking for updates...",
  LOADED = "Updates loaded",
  LOAD_FAILED = "Could not check for updates",
  OS_FAILED = "Could not detect your computer",
  ELEVATION_CANCELLED = "Update cancelled — administrator access is required",
  ELEVATION_PENDING = "Waiting for administrator approval...",
}

ViewModel.UI = {
  WINDOW_TITLE = "VeriPatch — Easy software updates",
  SECTION_SYSTEM = "About your computer",
  SECTION_SOURCES = "Trusted update sources",
  SECTION_UPDATES = "Available updates (check items to install)",
  SECTION_LOG = "Activity log",
  DIALOG_ELEVATION_TITLE = "Administrator access required",
}

ViewModel.TOOLTIPS = {
  refresh = "Check again for new updates from trusted sources.",
  elevate = "Restart the update service with administrator rights so installs can finish.",
  preview = "See what would be installed without making any changes to your computer.",
  update_selected = "Install only the updates you checked in the list above.",
  update_all = "Install every available update from trusted sources in one step.",
  update_cursor = "Install the Cursor editor update after you close Cursor completely.",
  sources_list = "Official places VeriPatch checks for updates, such as Microsoft WinGet.",
  updates_list = "Updates ready to install. Check the boxes for items you want, then choose an action below.",
  activity_log = "Step-by-step progress while VeriPatch checks for or installs updates.",
  status = "Current status of your update session.",
}

function ViewModel.control_tooltip(control_id)
  return ViewModel.TOOLTIPS[control_id] or ""
end

function ViewModel.all_tooltip_ids()
  return {
    "refresh",
    "elevate",
    "preview",
    "update_selected",
    "update_all",
    "update_cursor",
    "sources_list",
    "updates_list",
    "activity_log",
    "status",
  }
end

function ViewModel.format_os_label(os_result, os_err)
  if not os_result then
    return "Could not reach the update service: " .. tostring(os_err or "unknown"), ViewModel.STATUS.OS_FAILED
  end

  local os = os_result.os or {}
  local admin_label = os_result.elevated and "Yes" or "No"
  local label = string.format(
    "Computer: %s | Version: %s | Type: %s | Administrator access: %s",
    os.os_type or "?",
    os.version or "?",
    os.architecture or "?",
    admin_label
  )
  if os.distro_name then
    label = label .. " | Edition: " .. os.distro_name
  end
  return label, nil
end

function ViewModel.format_source_rows(src_result, src_err)
  local rows = {}
  if src_result and src_result.sources then
    for _, source in ipairs(src_result.sources) do
      table.insert(rows, source.name or source.id or "Unknown source")
    end
    return rows, nil
  end
  table.insert(rows, "Could not load update sources: " .. tostring(src_err or "unknown"))
  return rows, "source_error"
end

function ViewModel.parse_update_items(upd_result)
  local items = {}
  if upd_result and upd_result.updates and upd_result.updates.items then
    for _, item in ipairs(upd_result.updates.items) do
      local metadata = item.metadata or {}
      table.insert(items, {
        id = item.id,
        title = item.title,
        source_id = item.source_id,
        package_id = metadata.package_id,
        display = item.title or item.id or "Update",
      })
    end
  end
  return items
end

function ViewModel.format_update_rows(upd_result, upd_err)
  local items = ViewModel.parse_update_items(upd_result)
  local rows = {}
  for _, item in ipairs(items) do
    table.insert(rows, item.display)
  end
  if #rows > 0 then
    return rows, ViewModel.STATUS.LOADED
  end
  if upd_err or not upd_result then
    table.insert(rows, "Could not check for updates: " .. tostring(upd_err or "unknown"))
    return rows, ViewModel.STATUS.LOAD_FAILED
  end
  table.insert(rows, "No updates available")
  return rows, ViewModel.STATUS.LOADED
end

function ViewModel.cursor_update_available(update_items, blockers)
  if blockers and blockers.cursor_update_available then
    return true
  end
  for _, item in ipairs(update_items or {}) do
    if item.package_id == ViewModel.CURSOR_PACKAGE_ID then
      return true
    end
  end
  return false
end

function ViewModel.should_prompt_cursor_gate(update_items, blockers)
  if not blockers or not blockers.cursor_running then
    return false
  end
  return ViewModel.cursor_update_available(update_items, blockers)
end

function ViewModel.cursor_gate_message()
  return table.concat({
    "Cursor is open and has an update waiting.",
    "",
    "Yes = Skip Cursor and update everything else",
    "No = Cancel this update run",
    "",
    "Close Cursor completely, then use 'Update Cursor Later'.",
  }, "\n")
end

function ViewModel.refresh_button_label()
  return "&Refresh"
end

function ViewModel.elevate_button_label()
  return "Run as &administrator"
end

function ViewModel.apply_button_label(dry_run)
  if dry_run then
    return "&Preview updates (no changes)"
  end
  return "Install updates"
end

function ViewModel.update_selected_button_label()
  return "Update &selected"
end

function ViewModel.update_all_button_label()
  return "Update &all"
end

function ViewModel.update_cursor_later_button_label()
  return "Update Cursor &later"
end

function ViewModel.confirm_update_all_message()
  return table.concat({
    "Install all available updates from trusted sources?",
    "",
    "Apps may restart and your computer may ask you to restart when finished.",
  }, "\n")
end

function ViewModel.confirm_update_selected_message(count)
  return string.format(
    "Install %d selected update(s) from trusted sources?",
    count or 0
  )
end

function ViewModel.confirm_update_cursor_message()
  return table.concat({
    "Install the Cursor update now?",
    "",
    "Close Cursor completely before continuing.",
  }, "\n")
end

function ViewModel.confirm_elevation_message()
  return table.concat({
    "Administrator access is required to install updates.",
    "",
    "Allow VeriPatch to continue with administrator rights?",
  }, "\n")
end

function ViewModel.can_apply_real(elevated, confirmed, confirm_token)
  if not elevated then
    return false, "Administrator access is required to install updates"
  end
  if not confirmed then
    return false, "Please confirm before installing updates"
  end
  if confirm_token ~= config.APPLY_CONFIRMATION_TOKEN then
    return false, "Update could not be confirmed. Please try again."
  end
  return true, nil
end

function ViewModel.build_apply_params(dry_run, confirmed, confirm_token, options)
  options = options or {}
  local params = { dry_run = dry_run }
  if not dry_run then
    params.confirm = confirmed
    params.confirm_token = confirm_token
  end
  if options.package_ids and #options.package_ids > 0 then
    params.package_ids = options.package_ids
  end
  if options.skip_package_ids and #options.skip_package_ids > 0 then
    params.skip_package_ids = options.skip_package_ids
  end
  return params
end

function ViewModel.format_apply_summary(result)
  if not result or not result.summary then
    return nil
  end
  local summary = result.summary
  return string.format(
    "%d updated · %d skipped · %d failed",
    summary.updated or 0,
    summary.skipped or 0,
    summary.failed or 0
  )
end

function ViewModel.format_apply_status(result, err, dry_run)
  if not result then
    return text.repair_mojibake("Install failed: " .. tostring(err or "unknown error"))
  end

  local summary_text = ViewModel.format_apply_summary(result)
  if dry_run then
    if summary_text then
      return "Preview complete: " .. summary_text
    end
    local count = result.items and #result.items or 0
    return string.format("Preview complete: %s (%d items)", result.message or "done", count)
  end

  if summary_text then
    if result.success then
      return "Install complete: " .. text.repair_mojibake(summary_text)
    end
    return "Some updates did not finish: " .. text.repair_mojibake(summary_text) .. " — see Activity log"
  end

  if result.success then
    return string.format(
      "Install complete: %s",
      text.repair_mojibake(result.message or "done")
    )
  end

  if result.errors and #result.errors > 0 then
    local primary = text.repair_mojibake(result.errors[1])
    if #result.errors > 1 then
      return string.format(
        "Install failed (%d issues). %s — see Activity log",
        #result.errors,
        primary
      )
    end
    return "Install failed: " .. primary
  end

  return text.repair_mojibake("Install failed: " .. (result.message or "unknown error"))
end

function ViewModel.format_elevation_status(result, err)
  if not result then
    return "Could not check administrator access: " .. tostring(err or "unknown")
  end
  if result.elevated then
    return "Running with administrator access"
  end
  if result.spawned then
    return "Approve the Windows security prompt to continue"
  end
  if result.suggested_sudo then
    return "Restart VeriPatch with administrator rights: " .. result.suggested_sudo
  end
  if result.suggested then
    return result.suggested
  end
  return result.message or "Administrator access is required to install updates"
end

function ViewModel.format_apply_timeout_message(timeout_seconds)
  return string.format(
    "An update step took longer than %d minutes. You can try again or set VERIPATCH_APPLY_TIMEOUT for more time.",
    math.floor((timeout_seconds or 300) / 60)
  )
end

function ViewModel.selected_package_ids(update_items, checked_indices)
  local package_ids = {}
  for _, index in ipairs(checked_indices or {}) do
    local item = update_items[index + 1]
    if item and item.package_id and item.package_id ~= "" then
      table.insert(package_ids, item.package_id)
    end
  end
  return package_ids
end

return ViewModel
