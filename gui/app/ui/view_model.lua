-- VeriPatch GUI view-model (pure logic, no wx dependencies)

local config = require("app.config")
local text = require("app.ui.text")

local ViewModel = {}

ViewModel.CURSOR_PACKAGE_ID = "Anysphere.Cursor"

ViewModel.STATUS = {
  READY = "Ready",
  CONNECTING = "Connecting to backend...",
  LOADED = "Updates loaded",
  LOAD_FAILED = "Update check failed",
  OS_FAILED = "Failed to detect OS",
}

function ViewModel.format_os_label(os_result, os_err)
  if not os_result then
    return "Backend error: " .. tostring(os_err or "unknown"), ViewModel.STATUS.OS_FAILED
  end

  local os = os_result.os or {}
  local elevated = os_result.elevated and "Yes" or "No"
  local label = string.format(
    "OS: %s | Version: %s | Arch: %s | Elevated: %s",
    os.os_type or "?",
    os.version or "?",
    os.architecture or "?",
    elevated
  )
  if os.distro_name then
    label = label .. " | Distro: " .. os.distro_name
  end
  return label, nil
end

function ViewModel.format_source_rows(src_result, src_err)
  local rows = {}
  if src_result and src_result.sources then
    for _, source in ipairs(src_result.sources) do
      table.insert(rows, source.name .. " (" .. source.id .. ")")
    end
    return rows, nil
  end
  table.insert(rows, "Failed to load sources: " .. tostring(src_err or "unknown"))
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
        display = item.title .. " [" .. item.source_id .. "]",
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
    table.insert(rows, "Failed to check updates: " .. tostring(upd_err or "unknown"))
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
    "Cursor is running and has an available update.",
    "",
    "Yes = Skip Cursor and update other packages",
    "No = Cancel this update run",
    "",
    "Close Cursor completely, then use 'Update Cursor Later'.",
  }, "\n")
end

function ViewModel.apply_button_label(dry_run)
  if dry_run then
    return "Apply (Dry Run)"
  end
  return "Apply Updates"
end

function ViewModel.update_selected_button_label()
  return "Update Selected"
end

function ViewModel.update_all_button_label()
  return "Update All"
end

function ViewModel.update_cursor_later_button_label()
  return "Update Cursor Later"
end

function ViewModel.confirm_update_all_message()
  return table.concat({
    "Install all available updates from official sources?",
    "",
    "This uses WinGet, Windows Update, apt, or other vendor tools.",
    "Apps may restart and some updates may require a reboot.",
  }, "\n")
end

function ViewModel.confirm_update_selected_message(count)
  return string.format(
    "Install %d selected update(s) from official sources?",
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
    "Administrator privileges are required to install updates.",
    "",
    "Request elevation now?",
  }, "\n")
end

function ViewModel.can_apply_real(elevated, confirmed, confirm_token)
  if not elevated then
    return false, "Administrator/root privileges required for real apply"
  end
  if not confirmed then
    return false, "Confirmation required before applying updates"
  end
  if confirm_token ~= config.APPLY_CONFIRMATION_TOKEN then
    return false, "Invalid confirmation token"
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
    return text.repair_mojibake("Apply failed: " .. tostring(err or "unknown error"))
  end

  local summary_text = ViewModel.format_apply_summary(result)
  if dry_run then
    if summary_text then
      return "Dry run complete: " .. summary_text
    end
    local count = result.items and #result.items or 0
    return string.format("Dry run complete: %s (%d items)", result.message or "done", count)
  end

  if summary_text then
    if result.success then
      return "Apply complete: " .. text.repair_mojibake(summary_text)
    end
    return "Partial update: " .. text.repair_mojibake(summary_text) .. " — see Process Output"
  end

  if result.success then
    return string.format(
      "Apply complete: %s",
      text.repair_mojibake(result.message or "done")
    )
  end

  if result.errors and #result.errors > 0 then
    local primary = text.repair_mojibake(result.errors[1])
    if #result.errors > 1 then
      return string.format(
        "Apply failed (%d issues). %s — see Process Output",
        #result.errors,
        primary
      )
    end
    return "Apply failed: " .. primary
  end

  return text.repair_mojibake("Apply failed: " .. (result.message or "unknown error"))
end

function ViewModel.format_elevation_status(result, err)
  if not result then
    return "Elevation check failed: " .. tostring(err or "unknown")
  end
  if result.elevated then
    return "Running with administrator/root privileges"
  end
  if result.spawned then
    return "UAC elevation prompt launched — approve to continue"
  end
  if result.suggested_sudo then
    return "Re-run with: " .. result.suggested_sudo
  end
  if result.suggested then
    return result.suggested
  end
  return result.message or "Elevation required for real apply"
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
