# Builds all distribution artifacts at the repo root from plugins/.
#   <plugin>.plugin - Cowork/Desktop plugin bundle (zip of that plugin's root)
#   <skill>.skill   - per-skill zip for claude.ai chat upload
# Zip entries use forward slashes (required by skill/plugin loaders).

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$repoRoot = Split-Path $PSScriptRoot -Parent
$pluginsDir = Join-Path $repoRoot 'plugins'

function Add-DirToZip($zip, $rootDir, $entryPrefix) {
  # -Force: on SMB shares, dot-prefixed names (.claude-plugin) carry the DOS hidden
  # attribute and would otherwise be silently skipped, shipping manifest-less bundles.
  Get-ChildItem $rootDir -Recurse -File -Force | ForEach-Object {
    $rel = $_.FullName.Substring($rootDir.Length + 1) -replace '\\', '/'
    $entryName = if ($entryPrefix) { "$entryPrefix/$rel" } else { $rel }
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entryName) | Out-Null
  }
}

Get-ChildItem $pluginsDir -Directory | ForEach-Object {
  $pluginDir = $_.FullName
  $pluginName = $_.Name

  # Cowork/Desktop bundle: the whole plugin root (manifest + skills)
  $out = Join-Path $repoRoot ($pluginName + '.plugin')
  if (Test-Path $out) { Remove-Item $out -Force }
  $zip = [System.IO.Compression.ZipFile]::Open($out, 'Create')
  Add-DirToZip $zip $pluginDir ''
  $zip.Dispose()
  Write-Host "built $pluginName.plugin"

  # Per-skill zips for claude.ai chat
  Get-ChildItem (Join-Path $pluginDir 'skills') -Directory | ForEach-Object {
    $out = Join-Path $repoRoot ($_.Name + '.skill')
    if (Test-Path $out) { Remove-Item $out -Force }
    $zip = [System.IO.Compression.ZipFile]::Open($out, 'Create')
    Add-DirToZip $zip $_.FullName $_.Name
    $zip.Dispose()
    Write-Host "built $($_.Name).skill"
  }
}
