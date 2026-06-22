-- Headless UI/UX tests for VeriPatch view-model

package.path = "./gui/?.lua;./gui/?/init.lua;" .. package.path

local ViewModel = require("app.ui.view_model")
local config = require("app.config")

describe("ViewModel.format_os_label", function()
  it("formats OS info when backend succeeds", function()
    local text, status = ViewModel.format_os_label({
      os = {
        os_type = "windows",
        version = "10.0",
        architecture = "AMD64",
        distro_name = nil,
      },
      elevated = false,
    })
    assert.are.equal(nil, status)
    assert.is_true(text:find("windows") ~= nil)
    assert.is_true(text:find("Elevated: No") ~= nil)
  end)

  it("returns error label when backend fails", function()
    local text, status = ViewModel.format_os_label(nil, "connection refused")
    assert.are.equal(ViewModel.STATUS.OS_FAILED, status)
    assert.is_true(text:find("Backend error") ~= nil)
  end)
end)

describe("ViewModel.format_source_rows", function()
  it("maps official sources to display rows", function()
    local rows = ViewModel.format_source_rows({
      sources = {
        { id = "winget", name = "Microsoft WinGet" },
      },
    })
    assert.are.equal(1, #rows)
    assert.are.equal("Microsoft WinGet (winget)", rows[1])
  end)

  it("shows error row on failure", function()
    local rows, err = ViewModel.format_source_rows(nil, "timeout")
    assert.are.equal("source_error", err)
    assert.is_true(rows[1]:find("Failed to load sources") ~= nil)
  end)
end)

describe("ViewModel.format_update_rows", function()
  it("maps update items to list rows", function()
    local rows, status = ViewModel.format_update_rows({
      updates = {
        items = {
          {
            title = "Security Update",
            source_id = "winget",
            metadata = { package_id = "Vendor.App" },
          },
        },
      },
    })
    assert.are.equal(ViewModel.STATUS.LOADED, status)
    assert.are.equal("Security Update [winget]", rows[1])
  end)

  it("parses structured update items", function()
    local items = ViewModel.parse_update_items({
      updates = {
        items = {
          {
            id = "winget-cursor",
            title = "Cursor",
            source_id = "winget",
            metadata = { package_id = ViewModel.CURSOR_PACKAGE_ID },
          },
        },
      },
    })
    assert.are.equal(1, #items)
    assert.are.equal(ViewModel.CURSOR_PACKAGE_ID, items[1].package_id)
  end)

  it("returns load failed status on error", function()
    local rows, status = ViewModel.format_update_rows(nil, "rpc error")
    assert.are.equal(ViewModel.STATUS.LOAD_FAILED, status)
    assert.is_true(rows[1]:find("Failed to check updates") ~= nil)
  end)
end)

describe("ViewModel.apply confirmation flow", function()
  it("allows dry run without confirmation", function()
    local ok = ViewModel.can_apply_real(false, false, "")
    assert.is_false(ok)
  end)

  it("requires elevation and token for real apply", function()
    local ok, reason = ViewModel.can_apply_real(false, true, config.APPLY_CONFIRMATION_TOKEN)
    assert.is_false(ok)
    assert.is_true(reason:find("privileges") ~= nil)

    ok, reason = ViewModel.can_apply_real(true, false, config.APPLY_CONFIRMATION_TOKEN)
    assert.is_false(ok)
    assert.is_true(reason:find("Confirmation") ~= nil)

    ok = ViewModel.can_apply_real(true, true, config.APPLY_CONFIRMATION_TOKEN)
    assert.is_true(ok)
  end)

  it("builds apply params with confirmation for real apply", function()
    local params = ViewModel.build_apply_params(
      false,
      true,
      config.APPLY_CONFIRMATION_TOKEN
    )
    assert.is_false(params.dry_run)
    assert.is_true(params.confirm)
    assert.are.equal(config.APPLY_CONFIRMATION_TOKEN, params.confirm_token)
  end)

  it("formats apply status messages", function()
    local msg = ViewModel.format_apply_status({
      success = true,
      message = "done",
      items = { {}, {} },
    }, nil, true)
    assert.is_true(msg:find("Dry run complete") ~= nil)

    msg = ViewModel.format_apply_status(nil, "backend down", true)
    assert.is_true(msg:find("Apply failed") ~= nil)

    msg = ViewModel.format_apply_status({
      success = false,
      summary = { updated = 2, skipped = 1, failed = 1 },
    }, nil, false)
    assert.is_true(msg:find("2 updated") ~= nil)
    assert.is_true(msg:find("1 skipped") ~= nil)
    assert.is_true(msg:find("1 failed") ~= nil)
  end)

  it("builds apply params for selected packages and skip rules", function()
    local params = ViewModel.build_apply_params(
      false,
      true,
      config.APPLY_CONFIRMATION_TOKEN,
      {
        package_ids = { "chrox.Readest" },
        skip_package_ids = { ViewModel.CURSOR_PACKAGE_ID },
      }
    )
    assert.are.same({ "chrox.Readest" }, params.package_ids)
    assert.are.same({ ViewModel.CURSOR_PACKAGE_ID }, params.skip_package_ids)
  end)

  it("detects cursor gate conditions", function()
    local items = {
      { package_id = ViewModel.CURSOR_PACKAGE_ID, display = "Cursor [winget]" },
    }
    assert.is_true(ViewModel.should_prompt_cursor_gate(items, { cursor_running = true }))
    assert.is_false(ViewModel.should_prompt_cursor_gate(items, { cursor_running = false }))
  end)

  it("collects selected package ids from checked indices", function()
    local items = {
      { package_id = "chrox.Readest", display = "Readest [winget]" },
      { package_id = ViewModel.CURSOR_PACKAGE_ID, display = "Cursor [winget]" },
    }
    local package_ids = ViewModel.selected_package_ids(items, { 0 })
    assert.are.same({ "chrox.Readest" }, package_ids)
  end)

  it("formats elevation status messages", function()
    local msg = ViewModel.format_elevation_status({ elevated = true })
    assert.is_true(msg:find("administrator") ~= nil)

    msg = ViewModel.format_elevation_status({
      elevated = false,
      suggested_sudo = "sudo veripatch",
    })
    assert.is_true(msg:find("sudo veripatch") ~= nil)
  end)

  it("provides update-all labels and confirmation copy", function()
    assert.are.equal("Update All", ViewModel.update_all_button_label())
    assert.is_true(ViewModel.confirm_update_all_message():find("official sources") ~= nil)
    assert.is_true(ViewModel.confirm_elevation_message():find("Administrator") ~= nil)
  end)
end)
