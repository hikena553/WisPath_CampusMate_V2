param(
  [Parameter(Mandatory=$true)][string]$InFile,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [int]$Width = 1920,
  [int]$Height = 1080,
  [string]$Slides = ""
)
$ErrorActionPreference = 'Stop'
$InFile = (Resolve-Path $InFile).Path
if (!(Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$OutDir = (Resolve-Path $OutDir).Path
$pp = $null
$pres = $null
try {
  $pp = New-Object -ComObject PowerPoint.Application
  $pp.Visible = -1
  $pres = $pp.Presentations.Open($InFile, -1, 0, -1)
  $count = $pres.Slides.Count
  $idx = @()
  if ($Slides -ne "") { $idx = $Slides.Split(',') | ForEach-Object { [int]$_.Trim() } } else { $idx = 1..$count }
  $manifest = @()
  foreach ($i in $idx) {
    $file = Join-Path $OutDir ("slide-{0:D2}.png" -f $i)
    $pres.Slides.Item($i).Export($file, "PNG", $Width, $Height)
    $manifest += [pscustomobject]@{ slide = $i; exists = (Test-Path $file); size = (Get-Item $file).Length }
  }
  $manifest | ConvertTo-Json -Compress
} finally {
  if ($pres -ne $null) { $pres.Close() }
  if ($pp -ne $null) { $pp.Quit() }
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) 2>$null | Out-Null
  [GC]::Collect()
}
