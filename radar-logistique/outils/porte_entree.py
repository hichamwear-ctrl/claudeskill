#!/usr/bin/env python3
"""LA PORTE D'ENTRÉE — par où contacter réellement ce prospect.

    python3 outils/porte_entree.py                    # toutes les pages conservées
    python3 outils/porte_entree.py --page fichier.html --url https://…

POURQUOI CET OUTIL EXISTE, MESURÉ LE 2026-09-13
───────────────────────────────────────────────
Sur les deux prospects réels du 2026-09-12, le radar a répondu :

    Colis Privé  →  CONTACT  donnees-personnelles@colisprive.com
    DHL          →  CONTACT  AUCUN

Le premier est l'adresse du délégué à la protection des données : juridiquement
correcte, commercialement inutile. Le second est un cul-de-sac apparent.

Or les deux pages portent un formulaire de candidature : 17 champs de saisie
chez Colis Privé, 47 chez DHL. Sur 2 prospects sur 2, la porte d'entrée réelle
a été manquée. C'est un FAUX NÉGATIF D'ACTIONNABILITÉ : le commercial conclut
« pas de contact » devant une porte ouverte.

CE QUE CET OUTIL FAIT
─────────────────────
Il compte ce qui est matériellement présent dans la page. Rien n'est interprété :
un champ de saisie visible est un fait, pas une opinion.

CE QU'IL NE FAIT PAS
────────────────────
  · il n'entre PAS dans le moteur : ni état, ni score, ni nature, ni classement ;
  · il n'écrit PAS dans `lien_depot` — ce champ nourrit `depot_organise` dans
    procedure.py, donc la LECTURE D'ÉTAT. Y verser un formulaire privé ferait
    bouger l'état sans que personne l'ait demandé. Mesuré avant d'écrire une
    ligne, et évité ;
  · il n'invente aucune adresse et ne devine aucun destinataire.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

RACINE = Path(__file__).resolve().parent.parent
PAGES = RACINE / "validation" / "pages_reelles"

# Un champ de saisie dont le type sert à autre chose qu'à décrire un candidat.
TYPES_IGNORES = {"hidden", "submit", "button", "image", "reset", "search"}

# Ce qu'un formulaire de recherche porte, et qu'une candidature ne porte pas.
INDICES_RECHERCHE = ("search", "recherche", "zoek", "s=", "q=")


class Sonde(HTMLParser):
    """Compte ce qui est là. Ne juge rien."""

    def __init__(self):
        super().__init__()
        self.formulaires: list[dict] = []
        self._pile: list[dict] = []
        self.champs_hors_form = 0
        self.mailto: list[str] = []
        self.tel: list[str] = []

    def handle_starttag(self, balise, attrs):
        a = dict(attrs)
        if balise == "form":
            f = {"action": a.get("action"), "methode": (a.get("method") or "").lower(),
                 "champs": 0, "libelles": [], "types": []}
            self.formulaires.append(f)
            self._pile.append(f)
            return
        if balise in ("input", "textarea", "select"):
            t = (a.get("type") or ("textarea" if balise == "textarea" else "text")).lower()
            if t in TYPES_IGNORES:
                return
            etiquette = (a.get("placeholder") or a.get("name") or a.get("id") or "").strip()
            if self._pile:
                f = self._pile[-1]
                f["champs"] += 1
                f["types"].append(t)
                if etiquette:
                    f["libelles"].append(etiquette)
            else:
                self.champs_hors_form += 1
            return
        if balise == "a":
            h = a.get("href", "")
            if h.startswith("mailto:"):
                self.mailto.append(h[7:].split("?")[0])
            elif h.startswith("tel:"):
                self.tel.append(h[4:])

    def handle_endtag(self, balise):
        if balise == "form" and self._pile:
            self._pile.pop()


def _ressemble_a_une_recherche(f: dict) -> bool:
    """Un formulaire d'un seul champ dont l'action ou le nom parle de recherche."""
    if f["champs"] > 2:
        return False
    signature = " ".join([str(f.get("action") or "")] + f["libelles"]).lower()
    return any(i in signature for i in INDICES_RECHERCHE)


def mesurer(html: str, url: str = "") -> dict:
    s = Sonde()
    s.feed(html)

    candidatures = [f for f in s.formulaires
                    if f["champs"] >= 3 and not _ressemble_a_une_recherche(f)]
    total_champs = sum(f["champs"] for f in s.formulaires) + s.champs_hors_form

    # Un formulaire construit en JavaScript n'a pas de balise <form> : DHL en
    # est la preuve, 47 champs et zéro <form>. On compte donc les champs, pas
    # les balises. C'est ce qui distingue « pas de porte » de « porte non
    # balisée ».
    if candidatures:
        # Une balise <form> avec ses champs : c'est une porte, constatée.
        forme = "formulaire balisé"
        certitude = "OBSERVÉE"
        champs = max(f["champs"] for f in candidatures)
        action = next((f["action"] for f in candidatures if f["action"]), None)
        lien = urljoin(url, action) if (action and url) else action
    elif total_champs >= 3:
        # Des champs de saisie sans <form> autour. Ce PEUT être un formulaire
        # construit en JavaScript — DHL, 47 champs, zéro balise — ou seulement
        # une barre de recherche et un login — pypi.org, 6 champs.
        #
        # Mesuré le 2026-09-13 : 16 · 47 · 6 champs sur trois pages réelles.
        # Trois points ne font pas un seuil. Fixer « au-dessus de 8 c'est une
        # candidature » serait ajuster une règle sur le corpus qui l'a inspirée
        # — l'erreur déjà payée deux fois sur ce projet. On ne tranche donc
        # pas : on rapporte le nombre et on le marque À VÉRIFIER.
        forme = "champs de saisie sans balise <form>"
        certitude = "À VÉRIFIER"
        champs = total_champs
        lien = url or None
    else:
        forme = None
        certitude = "AUCUNE"
        champs = 0
        lien = None

    emails = sorted(set(re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)))

    return {
        "url": url,
        "porte": forme,
        "certitude": certitude,
        "champs_a_remplir": champs,
        "lien_candidature": lien,
        "formulaires_balises": len(s.formulaires),
        "champs_hors_balise_form": s.champs_hors_form,
        "mailto": s.mailto,
        "telephone": s.tel,
        "emails_en_clair": emails,
        "exemples_de_champs": (candidatures[0]["libelles"][:10] if candidatures else []),
    }


def rendre(m: dict) -> str:
    L = [f"  url                {m['url'] or '—'}"]
    if m["porte"] and m["certitude"] == "OBSERVÉE":
        L.append(f"  PORTE D'ENTRÉE     {m['porte']} — {m['champs_a_remplir']} champs à remplir")
        L.append(f"  où postuler        {m['lien_candidature'] or 'URL de la page'}")
    elif m["porte"]:
        L.append(f"  PORTE D'ENTRÉE     À VÉRIFIER — {m['champs_a_remplir']} {m['porte']}")
        L.append(f"  où regarder        {m['lien_candidature'] or 'URL de la page'}")
    else:
        L.append("  PORTE D'ENTRÉE     AUCUNE OBSERVÉE — ni formulaire, ni champ de saisie")
    L.append(f"  mailto             {', '.join(m['mailto']) or 'AUCUN'}")
    L.append(f"  téléphone          {', '.join(m['telephone']) or 'AUCUN'}")
    L.append(f"  e-mails en clair   {', '.join(m['emails_en_clair']) or 'AUCUN'}")
    if m["exemples_de_champs"]:
        L.append(f"  ce qu'ils demandent  {' · '.join(m['exemples_de_champs'][:6])}")
    L.append(f"  (balises <form> {m['formulaires_balises']} · "
             f"champs hors <form> {m['champs_hors_balise_form']})")
    return "\n".join(L)


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
        m = mesurer(chemin.read_text(encoding="utf-8", errors="replace"), url)
        m["fichier"] = chemin.name
        sorties.append(m)
        if not a.json:
            print(f"\n── {chemin.name}")
            print(rendre(m))

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
