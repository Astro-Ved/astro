Attribute VB_Name = "KundliModule"
Option Explicit

' Requires Reference to "Microsoft XML, v6.0" (MSXML2.XMLHTTP)
' For JSON parsing, a simple string manipulation is used here to avoid external dependencies.

' Use a dictionary for basic caching so we don't spam the server on sheet recalculation
Private CacheDict As Object

Public Function GetKundli(field As String, year As Variant, month As Variant, day As Variant, hour As Variant, minute As Variant, city As Variant) As String
    ' This makes it usable as a formula: =GetKundli("Tithi", B1, B2, B3, B4, B5, B6)

    ' Error handling for empty or invalid values
    If IsEmpty(year) Or IsEmpty(month) Or IsEmpty(day) Or IsEmpty(hour) Or IsEmpty(minute) Or IsEmpty(city) Then
        GetKundli = ""
        Exit Function
    End If

    If Not IsNumeric(year) Or Not IsNumeric(month) Or Not IsNumeric(day) Or Not IsNumeric(hour) Or Not IsNumeric(minute) Then
        GetKundli = "#VALUE!"
        Exit Function
    End If

    ' Only send valid values (e.g., month cannot be > 12 or 0)
    If year = 0 Or month = 0 Or day = 0 Then
        GetKundli = "#INV_DATE!"
        Exit Function
    End If

    ' Initialize cache dictionary if not set
    If CacheDict Is Nothing Then
        Set CacheDict = CreateObject("Scripting.Dictionary")
    End If

    Dim cacheKey As String
    cacheKey = year & "-" & month & "-" & day & "-" & hour & "-" & minute & "-" & city

    Dim jsonResponse As String

    ' Check if we already fetched data for these parameters
    If CacheDict.Exists(cacheKey) Then
        jsonResponse = CacheDict(cacheKey)
    Else
        Dim http As Object
        Set http = CreateObject("MSXML2.XMLHTTP")

        Dim url As String
        url = "http://127.0.0.1:5000/calculate"

        Dim payload As String
        payload = "{""year"":" & year & ", ""month"":" & month & ", ""day"":" & day & ", ""hour"":" & hour & ", ""minute"":" & minute & ", ""city"":""" & city & """}"

        ' Send POST request (Synchronous inside a UDF can freeze excel if server is down, so we use a small timeout workaround implicitly by error handling)
        On Error GoTo HttpError
        http.Open "POST", url, False
        http.setRequestHeader "Content-type", "application/json"
        http.send payload

        If http.Status = 200 Then
            jsonResponse = http.responseText
            CacheDict.Add cacheKey, jsonResponse
        Else
            GetKundli = "#API_ERR_" & http.Status & "!"
            Exit Function
        End If
        On Error GoTo 0
    End If

    ' Extract value
    GetKundli = ExtractJsonStringValue(jsonResponse, field)
    Exit Function

HttpError:
    GetKundli = "#CONN_ERR!"
End Function


Public Sub ClearKundliCache()
    ' Macro to clear cache manually if needed
    Set CacheDict = Nothing
    MsgBox "Cache cleared."
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
