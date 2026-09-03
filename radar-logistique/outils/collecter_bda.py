#!/usr/bin/env python3
"""Collecteur BDA — à lancer depuis une machine ayant un accès réseau.

    python3 outils/collecter_bda.py --pages 5 --sortie bda-brut.json
    python  -m radar.cli recenser --source bda --echantillon bda-brut.json

Deux règles non négociables, appliquées avant toute lecture :

  1. le robots.txt est consulté ; un chemin interdit N'EST PAS lu ;
  2. le délai entre requêtes est celui du robots.txt, jamais moins que 2,5 s.

Si le robots.txt est illisible, le script s'ARRÊTE : ne pas savoir n'autorise
pas. Et il ne prétend jamais avoir réussi — un échec sort avec un code non nul.

AVERTISSEMENT : les sélecteurs de sources/bda.yaml n'ont PAS été vérifiés sur
la vraie page. Si l'extraction ne rend rien, le script enregistre le HTML brut
pour que les sélecteurs soient corrigés sur pièces.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                    # noqa: E402

from radar import robots                                       # noqa: E402
from radar.extraction import extraire                          # noqa: E402


def lire(url: str, agent: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": agent, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:800]
    except urllib.error.URLError as e:
        return 0, f"réseau injoignable : {e.reason}"


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description="Collecte des avis du BDA")
    p.add_argument("--pages", type=int, default=5)
    p.add_argument("--recherche", default="transport")
    p.add_argument("--sortie", default="bda-brut.json")
    p.add_argument("--html-brut", default="bda-pages",
                   help="dossier où déposer le HTML si l'extraction échoue")
    a = p.parse_args(argv)

    cfg = yaml.safe_load((RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8"))
    nav = cfg["navigation"]
    agent = nav["agent"]

    # ── 1. robots.txt, avant toute lecture ──
    regles = robots.recuperer(nav["base_url"], agent=agent.split("/")[0].lower())
    if not regles.lu:
        print(f"robots.txt illisible ({regles.erreur}) — arrêt.", file=sys.stderr)
        print("Ne pas savoir n'autorise pas : aucune page ne sera lue.", file=sys.stderr)
        return 2
    autorise, motif = regles.chemin_autorise(nav["url_recherche"])
    print(f"robots.txt : {motif} · délai imposé {regles.delai:g} s")
    if not autorise:
        print("Chemin interdit par robots.txt — arrêt, sans contournement.", file=sys.stderr)
        return 3
    delai = max(regles.delai, nav.get("delai_minimum_s", 2.5))

    # ── 2. pagination ──
    tout, pages_brutes = [], []
    for page in range(1, min(a.pages, nav.get("pages_max", 20)) + 1):
        params = urllib.parse.urlencode({nav.get("parametre_recherche", "q"): a.recherche,
                                         nav.get("parametre_page", "page"): page})
        url = f"{nav['url_recherche']}?{params}"
        statut, contenu = lire(url, agent)
        time.sleep(delai)

        if statut != 200:
            print(f"\nÉCHEC page {page} — code {statut}", file=sys.stderr)
            print(contenu[:400], file=sys.stderr)
            if not tout:
                return 4
            break

        lignes = extraire(contenu, cfg, base_url=nav["base_url"])
        pages_brutes.append((page, contenu))
        if not lignes:
            print(f"page {page} : reçue ({len(contenu)} octets) mais AUCUNE ligne extraite.")
            print("   → les sélecteurs de sources/bda.yaml ne correspondent pas à la page.")
            break
        neufs = [l for l in lignes if l not in tout]
        tout += neufs
        print(f"page {page:>3} : {len(lignes):>4} lignes, {len(neufs):>4} nouvelles "
              f"(total {len(tout)})")
        if not neufs:
            print("fin de pagination.")
            break

    # ── 3. sortie ──
    if not tout:
        dossier = Path(a.html_brut)
        dossier.mkdir(parents=True, exist_ok=True)
        for page, contenu in pages_brutes:
            (dossier / f"page-{page}.html").write_text(contenu, encoding="utf-8")
        print(f"\nAucune ligne extraite. {len(pages_brutes)} page(s) HTML brute(s) "
              f"enregistrée(s) dans {dossier}/", file=sys.stderr)
        print("Corrige les sélecteurs dans sources/bda.yaml sur ces pages, "
              "PAS dans le code.", file=sys.stderr)
        return 5

    Path(a.sortie).write_text(json.dumps(tout, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    cles = sorted({k for l in tout for k in l})
    print(f"\n{len(tout)} avis écrits dans {a.sortie}")
    print(f"champs réellement extraits : {', '.join(cles)}")
    manquants = [c for c in cfg["navigation"]["champs"] if c not in cles]
    if manquants:
        print(f"champs DÉCLARÉS mais jamais trouvés : {', '.join(manquants)}")
        print("→ sélecteurs à corriger dans sources/bda.yaml")
    print(f"\nÉtape suivante :\n"
          f"  python -m radar.cli recenser --source bda --echantillon {a.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
