#!/bin/sh
# ═══════════════════════════════════════════════════════════════════
#  RADAR COMMERCIAL — lanceur Linux / macOS
#
#      ./radar.sh analyse-du-jour --import mon-export.tsv
#      ./radar.sh opportunites
#      ./radar.sh statut
#
#  Sous Windows, le lanceur s'appelle radar.cmd et s'invoque « radar ».
#  Rien à installer : bibliothèque standard de Python, plus PyYAML.
#
#  Le fichier ne peut pas s'appeler « radar » tout court : c'est déjà le
#  nom du paquet Python, et les deux se marcheraient dessus.
# ═══════════════════════════════════════════════════════════════════
RACINE="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$RACINE:$PYTHONPATH"
export PYTHONPATH
export PYTHONIOENCODING=utf-8

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo
  echo "  PYTHON INTROUVABLE"
  echo
  echo "  Installez Python 3.11 ou plus récent."
  echo
  exit 2
fi

exec "$PY" -m radar.cli "$@"
