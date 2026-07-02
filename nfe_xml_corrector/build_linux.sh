#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --specpath "$PROJECT_ROOT/build" \
  --name "CorretorXMLNFe-linux-x86_64" \
  "nfe_xml_corrector/app.py"

chmod +x "$PROJECT_ROOT/dist/CorretorXMLNFe-linux-x86_64"
tar \
  -C "$PROJECT_ROOT/dist" \
  -czf "$PROJECT_ROOT/dist/CorretorXMLNFe-linux-x86_64.tar.gz" \
  "CorretorXMLNFe-linux-x86_64"

echo
echo "Pacote Linux gerado em: $PROJECT_ROOT/dist/CorretorXMLNFe-linux-x86_64.tar.gz"
