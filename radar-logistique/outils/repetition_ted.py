#!/usr/bin/env python3
"""RÉPÉTITION GÉNÉRALE — le trajet complet, avant que les vraies données arrivent.

Ce script ne mesure PAS le marché. Il ne dit rien de ce qui se vend en
Belgique. Il vérifie une seule chose, et il faut le dire clairement :

    quand un fichier TED réel arrivera, aucune ligne ne se perdra en route.

Il fabrique donc un lot HOSTILE — volontairement mal formé, incomplet,
dupliqué, hors schéma — puis le fait passer par la chaîne entière :

    COLLECTE → PREUVE → NORMALISATION → LOTS → DÉDUPLICATION
    → ANALYSE → CAPACITÉ → ÉCONOMIE → SCORE → CAPTER/DÉVELOPPER → RAPPORT

et exige que le livre de comptes se réconcilie à l'unité près.

Les enregistrements de ce lot sont des FIXTURES. Elles n'ont aucune preuve de
collecte, donc :
  · en DEMO   elles passent, et le trajet est éprouvé ;
  · en RÉEL   elles sont toutes REFUSÉES et conservées comme incidents.
C'est exactement ce qu'on veut vérifier avant de brancher la vraie source.

    python3 outils/repetition_ted.py

Sortie 0 = le trajet tient. Sortie 1 = une ligne s'est perdue : ne pas brancher
les vraies données tant que ce n'est pas corrigé.
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                    # noqa: E402

from radar.adaptateur import Adaptateur, vers_opportunite      # noqa: E402
from radar.base import ouvrir                                  # noqa: E402
from radar.chaine import Moteur, traiter                       # noqa: E402
from radar.comptes import ReconciliationImpossible             # noqa: E402
from radar.mode import Mode, estampiller                       # noqa: E402
from radar import rapport as rapport_mod                       # noqa: E402


# ─────────────────────────────────────────────────────────── le lot hostile --
# Chaque entrée porte le nom du piège qu'elle tend. Les clés sont celles
# déclarées dans sources/ted.yaml : si l'adaptateur change, la répétition
# suit — elle ne réécrit pas le schéma dans son coin.
def lot_hostile() -> list[dict]:
    return [
        # 1. l'avis normal, celui qu'on espère recevoir
        {"publication-number": "TED-0001",
         "title": {"fra": "Transport et distribution de colis — région bruxelloise"},
         "description": {"fra": "Tournées quotidiennes au départ d'un dépôt belge."},
         "buyer": {"name": {"fra": "Commune de Schaerbeek"}},
         "classification-cpv": ["60000000", "64120000"],
         "estimated-value": {"amount": 240000, "currency": "EUR"},
         "duration-months": 24, "frequency": "quotidienne",
         "deadline-receipt-tender": "2099-01-31",
         "place-of-delivery": {"country": "BE"}},

        # 2. AUCUN identifiant : c'est le bug des sept opportunités disparues.
        {"title": {"fra": "Livraison de repas scolaires — lots communaux"},
         "description": {"fra": "Livraison quotidienne en liaison froide."},
         "buyer": {"name": {"fra": "CPAS de Liège"}},
         "classification-cpv": ["60000000"],
         "estimated-value": {"amount": 88000, "currency": "EUR"},
         "deadline-receipt-tender": "2099-02-15",
         "place-of-delivery": {"country": "BE"}},

        # 3. le second sans identifiant : il ne doit PAS écraser le précédent.
        {"title": {"fra": "Transport de fleurs coupées depuis Aalsmeer"},
         "description": {"fra": "Collecte aux Pays-Bas, livraison en Belgique."},
         "buyer": {"name": {"fra": "Coopérative florale"}},
         "classification-cpv": ["60000000"],
         "place-of-collection": {"country": "NL"},
         "place-of-delivery": {"country": "BE"},
         "deadline-receipt-tender": "2099-03-01"},

        # 4. hors schéma total : aucune clé connue.
        {"chose": "objet non identifié", "valeur": 12},

        # 5. hors schéma lui aussi, mais DIFFÉRENT : ne doit pas fusionner
        #    avec le précédent sous prétexte que tous deux sont vides.
        {"autre": "second objet non identifié", "valeur": 13},

        # 6. le même marché que 1, republié : doublon CERTAIN attendu.
        {"publication-number": "TED-0001-BIS",
         "title": {"fra": "Transport et distribution de colis — région bruxelloise"},
         "description": {"fra": "Tournées quotidiennes au départ d'un dépôt belge."},
         "buyer": {"name": {"fra": "Commune de Schaerbeek"}},
         "classification-cpv": ["60000000", "64120000"],
         "estimated-value": {"amount": 240000, "currency": "EUR"},
         "duration-months": 24, "frequency": "quotidienne",
         "deadline-receipt-tender": "2099-01-31",
         "place-of-delivery": {"country": "BE"}},

        # 7. marché à lots : chaque lot doit devenir une opportunité, en
        #    gardant le lien vers son marché parent.
        {"publication-number": "TED-0002",
         "title": {"fra": "Marché de services logistiques — 3 lots"},
         "description": {"fra": "Marché divisé en lots."},
         "buyer": {"name": {"fra": "Province du Brabant wallon"}},
         "classification-cpv": ["60000000"],
         "deadline-receipt-tender": "2099-04-01",
         "place-of-delivery": {"country": "BE"},
         "lots": [
             {"numero": "1", "intitule": "Transport de mobilier",
              "montant": 60000, "cpv": ["60000000"]},
             {"numero": "2", "intitule": "Fourniture et livraison de poissons frais",
              "montant": 400000, "cpv": ["15200000"]},
             {"numero": "3", "intitule": "Distribution régionale — 12 véhicules exigés",
              "montant": 900000, "cpv": ["60000000"],
              "requirements": {"min-vehicles": 12}},
         ]},

        # 8. type informatif : ni ouvert ni attribué.
        {"publication-number": "TED-0003", "notice-type": "pin",
         "title": {"fra": "Avis de préinformation — transport de personnes"},
         "classification-cpv": ["60130000"],
         "place-of-delivery": {"country": "BE"}},

        # 9. attribué : va vers DÉVELOPPER, pas vers CAPTER.
        {"publication-number": "TED-0004", "contract-awarded": True,
         "title": {"fra": "Distribution régionale de colis — marché attribué"},
         "buyer": {"name": {"fra": "Intercommunale"}},
         "winner": {"name": "Grand Opérateur Logistique"},
         "estimated-value": {"amount": 2400000, "currency": "EUR"},
         "duration-months": 48, "award-date": "2026-01-15",
         "classification-cpv": ["60000000"],
         "place-of-delivery": {"country": "BE"}},

        # 10. fourniture pure : rejet attendu, AVEC son motif.
        {"publication-number": "TED-0005",
         "title": {"fra": "Fourniture de fournitures de bureau"},
         "description": {"fra": "Achat de papier et de cartouches."},
         "classification-cpv": ["30190000"],
         "place-of-delivery": {"country": "BE"}},

        # 11. obligation légale que l'entreprise n'a pas : ADR.
        {"publication-number": "TED-0006",
         "title": {"fra": "Transport de matières dangereuses — ADR exigé"},
         "description": {"fra": "Transport ADR classe 3."},
         "classification-cpv": ["60000000"],
         "place-of-delivery": {"country": "BE"},
         "deadline-receipt-tender": "2099-05-01"},

        # 12. aucun lieu publié : conservé, jamais écarté pour ça.
        {"publication-number": "TED-0007",
         "title": {"fra": "Prestations de transport — lieu non précisé"},
         "classification-cpv": ["60000000"],
         "deadline-receipt-tender": "2099-06-01"},

        # 13. échéance dépassée : sortie du flux, avec son motif.
        {"publication-number": "TED-0008",
         "title": {"fra": "Transport scolaire — appel clos"},
         "classification-cpv": ["60130000"],
         "deadline-receipt-tender": "2001-01-01",
         "place-of-delivery": {"country": "BE"}},

        # 14. valeurs nulles partout où le schéma en attend.
        {"publication-number": "TED-0009", "title": None, "description": None,
         "estimated-value": None, "deadline-receipt-tender": None,
         "classification-cpv": None, "place-of-delivery": None},

        # 15. types inattendus : un montant en texte, une durée en texte.
        {"publication-number": "TED-0010",
         "title": {"fra": "Transport de palettes"},
         "estimated-value": {"amount": "120 000", "currency": "EUR"},
         "duration-months": "douze",
         "classification-cpv": "60000000",
         "deadline-receipt-tender": "31/12/2099",
         "place-of-delivery": {"country": "BE"}},

        # 16. hors zone : rien ne touche la Belgique.
        {"publication-number": "TED-0011",
         "title": {"fra": "Transport Lyon → Marseille"},
         "classification-cpv": ["60000000"],
         "place-of-delivery": {"country": "FR"},
         "deadline-receipt-tender": "2099-07-01"},

        # 17. métier inconnu du vocabulaire : doit passer par 🟣, pas par 🔴.
        {"publication-number": "TED-0012",
         "title": {"fra": "Entretien des espaces verts — formation assurée par le pouvoir adjudicateur"},
         "description": {"fra": "Une formation de deux semaines est assurée. "
                                "Marché de trois ans, démarrage en 2099."},
         "start-date": "2099-09-01", "duration-months": 36,
         "deadline-receipt-tender": "2099-08-01",
         "place-of-delivery": {"country": "BE"}},
    ]


def _moteur() -> Moteur:
    lire = lambda n: yaml.safe_load((RACINE / n).read_text(encoding="utf-8"))
    return Moteur(lire("profil.yaml"), lire("config/capacites.yaml"),
                  lire("config/geographie.yaml"), lire("config/ponderations.yaml"),
                  lire("config/roles.yaml"))


def _opportunites(charges):
    cfg = yaml.safe_load((RACINE / "sources" / "ted.yaml").read_text(encoding="utf-8"))
    ad = Adaptateur.depuis_config(cfg)
    defauts = {"signal": cfg.get("signal"), "secteur": cfg.get("secteur_par_defaut")}
    return [vers_opportunite(ad, c, "ted", defauts) for c in charges]


def _passer(charges, mode: Mode):
    cx = ouvrir(":memory:")
    b = traiter(cx, _moteur(), _opportunites(charges), mode=mode)
    return cx, b


def principal(argv=None) -> int:
    print("╔" + "═" * 68 + "╗")
    print("║  RÉPÉTITION GÉNÉRALE — CE N'EST PAS UNE MESURE DU MARCHÉ            ║")
    print("║  Aucun chiffre ci-dessous ne décrit une opportunité réelle.        ║")
    print("╚" + "═" * 68 + "╝\n")

    charges = lot_hostile()
    echecs = []

    # ── 1. le trajet complet, en DEMO ────────────────────────────────────
    print(f"1. TRAJET COMPLET sur {len(charges)} enregistrements hostiles (DEMO)")
    try:
        cx, b = _passer(charges, Mode.DEMO)
    except ReconciliationImpossible as e:
        print(f"   ✗ LE LIVRE NE TOMBE PAS JUSTE : {e}")
        return 1
    print(f"   lus {b.lus} · lots éclatés {b.lots_eclates} · doublons {b.doublons}")
    print(f"   🟢 {b.direct} · 🟡 {b.renforcement} · 🟣 {b.a_construire} · "
          f"🔵 {b.prospect} · 🔴 {b.rejet}")
    print(f"   CAPTER {b.capter} · DÉVELOPPER {b.developper}")
    print(f"   réconciliation : écart {b.livre.ecart()}")
    if b.livre.ecart() != 0:
        echecs.append("le livre de comptes ne se réconcilie pas")
    if b.lus != len(charges):
        echecs.append(f"{len(charges)} entrées fournies, {b.lus} lues")

    # ── 2. rien n'est sorti sans motif ───────────────────────────────────
    print("\n2. AUCUNE SORTIE SILENCIEUSE")
    sans_motif = cx.execute("SELECT count(*) c FROM opportunites"
                            " WHERE type = 'REJET' AND (motif IS NULL OR motif = '')"
                            ).fetchone()["c"]
    print(f"   rejets sans motif : {sans_motif}")
    if sans_motif:
        echecs.append(f"{sans_motif} rejet(s) sans motif")
    sans_journal = cx.execute("SELECT count(*) c FROM opportunites"
                              " WHERE journal IS NULL OR journal = ''").fetchone()["c"]
    print(f"   opportunités sans journal : {sans_journal}")
    if sans_journal:
        echecs.append(f"{sans_journal} opportunité(s) sans journal")

    # ── 3. les lots gardent leur marché parent ───────────────────────────
    print("\n3. LOTS")
    lots = cx.execute("SELECT lot_numero, marche_ref, intitule FROM opportunites"
                      " WHERE lot_numero IS NOT NULL AND lot_numero <> ''").fetchall()
    for l in lots:
        print(f"   lot {l['lot_numero']:<3} parent {(l['marche_ref'] or 'ABSENT'):<12} "
              f"{(l['intitule'] or '')[:44]}")
    orphelins = [l for l in lots if not l["marche_ref"]]
    if orphelins:
        echecs.append(f"{len(orphelins)} lot(s) sans marché parent")

    # ── 4. les avis sans identifiant restent distincts ───────────────────
    print("\n4. AVIS SANS IDENTIFIANT")
    refs = [l["ref_source"] for l in cx.execute("SELECT ref_source FROM avis")]
    print(f"   {len(refs)} références, {len(set(refs))} distinctes")
    if len(refs) != len(set(refs)):
        echecs.append("deux avis partagent la même référence")
    if any(not r for r in refs):
        echecs.append("une référence est vide")

    # ── 5. le rapport se construit sur ce lot ────────────────────────────
    print("\n5. RAPPORT")
    r = rapport_mod.construire(cx, Mode.DEMO, limite_top=5)
    texte = r.en_texte(avec_fiches=False)
    print(f"   {len(texte.splitlines())} lignes produites, "
          f"{len(r.selections)} sélections, {len(r.top)} en tête")
    if "DEMO" not in texte.splitlines()[1]:
        echecs.append("le rapport ne porte pas son mode en tête")

    # ── 6. le même lot est REFUSÉ en RÉEL ────────────────────────────────
    print("\n6. LE MÊME LOT EN MODE RÉEL")
    try:
        cxr, br = _passer(charges, Mode.REEL)
    except ReconciliationImpossible as e:
        print(f"   ✗ LE LIVRE NE TOMBE PAS JUSTE : {e}")
        return 1
    incidents = cxr.execute("SELECT count(*) c FROM incidents").fetchone()["c"]
    print(f"   entrées {br.lus} · refusées {br.livre.total_illisibles} · "
          f"incidents conservés {incidents} · sorties {br.livre.sorties}")
    if br.livre.sorties != 0:
        echecs.append("une fixture est entrée dans le flux RÉEL")
    if incidents != len(charges):
        echecs.append(f"{len(charges)} refus attendus, {incidents} incidents conservés")

    # ── 7. une ligne réellement collectée passe, elle ────────────────────
    print("\n7. UNE LIGNE ESTAMPILLÉE PASSE EN RÉEL")
    vrai = estampiller(dict(charges[0]), source="ted", reference="TED-0001")
    try:
        _, bv = _passer([vrai], Mode.REEL)
        print(f"   sorties {bv.livre.sorties} · refusées {bv.livre.total_illisibles}")
        if bv.livre.total_illisibles:
            echecs.append("une ligne estampillée a été refusée en RÉEL")
    except ReconciliationImpossible as e:
        echecs.append(f"réconciliation impossible sur ligne estampillée : {e}")

    # ── verdict ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if echecs:
        print(f"RÉPÉTITION ÉCHOUÉE — {len(echecs)} problème(s) :")
        for e in echecs:
            print(f"  · {e}")
        print("\nNe branche PAS les vraies données tant que ce n'est pas corrigé.")
        return 1
    print("RÉPÉTITION RÉUSSIE — le trajet tient sur un lot volontairement hostile.")
    print("Cela ne dit RIEN du marché : c'est le chemin qui est éprouvé, pas l'offre.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
