#!/usr/bin/env python3
"""LA PORTE D'ENTRÉE — par où contacter réellement ce prospect.

    python3 outils/porte_entree.py                    # toutes les pages conservées
    python3 outils/porte_entree.py --page fichier.html --url https://…

La règle vit dans `radar/porte.py` et nulle part ailleurs : cet outil ne fait
que l'appliquer aux pages conservées et l'afficher. Deux copies d'une règle
finissent toujours par diverger.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from radar.porte import lire                                     # noqa: E402

PAGES = RACINE / "validation" / "pages_reelles"


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description="Où contacter réellement ce prospect")
    p.add_argument("--page", help="un fichier HTML précis")
    p.add_argument("--url", default="", help="URL de la page, pour résoudre un lien relatif")
    p.add_argument("--json", action="store_true", help="sortie machine")
    a = p.parse_args(argv)

    if a.page:
        lots = [(Path(a.page), a.url)]
    else:
        lots = []
        for f in sorted(PAGES.glob("*.html")):
            meta = f.with_suffix(".meta.json")
            url = ""
            if meta.exists():
                try:
                    url = json.loads(meta.read_text(encoding="utf-8")).get("url", "")
                except (json.JSONDecodeError, OSError):
                    url = ""
            lots.append((f, url))

    if not lots:
        print("aucune page conservée à mesurer", file=sys.stderr)
        return 2

    sorties = []
    for chemin, url in lots:
        porte = lire(chemin.read_text(encoding="utf-8", errors="replace"), url)
        sorties.append({"fichier": chemin.name, **porte.en_dict()})
        if not a.json:
            print(f"\n── {chemin.name}")
            print(f"  url                {url or '—'}")
            for ligne in (porte.en_lignes() or ["PORTE D'ENTRÉE AUCUNE OBSERVÉE"]):
                print(f"  {ligne}")

    if a.json:
        print(json.dumps(sorties, ensure_ascii=False, indent=1))
        return 0

    sure = sum(1 for m in sorties if m["certitude"] == "OBSERVÉE")
    douteux = sum(1 for m in sorties if m["certitude"] == "À VÉRIFIER")
    print(f"\n{sure} porte(s) OBSERVÉE(S) · {douteux} À VÉRIFIER · "
          f"{len(sorties) - sure - douteux} sans porte, sur {len(sorties)} page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
