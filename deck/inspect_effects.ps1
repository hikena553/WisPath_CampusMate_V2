param([Parameter(Mandatory=$true)][string]$InFile)
$ErrorActionPreference = 'Stop'
$InFile = (Resolve-Path $InFile).Path
$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$pres = $pp.Presentations.Open($InFile, -1, 0, 0)
try {
  foreach ($si in @(3,6)) {
    $s = $pres.Slides.Item($si)
    $seq = $s.TimeLine.MainSequence
    Write-Output ("---- slide $si : $($seq.Count) effects ----")
    for ($k = 1; $k -le $seq.Count; $k++) {
      $e = $seq.Item($k)
      $name = ""
      try { $name = $e.Shape.Name } catch {}
      Write-Output ("{0,2}  type={1,-4} trig={2} dur={3,-5} delay={4,-5} shape={5}" -f $k, [int]$e.EffectType, [int]$e.Timing.TriggerType, [math]::Round($e.Timing.Duration,2), [math]::Round($e.Timing.TriggerDelayTime,2), $name)
    }
  }
} finally {
  $pres.Close(); $pp.Quit()
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) 2>$null | Out-Null
  [GC]::Collect()
}