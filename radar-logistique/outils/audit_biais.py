#!/usr/bin/env python3
"""AUCUNE SOURCE NE PEUT ÊTRE LE MODÈLE IMPLICITE DU PRODUIT.

Dix détecteurs. Chacun MESURE — il exécute le moteur, lit l'AST, compte des
lignes réelles — et rend un verdict qu'on ne peut pas obtenir en relisant le
code avec bonne volonté.

Le piège que cet outil est fait pour éviter : prouver l'indépendance vis-à-vis
d'une source en ajoutant encore des tests sur cette source. Ici, on prouve
l'inverse — que le produit reste entier quand la source disparaît.

    python3 outils/audit_biais.py [--detail]
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                     # noqa: E402

from radar.base import ouvrir                                   # noqa: E402
from radar.chaine import Moteur, traiter                        # noqa: E402
from radar.classification import Type                           # noqa: E402
from radar.mode import Mode                                     # noqa: E402
from radar.modele import Opportunite                            # noqa: E402
from radar.procedure import Vocabulaire                         # noqa: E402

# Les modules qui décident de la VALEUR. Aucun n'a le droit de connaître un
# portail, ni de traiter une source différemment d'une autre.
COEUR = ("score", "capacite", "classification", "nature", "fiabilite",
         "chiffre_affaires", "construction", "activite", "geographie",
         "deduplication", "transitions", "questions", "lots")


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _vocabulaires():
    return {(c := _cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
            for f in sorted((RACINE / "sources").glob("*.yaml"))}


def _moteur():
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=_vocabulaires())


def _code_executable(chemin: Path) -> str:
    """Le code SANS commentaires ni chaînes. Un commentaire peut citer TED en
    exemple ; du code qui teste `source == "ted"` ne le peut pas."""
    src = chemin.read_text(encoding="utf-8")
    morceaux = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            morceaux.append(tok.string)
    return " ".join(morceaux)


# ═══════════════════════════════ LE MÊME BESOIN, HUIT FORMES ═══════════════
#
# Une seule économie, une seule exigence, un seul métier. Ce qui change : la
# source, la forme, les champs que ce type de source publie. Ce qui NE DOIT
# PAS changer : le score, la capacité, la classification métier.
ECONOMIE = dict(montant=540000, duree_mois=36, cadence="quotidienne",
                km_annuels=48000, chauffeurs_requis=3, vehicules_requis=3,
                pays_livraison=["BE"], exigences={"vehicules_min": 4})
BESOIN = ("Transport de marchandises et distribution régionale de colis "
          "vers les points de livraison.")


def huit_formes() -> list:
    """Le MÊME besoin commercial, écrit comme chaque famille l'écrirait."""
    def o(**kw):
        base = dict(intitule="Distribution régionale de colis", texte=BESOIN,
                    acheteur="Client", **ECONOMIE)
        base.update(kw)
        return Opportunite(**base)

    return [
        ("A appel d'offres public", o(
            source="ted", ref_source="A", secteur_acheteur="public",
            type_avis="appel-offres", cpv=["60000000"],
            type_information="avis de marché", statut_source="en cours")),
        ("B page d'entreprise", o(
            source="entreprise", ref_source="B", secteur_acheteur="prive",
            plateforme="https://exemple.be/partenaires")),
        ("C recherche web", o(
            source="recherche", ref_source="C", secteur_acheteur="prive",
            plateforme="https://exemple.be/besoin")),
        ("D bourse de fret", o(
            source="bourse_fret", ref_source="D", secteur_acheteur="prive")),
        # E et F portaient un intitulé différent des six autres. L'écart de
        # métier observé venait donc de MON banc, pas du moteur : le mot
        # « partenaire » ajoutait une famille reconnue. Le besoin doit être
        # écrit STRICTEMENT à l'identique — seule la provenance change.
        ("E sous-traitance", o(
            source="entreprise", ref_source="E", secteur_acheteur="prive",
            contact="sous-traitance@exemple.be")),
        ("F partenariat", o(
            source="entreprise", ref_source="F", secteur_acheteur="prive",
            contact="partenariat@exemple.be")),
        ("G renouvellement", o(
            source="portail", ref_source="G", secteur_acheteur="public",
            type_information="avis de préinformation")),
        ("H signal commercial", o(
            source="signaux", ref_source="H", secteur_acheteur="prive",
            est_signal=True, signal_code="ouverture_site")),
    ]


# ═══════════════════════════════════════════════ LES DIX DÉTECTEURS ════════
def d1_score_selon_source(detail=False):
    """§10 — même économie ⇒ même score. C'est LE test."""
    m = _moteur()
    notes = {}
    for nom, opp in huit_formes():
        notes[nom] = m.analyser(opp).score.total
    ecart = max(notes.values()) - min(notes.values())
    lignes = [f"    {n:<26} {v}" for n, v in notes.items()] if detail or ecart else []
    return (ecart == 0,
            f"écart de score entre les 8 formes du même besoin : {ecart}", lignes)


def d2_capacite_selon_source(detail=False):
    """Même exigence ⇒ même analyse de capacité."""
    m = _moteur()
    vus = {}
    for nom, opp in huit_formes():
        r = m.analyser(opp)
        vus[nom] = (tuple(r.bilan.bloquants), tuple(r.bilan.mobilisations),
                    tuple(r.bilan.atouts))
    distincts = set(vus.values())
    lignes = [f"    {n:<26} bloquants={len(v[0])} mobilis={len(v[1])} atouts={len(v[2])}"
              for n, v in vus.items()] if detail or len(distincts) > 1 else []
    return (len(distincts) == 1,
            f"analyses de capacité distinctes pour la même exigence : {len(distincts)}",
            lignes)


def d3_metier_selon_source(detail=False):
    """Même besoin métier ⇒ même classification métier (familles reconnues)."""
    m = _moteur()
    vus = {n: tuple(sorted(m.analyser(o).correspondance.familles))
           for n, o in huit_formes()}
    distincts = set(vus.values())
    lignes = [f"    {n:<26} {', '.join(v) or '—'}" for n, v in vus.items()] \
        if detail or len(distincts) > 1 else []
    return (len(distincts) == 1,
            f"classifications métier distinctes pour le même besoin : {len(distincts)}",
            lignes)


def d4_cpv_comme_autorite(detail=False):
    """Le CPV ne doit jamais l'emporter sur ce que le TEXTE dit."""
    m = _moteur()
    sans = m.analyser(Opportunite(source="entreprise", ref_source="X",
                                  intitule="Distribution de colis",
                                  texte=BESOIN, **ECONOMIE))
    avec = m.analyser(Opportunite(source="ted", ref_source="Y",
                                  intitule="Distribution de colis",
                                  texte=BESOIN, cpv=["60000000"], **ECONOMIE))
    ok = (sans.score.total == avec.score.total
          and sans.correspondance.familles == avec.correspondance.familles)
    lignes = [f"    sans CPV : score {sans.score.total} · "
              f"{', '.join(sans.correspondance.familles) or '—'}",
              f"    avec CPV : score {avec.score.total} · "
              f"{', '.join(avec.correspondance.familles) or '—'}"] if detail or not ok else []
    return ok, "le CPV ajoute de la valeur à besoin identique", lignes


def d5_reference_officielle_requise(detail=False):
    """Une opportunité sans référence officielle reste une opportunité."""
    m = _moteur()
    avec = m.analyser(Opportunite(source="ted", ref_source="2026/S-123456",
                                  intitule="Distribution de colis", texte=BESOIN,
                                  **ECONOMIE))
    sans = m.analyser(Opportunite(source="entreprise", ref_source="SANS-REF-abc",
                                  intitule="Distribution de colis", texte=BESOIN,
                                  **ECONOMIE))
    ok = avec.score.total == sans.score.total and avec.classement.type is sans.classement.type
    lignes = [f"    avec référence : {avec.score.total} · {avec.classement.type.value}",
              f"    sans référence : {sans.score.total} · {sans.classement.type.value}"] \
        if detail or not ok else []
    return ok, "la référence officielle change la valeur ou la catégorie", lignes


def d6_procedure_obligatoire(detail=False):
    """Classer une opportunité ne doit JAMAIS exiger une procédure."""
    m = _moteur()
    r = m.analyser(Opportunite(
        source="entreprise", ref_source="P", secteur_acheteur="prive",
        intitule="Nous recherchons un transporteur",
        texte="Nous recherchons un transporteur pour nos livraisons régionales.",
        acheteur="Delhaize", pays_livraison=["BE"]))
    etat = r.lecture.etat_affiche
    ok = (etat == "HORS PROCÉDURE" and r.classement.type is not Type.REJET
          and "VÉRIFIER" not in r.classement.action.value)
    lignes = [f"    état={etat} · type={r.classement.type.value} · "
              f"action={r.classement.action.value}"] if detail or not ok else []
    return ok, "un besoin privé est traité comme une procédure incomplète", lignes


def d7_completude_taillee_pour_le_public(detail=False):
    """La grille de complétude doit exister par FAMILLE, pas une seule pour tous."""
    from radar.rapport import CHAMPS_PAR_FAMILLE
    publiques = {"MARCHÉS PUBLICS", "RENOUVELLEMENTS À ANTICIPER"}
    privees = set(CHAMPS_PAR_FAMILLE) - publiques
    champs_publics = {c for f in publiques if f in CHAMPS_PAR_FAMILLE
                      for _, c in CHAMPS_PAR_FAMILLE[f]}
    fautes = []
    for famille in sorted(privees):
        for libelle, colonne in CHAMPS_PAR_FAMILLE[famille]:
            if colonne in ("etat_procedure", "lot_numero", "exigences") \
                    and colonne in champs_publics:
                fautes.append(f"{famille} mesurée sur « {libelle} », propre aux avis")
    return not fautes, f"{len(fautes)} famille(s) privée(s) mesurée(s) à la grille publique", \
        [f"    {f}" for f in fautes]


def d8_fiabilite_recompense_officialite(detail=False):
    """À preuves égales, la fiabilité ne doit pas dépendre de la source."""
    m = _moteur()
    niveaux = {}
    for source, secteur in (("ted", "public"), ("bda", "public"),
                            ("entreprise", "prive"), ("recherche", "prive"),
                            ("bourse_fret", "prive")):
        r = m.analyser(Opportunite(
            source=source, ref_source="R-1", secteur_acheteur=secteur,
            intitule="Distribution de colis", texte=BESOIN, acheteur="Client",
            plateforme="https://exemple.be/x", **ECONOMIE))
        niveaux[source] = r.fiabilite.niveau.value
    ok = len(set(niveaux.values())) == 1
    lignes = [f"    {s:<14} {n}" for s, n in niveaux.items()] if detail or not ok else []
    return ok, "la fiabilité varie selon la source à preuves égales", lignes


def d9_banc_dessai_en_forme_davis(detail=False):
    """Les fixtures et les tests ne doivent pas être majoritairement publics."""
    fautes, total_fix, publics_fix = [], 0, 0
    for fichier in sorted((RACINE / "exemples" / "familles").glob("*.json")):
        charges = json.loads(fichier.read_text(encoding="utf-8"))
        for c in charges:
            if not isinstance(c, dict):
                continue
            total_fix += 1
            if any(k in c for k in ("cpv", "type_avis", "publication-number",
                                    "pouvoir_adjudicateur")):
                publics_fix += 1
    part = publics_fix / total_fix if total_fix else 0
    if part > 0.5:
        fautes.append(f"{part:.0%} des fixtures portent des champs d'avis public")

    # Le constructeur d'opportunité du banc d'essai ne doit pas être public.
    # Sur l'AST, et sur le CORPS de `opp` seulement : sa docstring explique
    # précisément qu'il PORTAIT `type_avis` et `cpv`, et la lire en texte
    # faisait échouer le détecteur sur sa propre explication.
    arbre = ast.parse((RACINE / "tests" / "test_radar.py").read_text(encoding="utf-8"))
    for noeud in arbre.body:
        if isinstance(noeud, ast.FunctionDef) and noeud.name == "opp":
            corps = noeud.body[1:] if ast.get_docstring(noeud) else noeud.body
            code = " ".join(ast.dump(n) for n in corps)
            for interdit in ("type_avis", "cpv"):
                if f"'{interdit}'" in code:
                    fautes.append(f"le constructeur par défaut du banc porte "
                                  f"« {interdit} »")
    return not fautes, (f"banc d'essai en forme d'avis public "
                        f"({publics_fix}/{total_fix} fixtures)"), \
        [f"    {f}" for f in fautes]


def d10_rapport_organise_par_source(detail=False):
    """Le rapport doit s'ouvrir sur l'ARGENT, jamais sur les sources."""
    from radar.rapport import construire
    cx = ouvrir(":memory:")
    m = _moteur()
    traiter(cx, m, [o for _, o in huit_formes()], mode=Mode.DEMO)
    texte = construire(cx, Mode.DEMO, cible={}, proche_km=50).en_texte(avec_fiches=False)
    tete = texte[:2500]
    fautes = []
    # « SIGNAUX COMMERCIAUX » est un compte de NATURE, pas une rubrique de
    # source. On cherche donc un nom de source en début de ligne, suivi d'un
    # compte — la forme « ted : 132 avis » qu'on ne veut jamais voir en tête.
    for nom in ("ted", "bda", "portail", "bourse_fret", "signaux", "recherche",
                "entreprise", "google", "brave"):
        if re.search(rf"^\s*{nom}\s*[:|]\s*\d", tete, re.I | re.M):
            fautes.append(f"« {nom} » apparaît comme rubrique chiffrée en tête")
    # L'argent doit précéder les sources dans le document.
    i_argent = min((texte.find(x) for x in ("CA RÉELLEMENT IDENTIFIÉ",
                                            "À ATTAQUER MAINTENANT")
                    if texte.find(x) >= 0), default=10 ** 9)
    i_source = texte.find("COLLECTE")
    if i_source >= 0 and i_source < i_argent:
        fautes.append("la section COLLECTE précède les opportunités")
    return not fautes, "le rapport est organisé par source", [f"    {f}" for f in fautes]


def d11_nom_de_portail_dans_le_coeur(detail=False):
    """Aucun module de valeur ne cite un portail dans du CODE exécutable."""
    motif = re.compile(r"\b(ted|bda|tenderned|publicprocurement|google|brave)\b", re.I)
    fautes = []
    for nom in COEUR:
        chemin = RACINE / "radar" / f"{nom}.py"
        if not chemin.exists():
            continue
        code = _code_executable(chemin)
        for trouve in set(motif.findall(code)):
            fautes.append(f"{nom}.py nomme « {trouve} » dans du code")
    return not fautes, f"{len(fautes)} module(s) du cœur nomme(nt) un portail", \
        [f"    {f}" for f in fautes]


def d12_secteur_lu_par_le_coeur(detail=False):
    """`secteur_acheteur` ne doit pas être lu par les modules de VALEUR.

    C'est le canal le plus discret par lequel « public » redevient un proxy de
    qualité : il ne nomme aucun portail, donc le détecteur précédent le rate.
    """
    fautes = []
    for nom in COEUR:
        chemin = RACINE / "radar" / f"{nom}.py"
        if not chemin.exists():
            continue
        code = _code_executable(chemin)
        for champ in ("secteur_acheteur", "source_privee", "type_avis",
                      "publication-number", "secteur"):
            if champ in code:
                fautes.append(f"{nom}.py lit « {champ} »")
    return not fautes, f"{len(fautes)} lecture(s) de la provenance dans le cœur", \
        [f"    {f}" for f in fautes]


def d13_radar_entier_sans_public(detail=False):
    """§11 — 100 % privé : un vrai radar commercial, pas un radar mutilé."""
    return _radar_partiel({"prive"}, detail)


def d14_radar_entier_sans_prive(detail=False):
    """§11 — 100 % public : il doit fonctionner aussi, sans privilège."""
    return _radar_partiel({"public"}, detail)


def _radar_partiel(secteurs, detail):
    from radar.rapport import construire
    cx = ouvrir(":memory:")
    m = _moteur()
    lot = [o for _, o in huit_formes()
           if (o.secteur_acheteur or "prive") in secteurs]
    if not lot:
        return False, "aucune donnée dans ce secteur", []
    traiter(cx, m, lot, mode=Mode.DEMO)
    r = construire(cx, Mode.DEMO, cible={}, proche_km=50)
    texte = r.en_texte(avec_fiches=False)
    manques = []
    # Un radar ENTIER : il bulletin, il classe, il agit, il mesure.
    for exigee in ("TOP 5 DES ACTIONS", "CAPACITÉS MANQUANTES",
                   "CE QU'IL FAUT DÉCIDER", "VOLUME ≠ VALEUR"):
        if exigee not in texte:
            manques.append(f"section « {exigee} » absente")
    if not any(r.affaires.values()):
        manques.append("aucune affaire produite")
    lignes = [f"    {len(lot)} entrée(s), "
              f"{sum(len(v) for v in r.affaires.values())} affaire(s), "
              f"{len(texte.splitlines())} lignes de rapport"] if detail or manques else []
    return not manques, f"radar incomplet en {'/'.join(secteurs)} : " \
        + " · ".join(manques), lignes + [f"    {x}" for x in manques]


def d15_aucun_capteur_indispensable(detail=False):
    """§12 — retirer n'importe quelle source, le radar continue."""
    from radar.rapport import construire
    formes = huit_formes()
    sources = sorted({o.source for _, o in formes})
    morts, lignes = [], []
    for exclue in sources:
        cx = ouvrir(":memory:")
        lot = [o for _, o in formes if o.source != exclue]
        traiter(cx, _moteur(), lot, mode=Mode.DEMO)
        r = construire(cx, Mode.DEMO, cible={}, proche_km=50)
        n = sum(len(v) for v in r.affaires.values())
        lignes.append(f"    sans {exclue:<14} {n} affaire(s)")
        if n == 0:
            morts.append(exclue)
    return not morts, f"le radar meurt sans : {', '.join(morts)}", \
        (lignes if detail or morts else [])


def d16_nouveau_capteur_sans_toucher_au_moteur(detail=False):
    """§13 — brancher une source neuve ne doit exiger AUCUN code moteur.

    On fabrique un adaptateur qui n'existe nulle part dans le dépôt, avec des
    noms de champs inventés, et on le fait traverser toute la chaîne.
    """
    from radar.adaptateur import Adaptateur, vers_opportunite
    config = {
        "source": "capteur_inedit", "verifie": False, "secteur_par_defaut": "prive",
        # Le capteur doit porter TOUS les faits de la référence, sous des noms
        # inventés. Une charge appauvrie mesurerait la pauvreté de la charge,
        # pas le traitement de la source — l'erreur que ce détecteur a faite
        # trois fois avant d'être corrigée.
        "champs": {"identifiant": ["ref_interne"], "intitule": ["libelle_du_besoin"],
                   "objet": ["descriptif"], "acheteur": ["donneur_ordre"],
                   "montant": ["budget_annuel"], "duree_mois": ["mois"],
                   "cadence": ["rythme"], "pays_livraison": ["zone_livraison"],
                   "km_annuels": ["kilometrage"], "chauffeurs_requis": ["conducteurs"],
                   "vehicules_requis": ["camions"], "vehicules_min": ["camions_min"]},
    }
    charge = {"ref_interne": "XLS-42",
              "libelle_du_besoin": "Distribution régionale de colis",
              "descriptif": BESOIN, "donneur_ordre": "Client",
              "budget_annuel": 540000, "mois": 36, "rythme": "quotidienne",
              "zone_livraison": "BE", "kilometrage": 48000, "conducteurs": 3,
              "camions": 3, "camions_min": 4}
    opp = vers_opportunite(Adaptateur.depuis_config(config), charge, "capteur_inedit",
                           {"secteur": "prive"})
    r = _moteur().analyser(opp)
    reference = _moteur().analyser(dict(huit_formes())["B page d'entreprise"])
    ok = (r.score.total == reference.score.total
          and r.classement.type is reference.classement.type)
    lignes = [f"    capteur inédit : score {r.score.total} · {r.classement.type.value}",
              f"    référence      : score {reference.score.total} · "
              f"{reference.classement.type.value}"] if detail or not ok else []
    return ok, "une source inédite n'obtient pas le même traitement", lignes


DETECTEURS = [
    ("score identique à économie identique", d1_score_selon_source),
    ("capacité identique à exigence identique", d2_capacite_selon_source),
    ("métier identique à besoin identique", d3_metier_selon_source),
    ("le CPV n'est pas une autorité", d4_cpv_comme_autorite),
    ("la référence officielle n'est pas une condition", d5_reference_officielle_requise),
    ("aucune procédure obligatoire pour classer", d6_procedure_obligatoire),
    ("complétude par famille, pas par avis", d7_completude_taillee_pour_le_public),
    ("la fiabilité ne récompense pas l'officialité", d8_fiabilite_recompense_officialite),
    ("le banc d'essai n'est pas en forme d'avis", d9_banc_dessai_en_forme_davis),
    ("le rapport n'est pas organisé par source", d10_rapport_organise_par_source),
    ("aucun portail nommé dans le cœur", d11_nom_de_portail_dans_le_coeur),
    ("la provenance n'entre pas dans la valeur", d12_secteur_lu_par_le_coeur),
    ("radar entier avec 0 marché public", d13_radar_entier_sans_public),
    ("radar entier avec 0 donnée privée", d14_radar_entier_sans_prive),
    ("aucun capteur indispensable", d15_aucun_capteur_indispensable),
    ("un capteur inédit se branche sans toucher au moteur",
     d16_nouveau_capteur_sans_toucher_au_moteur),
]


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--detail", action="store_true")
    a = p.parse_args(argv)

    print("╔" + "═" * 70 + "╗")
    print("║  " + "AUCUNE SOURCE NE PEUT ÊTRE LE MODÈLE IMPLICITE DU PRODUIT".ljust(68) + "║")
    print("╚" + "═" * 70 + "╝")
    print()
    print("  Seize détecteurs. Chacun EXÉCUTE le moteur ou lit son AST.")
    print("  Le même besoin commercial est présenté sous huit formes ; ce qui")
    print("  change est la provenance, ce qui ne doit pas changer est la valeur.")
    print()

    echecs = []
    for libelle, fn in DETECTEURS:
        ok, message, lignes = fn(a.detail)
        marque = "✅" if ok else "❌"
        print(f"  {marque} {libelle:<46} {'' if ok else message}")
        for l in lignes:
            print(l)
        if not ok:
            echecs.append((libelle, message, lignes))

    print()
    print("─" * 72)
    if echecs:
        print(f"{len(echecs)} BIAIS DÉTECTÉ(S) — chacun fait qu'une source vaut plus")
        print("qu'une autre à besoin commercial identique.")
        for libelle, message, _ in echecs:
            print(f"  ❌ {libelle} : {message}")
        return 1
    print(f"{len(DETECTEURS)}/{len(DETECTEURS)} — aucune source n'est le modèle implicite.")
    print()
    print("Ce que cela NE prouve pas : que le radar trouve de vraies affaires.")
    print("Voir `python3 -m radar.cli validation` pour la mesure réelle.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
