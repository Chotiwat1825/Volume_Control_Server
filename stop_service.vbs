Set WshShell = CreateObject("WScript.Shell")
' ค้นหาและปิด pythonw.exe ที่รัน app.py
WshShell.Run "taskkill /f /im pythonw.exe", 0, True
Set WshShell = Nothing 