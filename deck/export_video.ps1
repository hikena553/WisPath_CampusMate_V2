param(
  [Parameter(Mandatory=$true)][string]$InFile,
  [Parameter(Mandatory=$true)][string]$OutFile,
  [int]$Height = 1080,
  [int]$Fps = 30
)
$ErrorActionPreference = 'Stop'
$InFile = (Resolve-Path $InFile).Path
$OutFile = [System.IO.Path]::GetFullPath($OutFile)
$dir = Split-Path $OutFile -Parent
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$pp = $null; $pres = $null
try {
  $pp = New-Object -ComObject PowerPoint.Application
  $pp.Visible = -1
  $pres = $pp.Presentations.Open($InFile, -1, 0, 0)
  $pres.CreateVideo($OutFile, -1, 5, $Height, $Fps, 85)
  $last = -1
  for ($i = 0; $i -lt 600; $i++) {
    Start-Sleep -Seconds 3
    $st = [int]$pres.CreateVideoStatus
    if ($st -ne $last) { Write-Output ("status=" + $st + " at " + (Get-Date -Format "HH:mm:ss")); $last = $st }
    if ($st -eq 3) { break }
    if ($st -eq 4) { throw "CreateVideo failed (status=4)" }
  }
  Write-Output ("final status=" + [int]$pres.CreateVideoStatus)
  if (Test-Path $OutFile) { Write-Output ("size=" + (Get-Item $OutFile).Length) } else { Write-Output "NO OUTPUT FILE" }
} finally {
  if ($pres -ne $null) { $pres.Close() }
  if ($pp -ne $null) { $pp.Quit() }
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) 2>$null | Out-Null
  [GC]::Collect()
}