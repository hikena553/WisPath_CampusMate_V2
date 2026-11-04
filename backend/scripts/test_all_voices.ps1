param(
    [string]$Base = "http://127.0.0.1:8000",
    [string]$LoginUser = "admin",
    [string]$LoginPass = "admin123"
)

$ErrorActionPreference = "Continue"

function Safe-Invoke($method, $url, $token, $bodyJson) {
    if ($method -eq 'GET') {
        try {
            $resp = Invoke-WebRequest -Uri $url -Headers (@{ Authorization = "Bearer $token" }) -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
            return @{ ok = $true; status = [int]$resp.StatusCode; text = $resp.Content }
        } catch {
            $we = $_.Exception
            $resp = $we.Response
            if ($resp -ne $null) {
                $code = [int]$resp.StatusCode
                $sr = $resp.GetResponseStream()
                $rdr = New-Object System.IO.StreamReader($sr)
                $txt = $rdr.ReadToEnd()
                return @{ ok = $false; status = $code; text = $txt }
            }
            return @{ ok = $false; status = 0; text = $we.Message }
        }
    } else {
        try {
            $resp = Invoke-WebRequest -Uri $url -Method POST -Headers (@{ Authorization = "Bearer $token"; 'Content-Type' = 'application/json' }) -Body $bodyJson -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
            return @{ ok = $true; status = [int]$resp.StatusCode; text = $resp.Content }
        } catch {
            $we = $_.Exception
            $resp = $we.Response
            if ($resp -ne $null) {
                $code = [int]$resp.StatusCode
                $sr = $resp.GetResponseStream()
                $rdr = New-Object System.IO.StreamReader($sr)
                $txt = $rdr.ReadToEnd()
                return @{ ok = $false; status = $code; text = $txt }
            }
            return @{ ok = $false; status = 0; text = $we.Message }
        }
    }
}

# 1) 启动后端
$logsDir = "D:\StudyNote\Mian02\backend\logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }
$errLog = Join-Path $logsDir "uvicorn.err.log"
$outLog = Join-Path $logsDir "uvicorn.out.log"
Remove-Item $errLog -ErrorAction SilentlyContinue
Remove-Item $outLog -ErrorAction SilentlyContinue

Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } catch {} }
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$proc = Start-Process -FilePath "D:\conda\envs\mianyang\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory "D:\StudyNote\Mian02\backend" -RedirectStandardOutput $outLog -RedirectStandardError $errLog -WindowStyle Hidden -PassThru
Write-Host "backend pid=$($proc.Id)"

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    $h = Safe-Invoke 'GET' "$Base/api/health" $null $null
    if ($h.ok) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Write-Host "BACKEND NOT READY"; Get-Content $errLog -Tail 30; exit 1 }
Write-Host "backend ready"

# 2) 登录
$loginBody = (@{ username = $LoginUser; password = $LoginPass } | ConvertTo-Json -Compress)
$lr = Safe-Invoke 'POST' "$Base/api/auth/login" $null $loginBody
if (-not $lr.ok) { Write-Host "LOGIN_FAIL $($lr.status) $($lr.text)"; Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; exit 1 }
$infoText = $lr.text.TrimStart([char]0xFEFF)
$token = ($infoText | ConvertFrom-Json).access_token
Write-Host "token_len=$($token.Length)"

# 3) 拿音色目录
$ir = Safe-Invoke 'GET' "$Base/api/settings/voice/info" $token $null
if (-not $ir.ok) { Write-Host "INFO_FAIL $($ir.status) $($ir.text)"; Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; exit 1 }
[System.IO.File]::WriteAllText("D:\StudyNote\Mian02\backend\scripts\voice_info_dump.txt", $ir.text, [System.Text.Encoding]::UTF8)
$infoText = $ir.text.TrimStart([char]0xFEFF)
$info = $infoText | ConvertFrom-Json

# 4) 逐个测试
$results = New-Object System.Collections.Generic.List[object]
$total = 0; $okCount = 0
foreach ($g in $info.voice_groups) {
    foreach ($v in $g.voices) {
        $total++
        $voice = $v.voice
        $model = $g.model
        $body = (@{ text = "测试"; voice = $voice } | ConvertTo-Json -Compress)
        $r = Safe-Invoke 'POST' "$Base/api/settings/tts/test" $token $body
        $entry = [ordered]@{ model = $model; voice = $voice; status = $r.status; ok = $r.ok; size = $r.text.Length; detail = "" }
        if ($r.ok) { $okCount++ } else { $entry.detail = $r.text }
        $results.Add([PSCustomObject]$entry)
        $tag = if ($r.ok) { "OK " } else { "ERR" }
        Write-Host ("[{0}] {1,-32} {2,-26} status={3,-4} bytes={4,-7} {5}" -f $tag, $model, $voice, $r.status, $r.text.Length, $r.text)
        Start-Sleep -Milliseconds 250
    }
}

# 5) 写结果
[System.IO.File]::WriteAllText("D:\StudyNote\Mian02\backend\scripts\voice_test_results.json", ($results | ConvertTo-Json -Depth 6), [System.Text.Encoding]::UTF8)
Write-Host ""
Write-Host "TOTAL=$total OK=$okCount FAIL=$($total - $okCount)"

# 6) 关掉后端
try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}