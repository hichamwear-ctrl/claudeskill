#!/usr/bin/env python3
"""LE CYCLE COMPLET, sur les données réelles déjà figées.

    base persistante → traitement → rapport → alerte fichier

Ce n'est pas une démonstration : c'est le radar qui tourne, sur les quinze
avis réellement collectés le 12 septembre et conservés, hachés, dans
`validation/collectes_reelles/`. Rien n'est fabriqué ; aucune page
individuelle n'a été lue, et le résultat le dit.

Deux passages successifs sur la MÊME entrée doivent donner :
  · le même nombre d'avis en base (déduplication) ;
  · aucune alerte de plus (la file est idempotente sur source+ref+motif) ;
  · aucun fichier d'alerte de plus (le sceau du contenu l'empêche).

    python3 outils/cycle_reel.py --base /tmp/radar.sqlite3 --alertes /tmp/alertes
    python3 outils/cycle_reel.py --base /tmp/radar.sqlite3 --alertes /tmp/alertes  # 2e passage

Bibliothèque standard uniquement.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml  # noqa: E402

from radar import envoi  # noqa: E402
from radar.adaptateur import Adaptateur, vers_opportunite  # noqa: E402
from radar.alerte import TransportFichier  # noqa: E402
from radar.base import ouvrir  # noqa: E402
from radar.chaine import traiter  # noqa: E402
from radar.mode import Mode, estampiller  # noqa: E402

COLLECTE = RACINE / "validation" / "collectes_reelles" / "2026-09-12-portail-brut.json"


def _moteur():
    """Le moteur du dépôt, monté depuis les mêmes fichiers de configuration
    que la ligne de commande. Aucun réglage propre à cet outil."""
    from radar.chaine import Moteur
    from radar.procedure import Vocabulaire

    def cfg(nom):
        return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))

    vocs = {(c := cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
            for f in sorted((RACINE / "sources").glob("*.yaml"))}
    return Moteur(cfg("profil.yaml"), cfg("config/capacites.yaml"),
                  cfg("config/geographie.yaml"), cfg("config/ponderations.yaml"),
                  cfg("config/roles.yaml"), vocabulaires=vocs)


def charger() -> list:
    """Les avis réels, tels qu'ils ont été collectés et conservés.

    SEULS `title` et `url` entrent : le résumé en prose produit par l'outil de
    recherche est écrit par un modèle, ce n'est pas une observation.
    """
    profil = yaml.safe_load((RACINE / "sources" / "portail.yaml").read_text(encoding="utf-8"))
    ad = Adaptateur.depuis_config(profil)
    brut = json.loads(COLLECTE.read_text(encoding="utf-8"))
    sortie = []
    for requete in brut["requetes"]:
        for r in requete["resultats"]:
            charge = estampiller({"id": r["url"], "intitule": r["title"], "url": r["url"]},
                                 source="portail", reference=r["url"])
            sortie.append(vers_opportunite(ad, charge, "portail", {}))
    return sortie


def etat_base(cx) -> dict:
    """Ce que la base contient, avant ou après un passage."""
    un = lambda sql: cx.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "avis": un("SELECT count(*) FROM avis"),
        "opportunites": un("SELECT count(*) FROM opportunites"),
        "alertes": un("SELECT count(*) FROM envois"),
        "alertes_delivrees": un("SELECT count(*) FROM envois WHERE etat='delivre'"),
        "transitions": un("SELECT count(*) FROM etats_historique"),
    }


def repartition(cx, colonne: str) -> dict:
    return dict(cx.execute(
        f"SELECT COALESCE({colonne},'—') k, count(*) n FROM opportunites"
        f" GROUP BY k ORDER BY n DESC").fetchall())


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True, help="fichier SQLite persistant")
    p.add_argument("--alertes", required=True, help="dossier où déposer les fiches")
    a = p.parse_args(argv)

    opportunites = charger()
    cx = ouvrir(a.base)
    avant = etat_base(cx)
    premier = avant["avis"] == 0

    bilan = traiter(cx, _moteur(), opportunites, mode=Mode.REEL)
    apres = etat_base(cx)

    envoi.reprendre_interrompus(cx)
    transport = TransportFichier(a.alertes)
    livraison = envoi.vider(cx, transport)
    final = etat_base(cx)

    ligne = "─" * 74
    print(ligne)
    print(f"  CYCLE RÉEL — {'PREMIER PASSAGE' if premier else 'PASSAGE SUIVANT'}")
    print(f"  entrée : {COLLECTE.relative_to(RACINE)}")
    print(f"  base   : {Path(a.base).resolve()}")
    print(ligne)
    print(f"  avis lus                    {bilan.lus}")
    print(f"  nouveaux en base            {apres['avis'] - avant['avis']}")
    print(f"  déjà connus (inchangés)     {bilan.lus - (apres['avis'] - avant['avis'])}")
    print(f"  modifiés (changement d'état){'':1}{apres['transitions'] - avant['transitions']:>3}")
    print(f"  doublons dans le lot        {bilan.doublons}")
    print()
    print(f"  opportunités produites      {bilan.lus - bilan.rejet}")
    print(f"    🟢 DIRECT                 {bilan.direct}")
    print(f"    🟡 RENFORCEMENT           {bilan.renforcement}")
    print(f"    🟣 À CONSTRUIRE           {bilan.a_construire}")
    print(f"    🔵 PROSPECT               {bilan.prospect}")
    print(f"    🔴 REJET                  {bilan.rejet}")
    print(f"  moteur CAPTER / DÉVELOPPER  {bilan.capter} / {bilan.developper}")
    print()
    for titre, colonne in (("ACTION", "action"), ("ÉTAT DE PROCÉDURE", "etat_procedure"),
                           ("TYPE D'INFORMATION", "type_information"), ("NATURE", "nature")):
        print(f"  {titre}")
        for k, n in repartition(cx, colonne).items():
            print(f"      {str(k)[:52]:54} {n:>3}")
    print()
    mesurables = cx.execute(
        "SELECT count(*) FROM opportunites WHERE score_mesurable=1").fetchone()[0]
    ca = cx.execute("SELECT COALESCE(sum(montant),0) FROM opportunites").fetchone()[0]
    print(f"  CA réellement identifié     {ca:.0f} €")
    print(f"  scores MESURABLES           {mesurables}")
    print(f"  scores NON MESURABLES       {final['opportunites'] - mesurables}")
    print()
    print(f"  alertes créées (file)       {apres['alertes'] - avant['alertes']}")
    print(f"  alertes réellement écrites  {len(transport.ecrits)}")
    print(f"  déjà sorties (sceau connu)  {len(transport.deja_sortis)}")
    print(f"  livraison                   {livraison}")
    print()
    couvertes = dict(cx.execute(
        "SELECT source, count(*) FROM avis GROUP BY source").fetchall())
    familles = [f.stem for f in sorted((RACINE / "sources").glob("*.yaml"))]
    print(f"  familles ayant vu une donnée  {sorted(couvertes) or '—'}")
    print(f"  familles encore muettes       "
          f"{[f for f in familles if f not in couvertes]}")
    print(ligne)
    cx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
