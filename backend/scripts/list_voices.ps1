$base = "http://127.0.0.1:8000"
$loginBody = @{ username = "admin"; password = "admin123" } | ConvertTo-Json -Compress
$loginResp = Invoke-WebRequest -Uri "$base/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
$token = ($loginResp.Content | ConvertFrom-Json).access_token

$r = Invoke-WebRequest -Uri "$base/api/settings/voice/info" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
[System.IO.File]::WriteAllText("D:\StudyNote\Mian02\backend\scripts\voice_info.json", $r.Content, [System.Text.Encoding]::UTF8)
Write-Host "WROTE $($r.Content.Length) bytes"