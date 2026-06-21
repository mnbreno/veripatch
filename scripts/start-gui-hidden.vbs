Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = scriptDir & "\start-gui.ps1"
logPath = shell.ExpandEnvironmentStrings("%TEMP%") & "\veripatch-launch.log"

quote = Chr(34)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & quote & ps1 & quote
exitCode = shell.Run(cmd, 0, True)

If exitCode <> 0 Then
  message = "VeriPatch failed to start." & vbCrLf & vbCrLf
  message = message & "See the launch log for details:" & vbCrLf
  message = message & logPath
  shell.Popup message, 0, "VeriPatch", 16
End If
