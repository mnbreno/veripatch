Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = scriptDir & "\start-backend.ps1"

port = 8765
projectRoot = fso.GetParentFolderName(scriptDir)
pythonExe = ""

If WScript.Arguments.Count >= 1 Then
  port = WScript.Arguments(0)
End If
If WScript.Arguments.Count >= 2 Then
  projectRoot = WScript.Arguments(1)
End If
If WScript.Arguments.Count >= 3 Then
  pythonExe = WScript.Arguments(2)
End If

quote = Chr(34)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & quote & ps1 & quote
cmd = cmd & " -Port " & port & " -ProjectRoot " & quote & projectRoot & quote & " -Restart"
If pythonExe <> "" Then
  cmd = cmd & " -PythonExe " & quote & pythonExe & quote
End If

shell.Run cmd, 0, False
