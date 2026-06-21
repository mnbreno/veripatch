-- VeriPatch GUI view-model (pure logic, no wx dependencies)

local config = require("app.config")

local ViewModel = {}

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
  local text = string.format(
    "OS: %s | Version: %s | Arch: %s | Elevated: %s",
    os.os_type or "?",
    os.version or "?",
    os.architecture or "?",
    elevated
  )
  if os.distro_name then
    text = text .. " | Distro: " .. os.distro_name
  end
  return text, nil
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

function ViewModel.format_update_rows(upd_result, upd_err)
  local rows = {}
  if upd_result and upd_result.updates and upd_result.updates.items then
    for _, item in ipairs(upd_result.updates.items) do
      table.insert(rows, item.title .. " [" .. item.source_id .. "]")
    end
    return rows, ViewModel.STATUS.LOADED
  end
  table.insert(rows, "Failed to check updates: " .. tostring(upd_err or "unknown"))
  return rows, ViewModel.STATUS.LOAD_FAILED
end

function ViewModel.apply_button_label(dry_run)
  if dry_run then
    return "Apply (Dry Run)"
  end
  return "Apply Updates"
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

function ViewModel.build_apply_params(dry_run, confirmed, confirm_token)
  local params = { dry_run = dry_run }
  if not dry_run then
    params.confirm = confirmed
    params.confirm_token = confirm_token
  end
  return params
end

function ViewModel.format_apply_status(result, err, dry_run)
  if not result then
    return "Apply failed: " .. tostring(err or "unknown error")
  end
  local count = result.items and #result.items or 0
  if dry_run then
    return string.format("Dry run complete: %s (%d items)", result.message or "done", count)
  end
  if result.success then
    return string.format("Apply complete: %s (%d items)", result.message or "done", count)
  end
  local error_text = result.errors and result.errors[1] or result.message or "Apply failed"
  return "Apply failed: " .. error_text
end

function ViewModel.format_backend_error(context, err)
  return string.format("%s: %s", context, tostring(err or "unknown backend error"))
end

return ViewModel
