Attribute VB_Name = "KundliModule"
Option Explicit

' Requires Reference to "Microsoft XML, v6.0" (MSXML2.XMLHTTP)
' For JSON parsing, a simple string manipulation is used here to avoid external dependencies.
' In a real-world scenario, importing a library like VBA-JSON is recommended.

Public Sub CalculateKundli()
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")

    Dim url As String
    url = "http://127.0.0.1:5000/calculate"

    ' Read values from the active sheet (adjust cell references as needed)
    Dim ws As Worksheet
    Set ws = ActiveSheet

    Dim year As String
    Dim month As String
    Dim day As String
    Dim hour As String
    Dim minute As String
    Dim city As String

    ' Assuming the inputs are in cells B1 to B6
    year = ws.Range("B1").Value
    month = ws.Range("B2").Value
    day = ws.Range("B3").Value
    hour = ws.Range("B4").Value
    minute = ws.Range("B5").Value
    city = ws.Range("B6").Value

    ' Basic validation
    If year = "" Or month = "" Or day = "" Or hour = "" Or minute = "" Or city = "" Then
        MsgBox "Please fill in all input fields (B1 to B6)."
        Exit Sub
    End If

    ' Construct JSON payload
    Dim payload As String
    payload = "{""year"":" & year & ", ""month"":" & month & ", ""day"":" & day & ", ""hour"":" & hour & ", ""minute"":" & minute & ", ""city"":""" & city & """}"

    ' Send POST request
    http.Open "POST", url, False
    http.setRequestHeader "Content-type", "application/json"

    On Error GoTo HttpError
    http.send payload
    On Error GoTo 0

    Dim responseText As String
    responseText = http.responseText

    ' Basic JSON Parsing using string functions
    Dim tithi As String
    tithi = ExtractJsonStringValue(responseText, "Tithi")

    Dim nakshatra As String
    nakshatra = ExtractJsonStringValue(responseText, "Nakshatra")

    Dim yoga As String
    yoga = ExtractJsonStringValue(responseText, "Yoga")

    Dim karana As String
    karana = ExtractJsonStringValue(responseText, "Karana")

    Dim vara As String
    vara = ExtractJsonStringValue(responseText, "Vara")

    Dim rashi As String
    rashi = ExtractJsonStringValue(responseText, "Rashi")

    Dim lagna As String
    lagna = ExtractJsonStringValue(responseText, "Lagna")

    Dim gana As String
    gana = ExtractJsonStringValue(responseText, "Gana")

    Dim nadi As String
    nadi = ExtractJsonStringValue(responseText, "Nadi")

    ' Write outputs (adjust cell references as needed)
    ws.Range("E1").Value = tithi
    ws.Range("E2").Value = nakshatra
    ws.Range("E3").Value = yoga
    ws.Range("E4").Value = karana
    ws.Range("E5").Value = vara
    ws.Range("E6").Value = rashi
    ws.Range("E7").Value = lagna
    ws.Range("E8").Value = gana
    ws.Range("E9").Value = nadi

    MsgBox "Kundli Calculation Complete!"
    Exit Sub

HttpError:
    MsgBox "Error communicating with Python API. Make sure the Flask server is running."
End Sub

Private Function ExtractJsonStringValue(jsonStr As String, key As String) As String
    Dim searchKey As String
    searchKey = """" & key & """"

    Dim startPos As Integer
    startPos = InStr(jsonStr, searchKey)

    If startPos > 0 Then
        startPos = startPos + Len(searchKey)
        ' Find the colon after the key
        startPos = InStr(startPos, jsonStr, ":")
        If startPos > 0 Then
            startPos = startPos + 1
            ' Find the first double quote for the value
            startPos = InStr(startPos, jsonStr, """")
            If startPos > 0 Then
                startPos = startPos + 1
                Dim endPos As Integer
                endPos = InStr(startPos, jsonStr, """")
                If endPos > startPos Then
                    ExtractJsonStringValue = Mid(jsonStr, startPos, endPos - startPos)
                End If
            End If
        End If
    Else
        ExtractJsonStringValue = ""
    End If
End Function
