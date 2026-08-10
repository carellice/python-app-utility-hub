Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = folder & "\.venv\Scripts\pythonw.exe"
app = folder & "\app.py"

If Not fso.FileExists(pythonw) Then
  MsgBox "Ambiente Python non configurato. Esegui prima setup_windows.bat", 48, "MP3 Tag Editor"
  WScript.Quit 1
End If

shell.CurrentDirectory = folder

args = ""
For Each item In WScript.Arguments
  args = args & " """ & item & """"
Next

shell.Run """" & pythonw & """ """ & app & """" & args, 0, False
