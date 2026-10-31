param([Parameter(Mandatory=$true)][string]$InFile, [switch]$Json)
$ErrorActionPreference = 'Stop'
$InFile = (Resolve-Path $InFile).Path
$pp = $null; $pres = $null
$rows = @()
try {
  $pp = New-Object -ComObject PowerPoint.Application
  $pp.Visible = -1
  $pres = $pp.Presentations.Open($InFile, -1, 0, 0)
  Write-Output ("SLIDES=" + $pres.Slides.Count)
  for ($i = 1; $i -le $pres.Slides.Count; $i++) {
    $s = $pres.Slides.Item($i)
    $seq = $s.TimeLine.MainSequence
    $trig = @{}
    $durs = @()
    for ($k = 1; $k -le $seq.Count; $k++) {
      $e = $seq.Item($k)
      $tt = [int]$e.Timing.TriggerType
      if ($trig.ContainsKey($tt)) { $trig[$tt]++ } else { $trig[$tt] = 1 }
      $durs += [math]::Round($e.Timing.Duration, 2)
    }
    $t = $s.SlideShowTransition
    $rows += [pscustomobject]@{
      slide = $i
      effects = $seq.Count
      trigger = (($trig.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Value)" }) -join ",")
      durMin = if ($durs.Count) { ($durs | Measure-Object -Minimum).Minimum } else { 0 }
      durMax = if ($durs.Count) { ($durs | Measure-Object -Maximum).Maximum } else { 0 }
      entry = [int]$t.EntryEffect
      advTime = $t.AdvanceTime
      advOnTime = [bool]$t.AdvanceOnTime
    }
  }
  $rows | Format-Table -AutoSize | Out-String -Width 200
  if ($Json) { $rows | ConvertTo-Json -Compress }
} finally {
  if ($pres -ne $null) { $pres.Close() }
  if ($pp -ne $null) { $pp.Quit() }
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) 2>$null | Out-Null
  [GC]::Collect()
}