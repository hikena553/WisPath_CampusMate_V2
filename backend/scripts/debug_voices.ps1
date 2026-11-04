$ErrorActionPreference = 'Continue'

$base = "http://localhost:8000"

$token = $null
try {
  $login = Invoke-RestMethod -Uri "$base/api/auth/login" -Method POST -ContentType 'application/json' -Body '{"username":"admin","password":"admin123"}'
  $token = $login.access_token
  Write-Host ("LOGIN OK role={0}" -f $login.user.role)
} catch {
  Write-Host ("LOGIN FAIL: {0} {1}" -f $_.Exception.Response.StatusCode.value__, $_.Exception.Message)
  exit 1
}

$probes = @('longanlingxi_v3.1', 'longanlingxi', 'longanhuan_v3.6', 'longanlingxin')

foreach ($voice in $probes) {
  $body = @{ text = '测试'; voice = $voice } | ConvertTo-Json -Compress
  $url = "$base/api/settings/tts/test"
  Write-Host "`n=== voice=$voice ==="
  $wc = New-Object System.Net.WebClient
  $wc.Headers.Add('Authorization', "Bearer $token")
  $wc.Headers.Add('Content-Type', 'application/json')
  try {
    $resp = $wc.UploadString($url, 'POST', $body)
    Write-Host ("OK response len={0}" -f $resp.Length)
  } catch [System.Net.WebException] {
    $ex = $_.Exception
    $resp = $ex.Response
    if ($resp) {
      $stream = $resp.GetResponseStream()
      $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
      $bodyText = $reader.ReadToEnd()
      Write-Host ("FAIL status={0} body={1}" -f [int]$resp.StatusCode, $bodyText)
    } else {
      Write-Host ("FAIL no resp: {0}" -f $ex.Message)
    }
  } catch {
    Write-Host ("OTHER: {0}" -f $_.Exception.Message)
  } finally {
    $wc.Dispose()
  }
}
