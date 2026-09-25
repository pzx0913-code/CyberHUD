Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\Cyber HUD.lnk")
oShortcut.TargetPath = strDir & "\start_hud_silent.vbs"
oShortcut.WorkingDirectory = strDir
oShortcut.Description = "Cyberpunk Mecha Desktop HUD"
oShortcut.Save

