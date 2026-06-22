-- Shared UTF-8 helpers for wxLua controls

local utf8_lib = require("utf8")

local text = {}

function text.repair_mojibake(value)
  value = tostring(value or "")
  if value == "" or not value:find("Ã", 1, true) then
    return value
  end
  local bytes = {}
  for _, code in utf8_lib.codes(value) do
    if code > 255 then
      return value
    end
    bytes[#bytes + 1] = string.char(code)
  end
  local packed = table.concat(bytes)
  local chars = {}
  local ok, err = pcall(function()
    for code in utf8_lib.codes(packed) do
      chars[#chars + 1] = utf8_lib.char(code)
    end
  end)
  if not ok then
    return value
  end
  local repaired = table.concat(chars)
  if repaired ~= "" and not repaired:find("Ã", 1, true) then
    return repaired
  end
  return value
end

function text.to_wx_string(wx, value)
  value = text.repair_mojibake(value)
  if wx.wxString and wx.wxString.FromUTF8 then
    return wx.wxString.FromUTF8(value)
  end
  return value
end

return text
