$base = "http://127.0.0.1:8000"
$loginBody = @{ username = "admin"; password = "admin123" } | ConvertTo-Json -Compress
$loginResp = Invoke-WebRequest -Uri "$base/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
$token = ($loginResp.Content | ConvertFrom-Json).access_token

foreach ($voice in @('longanlingxi', 'longanhuan_v3.6', 'longanlingxin', 'longanlufeng')) {
    $body = @{ text = "测试"; voice = $voice } | ConvertTo-Json -Compress
    $url = "$base/api/settings/tts/test"
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add('Authorization', "Bearer $token")
    $wc.Headers.Add('Content-Type', 'application/json')
    Write-Host "=== voice=$voice ==="
    try {
        $resp = $wc.UploadString($url, 'POST', $body)
        Write-Host ("OK len={0}" -f $resp.Length)
    } catch [System.Net.WebException] {
        $we = $_.Exception
        $resp = $we.Response
        if ($resp -ne $null) {
            Write-Host ("STATUS={0}" -f $resp.StatusCode)
            $sr = $resp.GetResponseStream()
            $rdr = New-Object System.IO.StreamReader($sr)
            $txt = $rdr.ReadToEnd()
            Write-Host ("BODY={0}" -f $txt)
        } else {
            Write-Host ("NO_RESPONSE msg={0}" -f $we.Message)
        }
    } catch {
        Write-Host ("OTHER msg={0}" -f $_.Exception.Message)
    }
    Start-Sleep -Milliseconds 500
}