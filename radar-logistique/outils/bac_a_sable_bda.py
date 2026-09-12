#!/usr/bin/env python3
"""BAC À SABLE — mesurer les sélecteurs BDA sur un HTML déposé à la main.

Le réseau sortant de cet environnement refuse `publicprocurement.be` : la
passerelle répond 403 au CONNECT. Les sélecteurs de `sources/bda.yaml` portent
donc `verifie: false` et le fichier le dit lui-même — « PLAUSIBLES, PAS
MESURÉS ».

Cet outil ne collecte rien et n'invente rien. Il attend qu'une page RÉELLE
soit déposée depuis une machine connectée, puis répond objectivement :

    quel sélecteur matche · combien d'éléments il retourne · combien de champs
    sont extraits · quels liens d'avis sont trouvés · lesquels retournent 0

    python3 outils/bac_a_sable_bda.py --html /chemin/vers/page-bda-reelle.html

Sans fichier, il n'affiche pas un résultat vide : il affiche NON MESURÉ, et
rappelle ce qui manque. C'est la différence entre « zéro élément trouvé » et
« on n'a jamais regardé ».

Bibliothèque standard uniquement, plus PyYAML comme le reste du dépôt.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml  # noqa: E402

from radar.extraction import analyser, extraire  # noqa: E402

PROFIL = RACINE / "sources" / "bda.yaml"


def _decrire(spec: dict) -> str:
    balise = spec.get("balise", "?")
    attrs = " ".join(f'{k}="{v}"' for k, v in (spec.get("attrs") or {}).items())
    bout = f"<{balise}{' ' + attrs if attrs else ''}>"
    if spec.get("attribut", "texte") != "texte":
        bout += f" → {spec['attribut']}"
    if spec.get("motif"):
        bout += f" ~ {spec['motif']}"
    return bout


def mesurer(html: str, profil: dict) -> dict:
    """Ce que les sélecteurs déclarés rendent RÉELLEMENT sur cette page."""
    racine = analyser(html)
    nav = profil.get("navigation") or {}
    spec_c = nav.get("conteneur") or {}
    spec_l = nav.get("ligne") or {}

    conteneurs = racine.trouver(spec_c.get("balise"), spec_c.get("attrs"))
    lignes = []
    for c in conteneurs:
        lignes += c.trouver(spec_l.get("balise"), spec_l.get("attrs"))

    champs = nav.get("champs") or {}
    compte = {nom: 0 for nom in champs}
    exemples: dict = {}
    for ligne in lignes:
        for nom, spec in champs.items():
            cibles = ligne.trouver(spec.get("balise"), spec.get("attrs"))
            if cibles:
                compte[nom] += 1
                exemples.setdefault(nom, (cibles[0].texte() or "")[:70])

    enregistrements = extraire(html, profil, nav.get("base_url"))
    liens = [e.get("lien_avis") for e in enregistrements if e.get("lien_avis")]
    return {"octets": len(html), "conteneurs": len(conteneurs), "lignes": len(lignes),
            "champs": compte, "exemples": exemples, "champs_declares": champs,
            "enregistrements": enregistrements, "liens": liens}


def rendre(m: dict | None, chemin: Path | None) -> str:
    barre = "═" * 74
    L = [barre, "  BAC À SABLE BDA — mesure des sélecteurs sur une page réelle", barre]
    if m is None:
        L += [
            "",
            "  ÉTAT : NON MESURÉ",
            "",
            "  Aucune page réelle n'a été déposée, et aucune n'a pu être collectée :",
            "  la politique réseau de cet environnement répond 403 au CONNECT pour",
            "  publicprocurement.be. Les sélecteurs de sources/bda.yaml restent donc",
            "  `verifie: false` — PLAUSIBLES, PAS MESURÉS.",
            "",
            "  CE QUI MANQUE, et rien d'autre :",
            "    · une page de résultats du BDA, enregistrée depuis une machine ayant",
            "      un accès sortant, puis déposée ici ;",
            "    · relancer :  python3 outils/bac_a_sable_bda.py --html <fichier>",
            "",
            "  Cet outil n'inventera pas de page et ne corrigera aucun sélecteur à",
            "  l'aveugle. « Zéro élément trouvé » et « jamais regardé » ne sont pas",
            "  la même chose.",
            barre,
        ]
        return "\n".join(L)

    L += [f"  fichier   {chemin}", f"  octets    {m['octets']}", "", "  ÉTAT : MESURÉ", ""]
    L += [f"  conteneur  → {m['conteneurs']} élément(s)",
          f"  lignes     → {m['lignes']} élément(s)", ""]
    if not m["lignes"]:
        L += ["  ⚠ AUCUNE LIGNE : le conteneur ou le sélecteur de ligne est faux.",
              "    Corriger sources/bda.yaml SUR PIÈCES, jamais en devinant.", ""]
    L.append("  CHAMPS DE LISTE")
    for nom, spec in m["champs_declares"].items():
        n = m["champs"][nom]
        part = (n / m["lignes"] * 100) if m["lignes"] else 0
        marque = "✔" if n else "✘ SÉLECTEUR FAUX"
        L.append(f"    {marque:16} {nom:14} {n:>4}/{m['lignes']:<4} ({part:3.0f} %)  "
                 f"{_decrire(spec)}")
        if m["exemples"].get(nom):
            L.append(f"                     exemple : « {m['exemples'][nom]} »")
    muets = [n for n, v in m["champs"].items() if not v]
    L += ["", f"  SÉLECTEURS À 0 %   {muets or 'aucun'}",
          f"  ENREGISTREMENTS    {len(m['enregistrements'])}",
          f"  LIENS D'AVIS       {len(m['liens'])}"]
    for lien in m["liens"][:5]:
        L.append(f"      → {lien}")
    L += ["",
          "  Tout champ à 0 % désigne un sélecteur faux. Il se corrige dans",
          "  sources/bda.yaml, jamais dans le code — puis `verifie: true`.", barre]
    return "\n".join(L)


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--html", help="page BDA réelle déposée à la main")
    a = p.parse_args(argv)
    profil = yaml.safe_load(PROFIL.read_text(encoding="utf-8"))
    if not a.html:
        print(rendre(None, None))
        return 2                       # NON MESURÉ n'est pas un succès
    chemin = Path(a.html)
    if not chemin.exists():
        print(f"fichier introuvable : {chemin}", file=sys.stderr)
        return 2
    print(rendre(mesurer(chemin.read_text(encoding="utf-8", errors="replace"), profil),
                 chemin))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
