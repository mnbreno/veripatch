#!/usr/bin/env lua
-- Headless view-model smoke tests (no busted required).

package.path = "./gui/?.lua;./gui/?/init.lua;" .. package.path

local function assert_eq(actual, expected, message)
  if actual ~= expected then
    error((message or "assert_eq failed") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
  end
end

local function assert_true(value, message)
  if not value then
    error(message or "assert_true failed")
  end
end

local function assert_same(actual, expected, message)
  if type(actual) ~= "table" or type(expected) ~= "table" then
    assert_eq(actual, expected, message)
    return
  end
  assert_eq(#actual, #expected, message or "table length mismatch")
  for index = 1, #actual do
    assert_eq(actual[index], expected[index], message)
  end
end

local ViewModel = require("app.ui.view_model")
local config = require("app.config")

local tests_run = 0

local function test(name, fn)
  tests_run = tests_run + 1
  local ok, err = pcall(fn)
  if not ok then
    io.stderr:write(string.format("FAIL %s: %s\n", name, err))
    os.exit(1)
  end
  io.write(string.format("ok %s\n", name))
end

test("parse_update_items", function()
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
  assert_eq(#items, 1)
  assert_eq(items[1].package_id, ViewModel.CURSOR_PACKAGE_ID)
end)

test("build_apply_params", function()
  local params = ViewModel.build_apply_params(
    false,
    true,
    config.APPLY_CONFIRMATION_TOKEN,
    {
      package_ids = { "chrox.Readest" },
      skip_package_ids = { ViewModel.CURSOR_PACKAGE_ID },
    }
  )
  assert_same(params.package_ids, { "chrox.Readest" })
  assert_same(params.skip_package_ids, { ViewModel.CURSOR_PACKAGE_ID })
end)

test("cursor_gate", function()
  local items = {
    { package_id = ViewModel.CURSOR_PACKAGE_ID, display = "Cursor [winget]" },
  }
  assert_true(ViewModel.should_prompt_cursor_gate(items, { cursor_running = true, cursor_update_available = true }))
  assert_eq(ViewModel.should_prompt_cursor_gate(items, { cursor_running = false }), false)
end)

test("selected_package_ids", function()
  local items = {
    { package_id = "chrox.Readest", display = "Readest [winget]" },
    { package_id = ViewModel.CURSOR_PACKAGE_ID, display = "Cursor [winget]" },
  }
  assert_same(ViewModel.selected_package_ids(items, { 0 }), { "chrox.Readest" })
end)

test("format_apply_summary", function()
  local summary = ViewModel.format_apply_summary({
    summary = { updated = 2, skipped = 1, failed = 1 },
  })
  assert_true(summary:find("2 updated") ~= nil)
  assert_true(summary:find("1 skipped") ~= nil)
  assert_true(summary:find("1 failed") ~= nil)
end)

io.write(string.format("\nAll %d view-model smoke tests passed.\n", tests_run))
