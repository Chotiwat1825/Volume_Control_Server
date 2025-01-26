Set WshShell = CreateObject("WScript.Shell")
' รัน app.py ด้วย pythonw และบันทึก path
WshShell.Run chr(34) & "pythonw" & Chr(34) & " " & Chr(34) & WshShell.CurrentDirectory & "\app.py" & Chr(34), 0
MsgBox "Media Control Service Started!", 64, "Service Status"
Set WshShell = Nothing 