"""Ligne de commande.

Un outil qui échoue le dit et s'arrête avec un code non nul, plutôt que
d'afficher « 0 » partout en signalant un succès.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import envoi, sondage as sondage_mod
from .adaptateur import Adaptateur, vers_opportunite
from .base import ouvrir
from .chaine import Moteur, traiter

RACINE = Path(__file__).resolve().parent.parent


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _moteur() -> Moteur:
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"))


def _source(nom):
    chemin = RACINE / "sources" / f"{nom}.yaml"
    if not chemin.exists():
        print(f"source inconnue : {nom} (aucun fichier {chemin.name})", file=sys.stderr)
        raise SystemExit(2)
    cfg = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    return Adaptateur.depuis_config(cfg), cfg


def _charger(adaptateur, cfg, chemin, source):
    charges = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if not isinstance(charges, list) or not charges:
        print("entrée vide ou mal formée — rien à traiter", file=sys.stderr)
        raise SystemExit(2)
    defauts = {"nature": cfg.get("nature"), "secteur": cfg.get("secteur_par_defaut")}
    return [vers_opportunite(adaptateur, c, source, defauts) for c in charges], charges


def cmd_recenser(a) -> int:
    adaptateur, _ = _source(a.source)
    charges = json.loads(Path(a.echantillon).read_text(encoding="utf-8"))
    if not isinstance(charges, list) or not charges:
        print("échantillon vide — rien à mesurer", file=sys.stderr)
        return 2
    taux = adaptateur.mesurer(charges)
    print(f"Recensement des clés « {a.source} » sur {len(charges)} réponses réelles\n")
    for nom, t in sorted(taux.items(), key=lambda x: -x[1]):
        marque = "  " if t > 0.5 else ("~ " if t > 0 else "✗ ")
        print(f"  {marque}{t:6.1%}  {nom}")
    absents = [n for n, t in taux.items() if t == 0]
    if absents:
        print(f"\n{len(absents)} champ(s) à 0 % : la clé déclarée n'existe pas.")
        print(f"Corrige-les dans sources/{a.source}.yaml, PAS dans le code.")
        return 1
    print("\nTous les champs répondent. Passe `verifie: true` dans le fichier de source.")
    return 0


def cmd_sonder(a) -> int:
    """Mesure le marché AVANT de construire quoi que ce soit de plus."""
    adaptateur, cfg = _source(a.source)
    opportunites, _ = _charger(adaptateur, cfg, a.entree, a.source)
    s = sondage_mod.sonder(_moteur(), opportunites, a.source)
    print(s.rapport())
    if not cfg.get("verifie"):
        print("\n/!\\ adaptateur non vérifié : lance d'abord `recenser`.")
        print("    Les chiffres ci-dessus portent sur ce que l'adaptateur a SU lire.")
    return 0


def cmd_traiter(a) -> int:
    adaptateur, cfg = _source(a.source)
    if not cfg.get("verifie"):
        print(f"AVERTISSEMENT : adaptateur « {a.source} » non vérifié — lance `recenser`.\n",
              file=sys.stderr)
    opportunites, _ = _charger(adaptateur, cfg, a.entree, a.source)
    cx = ouvrir(a.base)
    repris = envoi.reprendre_interrompus(cx)
    if repris:
        print(f"{repris} envoi(s) interrompu(s) marqué(s) ambigus — non réémis.")
    b = traiter(cx, _moteur(), opportunites)
    print(f"lus {b.lus} · doublons {b.doublons} · "
          f"🟢 {b.postulables} · 🟠 {b.a_verifier} · 🔴 {b.non_postulables} · "
          f"notifiés {b.notifies}")
    if b.attributions_memorisees:
        print(f"{b.attributions_memorisees} attribution(s) mémorisée(s) pour le calendrier "
              "(non notifiées)")
    if b.motifs_rejet:
        print("rejets : " + " · ".join(f"{k} ×{v}" for k, v in
                                       sorted(b.motifs_rejet.items(), key=lambda x: -x[1])[:5]))
    return 0


def cmd_opportunites(a) -> int:
    cx = ouvrir(a.base, lecture_seule=True)          # incapable d'écrire
    where = "statut IN ('POSTULABLE','A_VERIFIER')"
    if a.postulables_seulement:
        where = "statut='POSTULABLE'"
    if a.signaux:
        where += " AND nature='SIGNAL_COMMERCIAL'"
    elif not a.tout:
        where += " AND nature='OPPORTUNITE_DIRECTE'"
    lignes = cx.execute(
        f"SELECT o.*, a.ref_source FROM opportunites o JOIN avis a ON a.id=o.avis_id "
        f"WHERE {where} ORDER BY o.score DESC, o.echeance ASC").fetchall()
    if not lignes:
        print("Aucune opportunité. (Base lue correctement — ce n'est pas une panne.)")
        return 0
    for l in lignes:
        if a.complet:
            print(l["fiche"]); print("\n" + "─" * 66 + "\n")
        else:
            emoji = {"POSTULABLE": "🟢", "A_VERIFIER": "🟠"}.get(l["statut"], "·")
            print(f"{emoji} [{l['score']:3}] {(l['echeance'] or 'A_VERIFIER')[:10]:<11} "
                  f"{(l['intitule'] or '')[:52]}")
    print(f"\n{len(lignes)} opportunité(s).")
    return 0


def cmd_calendrier(a) -> int:
    """Ce qui va revenir sur le marché — calculé depuis les attributions."""
    cx = ouvrir(a.base, lecture_seule=True)
    lignes = cx.execute(
        "SELECT * FROM attributions ORDER BY renouvellement IS NULL, renouvellement").fetchall()
    if not lignes:
        print("Aucune attribution mémorisée pour l'instant.")
        return 0
    print("CALENDRIER DES REMISES EN CONCURRENCE\n")
    for l in lignes:
        quand = (l["renouvellement"] or "")[:7] or "A_VERIFIER"
        print(f"  {quand:<12} {(l['prestation'] or '')[:44]}")
        print(f"  {'':<12} titulaire : {l['titulaire'] or 'A_VERIFIER'} · {l['commentaire']}")
    return 0


def cmd_notifier(a) -> int:
    cx = ouvrir(a.base)
    envoi.reprendre_interrompus(cx)
    if a.pour_de_vrai:
        print("aucun transport configuré dans cet environnement", file=sys.stderr)
        return 3
    en_attente = envoi.a_envoyer(cx)
    print(f"{len(en_attente)} message(s) en attente (essai à blanc, rien n'est envoyé)")
    for l in en_attente:
        print(f"  · {l['source']}/{l['ref_source']}")
    return 0


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="Radar commercial logistique")
    p.add_argument("--base", default="radar.sqlite3")
    s = p.add_subparsers(dest="cmd", required=True)

    r = s.add_parser("recenser", help="mesurer les clés réelles d'une source")
    r.add_argument("--source", required=True); r.add_argument("--echantillon", required=True)
    r.set_defaults(fn=cmd_recenser)

    so = s.add_parser("sonder", help="mesurer le marché avant de construire")
    so.add_argument("--source", required=True); so.add_argument("--entree", required=True)
    so.set_defaults(fn=cmd_sonder)

    t = s.add_parser("traiter", help="traiter un lot")
    t.add_argument("--source", required=True); t.add_argument("--entree", required=True)
    t.set_defaults(fn=cmd_traiter)

    o = s.add_parser("opportunites", help="ce sur quoi on peut candidater")
    o.add_argument("--complet", action="store_true")
    o.add_argument("--postulables-seulement", action="store_true")
    o.add_argument("--signaux", action="store_true", help="uniquement les signaux commerciaux")
    o.add_argument("--tout", action="store_true", help="opportunités et signaux ensemble")
    o.set_defaults(fn=cmd_opportunites)

    c = s.add_parser("calendrier", help="remises en concurrence calculées")
    c.set_defaults(fn=cmd_calendrier)

    n = s.add_parser("notifier", help="vider la file d'envoi")
    n.add_argument("--pour-de-vrai", action="store_true")
    n.set_defaults(fn=cmd_notifier)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(principal())
