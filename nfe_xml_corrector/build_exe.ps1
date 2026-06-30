$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --specpath "$ProjectRoot\build" `
  --name "CorretorXMLNFe" `
  "nfe_xml_corrector\app.py"

Write-Host ""
Write-Host "Executavel gerado em: $ProjectRoot\dist\CorretorXMLNFe.exe"
