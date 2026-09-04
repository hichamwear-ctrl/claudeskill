#!/usr/bin/env python3
"""PREMIÈRE MESURE RÉELLE — une vraie page, de bout en bout, sans rien inventer.

    python3 outils/premiere_page_reelle.py --page page.html \
        --url https://... --origine "enregistrée dans le navigateur le 4/9" \
        --famille entreprise --completude "page complète"

    python3 outils/premiere_page_reelle.py --protocole    # ce qui sera mesuré
    python3 outils/premiere_page_reelle.py --etat         # état de validation

CE QUE CET OUTIL FAIT, ET DANS CET ORDRE :

  E. il conserve la page BRUTE, telle quelle, avec son empreinte SHA-256.
     C'est la preuve. Tout ce qui suit doit pouvoir être recontrôlé dessus.
  F. il montre ce qui a été RÉELLEMENT extrait, avec la piste qui l'a trouvé.
  G. il signale chaque information qu'il n'a PAS pu extraire, et la question
     à poser pour l'obtenir.
  C. il range chaque information dans un des quatre niveaux, et le niveau
     OBSERVÉ n'est accordé que si la valeur figure littéralement dans la page.
  D. il fait passer la donnée dans TOUTE la chaîne — rôle, ontologie, état,
     nature, fiabilité, capacités, score, classification, action.
  I. il produit une fiche commerciale complète, avec la prochaine question.
  J. il produit un rapport global, et inscrit la mesure au registre réel.

CE QU'IL NE FAIT PAS :
  · il ne complète aucun champ absent ;
  · il ne remplace aucune valeur illisible par une valeur plausible ;
  · il ne compte pas une page fabriquée comme une mesure réelle : le mode
    RÉEL exige une preuve de collecte, et cette preuve est l'empreinte du
    fichier tel qu'il est arrivé.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                     # noqa: E402

from radar import nature as nat                                 # noqa: E402
from radar import page as lecteur                               # noqa: E402
from radar import procedure as proc                             # noqa: E402
from radar import provenance as prov                            # noqa: E402
from radar import validation as val                             # noqa: E402
from radar.adaptateur import Adaptateur, vers_opportunite       # noqa: E402
from radar.base import ouvrir                                   # noqa: E402
from radar.chaine import Moteur, traiter                        # noqa: E402
from radar.mode import Mode, estampiller                        # noqa: E402

ARCHIVES = RACINE / "validation" / "pages_reelles"

PROTOCOLE = """\
╔════════════════════════════════════════════════════════════════════╗
║  PROTOCOLE — CE QUI SERA MESURÉ SUR LA PREMIÈRE PAGE RÉELLE        ║
╚════════════════════════════════════════════════════════════════════╝

POURQUOI UNE PAGE D'ENTREPRISE, ET PAS UN MARCHÉ PUBLIC
  Pas parce que le privé vaut mieux. Parce que c'est la zone qui porte le
  plus d'incertitude technique : aucun champ normé, aucune référence, aucun
  statut de procédure, aucun montant, souvent aucune date. Tout ce sur quoi
  les fixtures s'appuient y est absent.

CE QUI SERA MESURÉ — sept questions, réponses vérifiables
  1. STRUCTURE     quelle part du fichier est du texte lisible ? combien de
                   pistes de lecture répondent, et lesquelles restent muettes ?
  2. EXTRACTION    quels champs sortent réellement, et par quelle piste ?
  3. ABSENCE       quels champs n'existent pas sur cette page, et sont-ils
                   ceux que l'architecture avait ANNONCÉS comme absents ?
  4. COMPRÉHENSION la chaîne conclut-elle un besoin, un signal, ou rien ?
                   avec quelles preuves textuelles, citées ?
  5. ÉTAT          la page porte-t-elle une procédure ? si non, le radar dit-il
                   HORS PROCÉDURE, ou invente-t-il un état ?
  6. ÉCONOMIE      le score se calcule-t-il sans montant, sans durée, sans
                   cadence — ou s'effondre-t-il faute de champs ?
  7. ACTION        la fiche donne-t-elle une action utile ET la prochaine
                   question à poser, ou un verdict creux ?

CE QUI COMPTERAIT COMME UN ÉCHEC — écrit AVANT la mesure
  · un champ affiché comme lu alors qu'il ne figure pas dans la page ;
  · un état de procédure conclu sur une page qui n'en contient aucune ;
  · un INCONNU traité comme un zéro dans le score ;
  · un rejet causé par l'absence d'un mot attendu ;
  · un score qui dépend d'un champ que ce type de page ne porte jamais.

CE QUI NE COMPTERAIT PAS COMME UN ÉCHEC
  · beaucoup d'INCONNUS. Une page d'entreprise en est pleine, et c'est la
    bonne réponse. INCERTAIN vaut mieux qu'INCORRECT.
"""


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def vocabulaires() -> dict:
    sortie = {}
    for chemin in sorted((RACINE / "sources").glob("*.yaml")):
        cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
        sortie[cfg.get("source", chemin.stem)] = proc.Vocabulaire(cfg)
    return sortie


def _moteur() -> Moteur:
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=vocabulaires())


# ═══════════════════════════════════ E · conserver la page brute ═══════════
def archiver(octets: bytes, url: str, origine: str, famille: str) -> dict:
    """La preuve. Le fichier tel qu'il est arrivé, jamais réécrit."""
    empreinte = hashlib.sha256(octets).hexdigest()
    ARCHIVES.mkdir(parents=True, exist_ok=True)
    quand = datetime.now(timezone.utc).isoformat(timespec="seconds")
    nom = f"{quand[:10]}-{famille}-{empreinte[:12]}"
    fichier = ARCHIVES / f"{nom}.html"
    if not fichier.exists():
        fichier.write_bytes(octets)
    meta = {"url": url, "origine_de_la_donnee": origine, "famille": famille,
            "collecte_le": quand, "octets": len(octets),
            "sha256": empreinte, "fichier": fichier.name}
    (ARCHIVES / f"{nom}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


# ═════════════════════════════ C · les quatre niveaux, VÉRIFIÉS ════════════
def journaliser(lec: lecteur.Lecture, opp, res, meta: dict,
                source_brute: str = "") -> prov.Journal:
    """Range chaque information dans son niveau. Le journal peut refuser."""
    j = prov.Journal(lec.texte, source_brute)

    # — OBSERVÉ : demandé pour tout ce que le lecteur prétend avoir lu.
    for champ, valeur in lec.champs.items():
        j.observer(champ, valeur)

    # — INTERPRÉTÉ : les conclusions sémantiques, avec la phrase qui les porte.
    lecture_etat = res.lecture
    if lecture_etat is not None:
        if lecture_etat.procedure_detectee:
            j.interpreter("état de procédure", lecture_etat.etat_affiche,
                          regle=(lecture_etat.preuves[0].detail
                                 if lecture_etat.preuves else "hiérarchie de preuves"))
        else:
            j.deduire("état de procédure", "HORS PROCÉDURE",
                      regle="aucun marqueur de procédure trouvé dans la page")
    j.interpreter("nature", f"{res.nature.value}", regle=_regle_nature(res.nature, lec))
    j.interpreter("rôle", res.role.value,
                  regle="lexique prestation / fourniture du profil")
    if res.correspondance.familles:
        j.interpreter("métier reconnu", res.correspondance.familles,
                      regle="familles d'activité du profil")
    else:
        j.inconnu("métier reconnu",
                  question="Quelle prestation exactement — messagerie, palettes, "
                           "frigo, vrac, déménagement ?")

    # — DÉDUIT : calculé, sans support textuel direct. On le dit.
    j.deduire("zone", res.zone.zone.value,
              regle=(res.zone.raisons[0] if res.zone.raisons
                     else "géographie du profil confrontée aux pays lus"))
    j.deduire("catégorie", f"{res.classement.type.emoji} {res.classement.type.value}",
              regle="classification à partir du rôle, du métier, de la zone et des capacités")
    j.deduire("score économique", res.score.affichage,
              regle="barème économique — aveugle à la source et à l'état")
    j.deduire("fiabilité", res.fiabilite.niveau.value,
              regle=res.fiabilite.motif())
    j.deduire("preuve de collecte", meta["sha256"][:16],
              regle=f"SHA-256 du fichier conservé, {meta['octets']} octets")

    # — INCONNU : ce que la page ne porte pas. Avec la question à poser.
    for champ, question in lec.questions.items():
        j.inconnu(champ, question=question)
    for champ in lec.non_trouves:
        if champ not in lec.questions:
            j.inconnu(champ, question=f"Où trouver « {champ} » pour cette entreprise ?")
    return j


def _regle_nature(nature, lec: lecteur.Lecture) -> str:
    plat = prov.normaliser(lec.texte)
    for marqueur in ("nous recherchons", "nous cherchons", "we are looking",
                     "wij zoeken", "nous souhaitons", "devenir partenaire",
                     "rejoignez", "faites appel", "nous avons besoin"):
        if marqueur in plat:
            return f"besoin exprimé à la première personne : « {marqueur} »"
    return "aucune formulation de besoin direct trouvée — qualification par défaut"


# ═════════════════════════════════════════════ D · toute la chaîne ═════════
def mesurer(octets: bytes, url: str, origine: str, famille: str, completude: str):
    profil_page = _cfg("sources/page_web.yaml")
    meta = archiver(octets, url, origine, famille)

    html = octets.decode("utf-8", errors="replace")
    lec = lecteur.lire(html, profil_page)

    # La charge remise à l'adaptateur ne contient QUE ce qui a été lu.
    charge = {"url": url, **{k: v for k, v in lec.champs.items()
                             if k in ("intitule", "acheteur", "objet", "contact_email")}}
    # Le texte visible entier sert de matière au moteur sémantique. Il n'est pas
    # un champ « rempli » : c'est la page elle-même.
    charge["texte"] = lec.texte[:20000]
    charge = estampiller(charge, source=famille, reference=url)

    ad = Adaptateur.depuis_config(profil_page)
    opp = vers_opportunite(ad, charge, famille,
                           {"secteur": profil_page.get("secteur_par_defaut")})

    cx = ouvrir(":memory:")
    moteur = _moteur()
    # Le cycle complet, en mode RÉEL : la preuve de collecte est contrôlée, le
    # livre de comptes doit se réconcilier, sinon l'exécution s'arrête.
    bilan = traiter(cx, moteur, [opp], mode=Mode.REEL)
    res = moteur.analyser(opp)
    res.bilan_cycle = bilan

    j = journaliser(lec, opp, res, meta, source_brute=html)
    return meta, lec, opp, res, j, cx


# ══════════════════════════════════════════════════ F G I · affichage ══════
def afficher(meta, lec, opp, res, j, cx) -> str:
    L = []
    A = L.append
    A(Mode.REEL.bandeau())
    A("")
    A("═" * 72)
    A("  PREUVE DE COLLECTE — la page conservée, telle qu'elle est arrivée")
    A("═" * 72)
    A(f"  url          {meta['url']}")
    A(f"  origine      {meta['origine_de_la_donnee']}")
    A(f"  collectée    {meta['collecte_le']}")
    A(f"  fichier      validation/pages_reelles/{meta['fichier']}")
    A(f"  sha256       {meta['sha256']}")
    A(f"  taille       {meta['octets']} octets")
    A("")
    A("═" * 72)
    A("  1 · CE QUE LA PAGE EST, MATÉRIELLEMENT")
    A("═" * 72)
    A(f"  texte lisible          {lec.longueur_texte} car. sur {lec.longueur_html} "
      f"({lec.densite:.0%} du fichier)")
    A(f"  liens                  {len(lec.liens)}")
    A(f"  pistes qui répondent   {len(lec.champs)} / "
      f"{len(lec.champs) + len(lec.non_trouves)}")
    if lec.variantes:
        A("  variantes — deux pistes ne disent pas la même chose :")
        for champ, autres in lec.variantes.items():
            A(f"    {champ} : « {lec.champs[champ][:40]} » ≠ « {autres[0][:40]} »")

    A("")
    A("═" * 72)
    A("  2 · F · CE QUI A ÉTÉ RÉELLEMENT EXTRAIT, ET PAR QUELLE PISTE")
    A("═" * 72)
    if lec.champs:
        for champ, valeur in lec.champs.items():
            A(f"  ✔ {champ:<16} {str(valeur)[:70]}")
            A(f"    {'':<16} ← {lec.pistes[champ].regle}")
    else:
        A("  RIEN. Aucune piste de lecture n'a répondu sur cette page.")

    A("")
    A("═" * 72)
    A("  3 · G · CE QUI N'A PAS PU ÊTRE EXTRAIT")
    A("═" * 72)
    A("  Rien n'est comblé. Chaque ligne est une question à poser, pas un zéro.")
    A("")
    for champ, question in lec.questions.items():
        A(f"  ○ {champ:<22} INCONNU   → {question}")
    for champ in lec.non_trouves:
        if champ not in lec.questions:
            A(f"  ○ {champ:<22} INCONNU   → aucune piste déclarée n'a répondu")

    A("")
    A("═" * 72)
    A("  4 · C · LES QUATRE NIVEAUX — le niveau OBSERVÉ est VÉRIFIÉ, pas déclaré")
    A("═" * 72)
    A(j.tableau())
    A("")
    A(f"  {j.resume()}")
    if j.retrogradations():
        A("")
        A("  ⚠ NIVEAUX REFUSÉS — une valeur annoncée comme lue, absente de la page :")
        for c in j.retrogradations():
            A(f"    · {c.champ} : {c.retrograde}")

    A("")
    A("═" * 72)
    A("  5 · I · FICHE COMMERCIALE")
    A("═" * 72)
    A("")
    A(res.fiche.en_texte(avec_detail_score=True))
    A("")
    A("  ── CE QUI MANQUE POUR DÉCIDER ─────────────────────────────────────")
    manques = [c for c in j.par_niveau(prov.Niveau.INCONNU) if c.question]
    for c in manques:
        A(f"     ○ {c.champ}")
    if not manques:
        A("     (rien : la page portait tout ce qui était cherché)")
    A("")
    A("  ── PROCHAINE QUESTION ─────────────────────────────────────────────")
    A(f"     👉 {prochaine_question(lec, res, j)}")
    return "\n".join(L)


def prochaine_question(lec, res, j) -> str:
    """UNE question, celle qui débloque le plus. Pas une liste."""
    plat = prov.normaliser(lec.texte)
    if not lec.champs:
        return ("Cette page est-elle lisible sans JavaScript ? Rien n'en est "
                "sorti : il faut une autre voie d'accès avant toute analyse.")
    if "contact_email" not in lec.champs and "telephone" not in lec.champs:
        return ("Qui appeler ? La page ne porte ni adresse ni numéro : "
                "chercher la page contact avant d'engager du temps.")
    if res.nature is nat.Nature.HYPOTHESE:
        return ("Cette page décrit-elle un besoin actuel, ou seulement "
                "l'activité de l'entreprise ? Rien n'y exprime de demande.")
    for mot in ("palette", "colis", "conteneur", "frigo", "vrac", "camion"):
        if mot in plat:
            break
    else:
        return ("Quelle marchandise, et à quelle cadence ? Sans ça, "
                "ni le volume ni la marge ne sont mesurables.")
    return ("Quel volume mensuel, et le besoin est-il déjà couvert par un "
            "transporteur ? C'est ce qui décide entre CAPTER et DÉVELOPPER.")


# ═════════════════════════════════════════════════ J · rapport global ═════
def rapport_global(meta, lec, res, j, famille, completude) -> str:
    from radar import rapport as rapport_mod    # noqa: F401  (cohérence d'import)
    L = []
    A = L.append
    A("")
    A("═" * 72)
    A("  6 · J · RAPPORT GLOBAL DE LA MESURE")
    A("═" * 72)
    comptes = j.comptes()
    total = sum(comptes.values()) or 1
    A("")
    A("  RÉPARTITION DE CE QUE LE RADAR SAIT DE CETTE AFFAIRE")
    for niveau in prov.ORDRE:
        n = comptes[niveau]
        barre = "█" * int(30 * n / total)
        A(f"    {niveau.marque} {niveau.value:<20} {n:>3}  {barre}")
    A("")
    A(f"  Part de l'analyse ADOSSÉE AU TEXTE VISIBLE de la page : "
      f"{100 * comptes[prov.Niveau.OBSERVE] // total} %")
    A(f"  Part adossée au BALISAGE seul (invisible au lecteur) : "
      f"{100 * comptes[prov.Niveau.OBSERVE_BALISAGE] // total} %")
    A("  Le reste est interprété, calculé, ou reconnu inconnu. Aucune de ces")
    A("  trois catégories ne doit être présentée au client comme un fait lu.")
    A("")
    A("  MESURE INSCRITE AU REGISTRE RÉEL")
    A(f"    famille     {famille}")
    A(f"    complétude  {completude}")
    A(f"    empreinte   {meta['sha256'][:16]}")
    return "\n".join(L)


def enseignements(lec, opp, res, j) -> list[str]:
    """Ce que la donnée réelle révèle, mesuré — pas supposé."""
    out = []
    if lec.densite < 0.15:
        out.append(f"densité de texte {lec.densite:.0%} : les fixtures sont du "
                   "texte pur, une vraie page est majoritairement du balisage")
    if lec.non_trouves:
        out.append("pistes muettes : " + ", ".join(lec.non_trouves))
    if j.retrogradations():
        out.append(f"{len(j.retrogradations())} valeur(s) annoncée(s) comme lues "
                   "et absentes du texte de la page")
    comptes = j.comptes()
    if comptes[prov.Niveau.INCONNU] > comptes[prov.Niveau.OBSERVE]:
        out.append("plus d'INCONNUS que d'OBSERVÉS : c'est le régime normal "
                   "d'une page privée, et le score doit y survivre")
    if res.lecture is not None and res.lecture.procedure_detectee:
        out.append("⚠ une procédure a été détectée sur une page d'entreprise — "
                   "à vérifier : faux positif possible")
    if not lec.champs.get("contact_email"):
        out.append("aucun contact lisible : une opportunité sans porte d'entrée")
    return out


# ═══════════════════════════════════════════════════════════ CLI ══════════
def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--page", help="fichier HTML réel, tel qu'il a été reçu")
    p.add_argument("--url", default="", help="URL réelle de la page")
    p.add_argument("--origine", default="",
                   help="comment la donnée a été obtenue, exactement")
    p.add_argument("--famille", default="entreprise",
                   help="famille de source prévue par l'architecture")
    p.add_argument("--completude", default="page complète",
                   choices=["page complète", "extrait de listing", "fragment"])
    p.add_argument("--protocole", action="store_true",
                   help="afficher ce qui sera mesuré, AVANT de mesurer")
    p.add_argument("--etat", action="store_true",
                   help="afficher l'état de validation du radar")
    a = p.parse_args(argv)

    if a.protocole:
        print(PROTOCOLE)
        return 0
    if a.etat:
        print(val.etat().rendu())
        return 0
    if not a.page:
        print(PROTOCOLE)
        print("─" * 72)
        print(val.etat().rendu())
        print()
        print("Pour mesurer, il faut une VRAIE page :")
        print("  python3 outils/premiere_page_reelle.py --page fichier.html \\")
        print("      --url https://... --origine \"comment elle a été obtenue\"")
        print()
        print("Le réseau sortant est fermé dans cet environnement : le fichier")
        print("doit être fourni. Fabriquer une page ici en ferait un fixture")
        print("déguisé, et le compteur RÉEL resterait mensonger.")
        return 1

    chemin = Path(a.page)
    if not chemin.exists():
        print(f"fichier introuvable : {chemin}", file=sys.stderr)
        return 2
    if not a.origine:
        print("--origine est OBLIGATOIRE : sans elle, on ne peut pas dire "
              "comment la donnée a été obtenue, et la mesure ne prouve rien.",
              file=sys.stderr)
        return 2

    octets = chemin.read_bytes()
    meta, lec, opp, res, j, cx = mesurer(
        octets, a.url or chemin.name, a.origine, a.famille, a.completude)

    print(afficher(meta, lec, opp, res, j, cx))
    print(rapport_global(meta, lec, res, j, a.famille, a.completude))

    lecons = enseignements(lec, opp, res, j)
    print()
    print("  CE QUE CETTE DONNÉE RÉELLE RÉVÈLE, QUE LES FIXTURES NE MONTRAIENT PAS")
    for l in lecons:
        print(f"    · {l}")
    if not lecons:
        print("    · rien : la page s'est comportée comme les fixtures le prévoyaient")

    comptes = {n.value: v for n, v in j.comptes().items()}
    val.inscrire(val.Mesure(
        horodatage=meta["collecte_le"], famille=a.famille,
        origine=a.origine, reference=meta["url"], empreinte=meta["sha256"],
        page_conservee=meta["fichier"], completude=a.completude,
        verdict=f"{res.classement.type.emoji} {res.classement.type.value} "
                f"· score {res.score.affichage} · {res.classement.action.value}",
        porte_un_besoin=res.classement.type.notifiable,
        constats=comptes, enseignements=lecons))
    print()
    print(val.etat().rendu())
    return 0


if __name__ == "__main__":
    sys.exit(principal())
