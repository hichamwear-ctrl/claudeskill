"""LA BOUCLE COMMERCIALE, MESURÉE DE BOUT EN BOUT.

    DÉCOUVERTE → QUALIFICATION → OPPORTUNITÉ → ACTION → CONTACT
               → SUIVI → RÉSULTAT → SURVEILLANCE → NOUVELLE OPPORTUNITÉ

Ce module COMPTE. Il ne décide rien, ne classe rien, ne priorise rien.

AUCUNE SOURCE N'EST PRIORISÉE ICI
=================================

Le tableau met les sources côte à côte — résultats, pertinence, opportunités,
contacts, contrats. Il ne les trie pas par mérite et n'en promeut aucune.

C'est volontaire, et c'est la règle de l'étape : le radar doit d'abord
OBSERVER. Une source qui rend mille résultats et zéro contrat ne vaut pas
mieux qu'une source qui en rend dix et un contrat — mais décider laquelle
privilégier est une décision métier, et elle n'est pas prise.

UN CHIFFRE ABSENT NE VAUT PAS ZÉRO
==================================

La marge reste NON MESURÉE tant que les coûts d'exploitation ne sont pas au
profil. Le CA reste NON PUBLIÉ quand la source ne le dit pas. Aucun de ces
manques n'est comblé par une estimation : une estimation affichée à côté
d'un chiffre mesuré se lit comme un chiffre mesuré.

TROIS CHOSES QUI NE SE CONFONDENT JAMAIS
========================================

    SIGNAL             il se passe quelque chose
    BESOIN             quelqu'un a écrit qu'il cherchait
    OPPORTUNITÉ POSTULABLE  une consultation est ouverte

Le tableau les compte SÉPARÉMENT. Les additionner donnerait un total qui ne
veut rien dire, et qui flatterait le radar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import verdicts as mod_verdicts
from .verdicts import ECHANTILLON_INSUFFISANT, NON_MESURE

NON_PUBLIE = "NON PUBLIÉ"
MARGE_NON_MESUREE = "NON MESURÉE"

# Les statuts commerciaux, dans l'ordre de la boucle. Lus sur `suivi.Statut`
# plutôt que réécrits : deux listes finiraient par diverger.
def _statuts():
    from .suivi import Statut
    return list(Statut)


@dataclass
class Tableau:
    """Les cinq blocs demandés, et rien de plus."""
    decouverte: dict = field(default_factory=dict)
    qualification: dict = field(default_factory=dict)
    qualite: dict = field(default_factory=dict)
    commercial: dict = field(default_factory=dict)
    valeur: dict = field(default_factory=dict)
    par_source: dict = field(default_factory=dict)


def _compte(cx, sql, args=()):
    return cx.execute(sql, args).fetchone()[0]


def mesurer(cx) -> Tableau:
    from .pages import Acces, Qualification, Statut as StatutPage
    from .suivi import Statut

    t = Tableau()

    # ── DÉCOUVERTE ──
    t.decouverte = {
        "resultats_bruts": _compte(cx, "SELECT count(*) FROM trouvailles"),
        "urls_uniques": _compte(cx, "SELECT count(DISTINCT url) FROM trouvailles"),
        "sources": _compte(cx, "SELECT count(DISTINCT source) FROM trouvailles"),
        "requetes": _compte(cx, "SELECT count(DISTINCT requete) FROM trouvailles"
                                " WHERE requete IS NOT NULL"),
    }
    t.decouverte["doublons"] = (t.decouverte["resultats_bruts"]
                                - t.decouverte["urls_uniques"])

    # ── QUALIFICATION ──
    t.qualification = {
        "candidates": _compte(cx, "SELECT count(*) FROM pages_surveillees"
                                  " WHERE statut=?", (StatutPage.CANDIDATE.value,)),
        "surveillees": _compte(cx, "SELECT count(*) FROM pages_surveillees"
                                   " WHERE statut=?", (StatutPage.SURVEILLEE.value,)),
        "collectees": _compte(cx, "SELECT count(*) FROM pages_surveillees"
                                  " WHERE acces=?", (Acces.CONSULTEE.value,)),
        "qualifiees": _compte(cx, "SELECT count(*) FROM pages_surveillees"
                                  " WHERE qualification<>?",
                              (Qualification.NON_QUALIFIEE.value,)),
        "preuves": _compte(cx, "SELECT count(*) FROM pages_surveillees"
                               " WHERE qualification=?", (Qualification.PREUVE.value,)),
        "opportunites": _compte(cx, "SELECT count(*) FROM opportunites"),
    }

    # ── NATURE, ÉTAT — trois choses qui ne se confondent jamais ──
    t.qualification["signaux"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE nature='SIGNAL'")
    t.qualification["faits"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE nature='FAIT'")
    t.qualification["hypotheses"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE nature='HYPOTHÈSE'")
    t.qualification["postulables"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE etat_procedure='POSTULABLE'")
    t.qualification["attribuees"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE etat_procedure='ATTRIBUÉ'")

    # ── QUALITÉ ──
    t.qualite = mod_verdicts.metriques(cx)

    # ── COMMERCIAL ──
    t.commercial = {s.value: _compte(
        cx, "SELECT count(*) FROM opportunites WHERE etat=?", (s.value,))
        for s in _statuts()}
    t.commercial["sans_statut"] = _compte(
        cx, "SELECT count(*) FROM opportunites WHERE etat IS NULL")
    t.commercial["actions"] = {
        l["action"]: l["n"] for l in cx.execute(
            "SELECT action, count(*) n FROM opportunites"
            " WHERE action IS NOT NULL AND type<>'REJET' GROUP BY action")}
    t.commercial["attributions"] = _compte(cx, "SELECT count(*) FROM attributions")
    t.commercial["renouvellements"] = _compte(
        cx, "SELECT count(*) FROM attributions WHERE renouvellement IS NOT NULL")

    # ── VALEUR — jamais estimée ──
    gagnees = cx.execute(
        "SELECT ca_annuel, ca_etat FROM opportunites WHERE etat=?",
        (Statut.GAGNEE.value,)).fetchall()
    mesures = [l["ca_annuel"] for l in gagnees if l["ca_annuel"]]
    potentiel = [l["ca_annuel"] for l in cx.execute(
        "SELECT ca_annuel FROM opportunites WHERE type<>'REJET'"
        " AND ca_annuel IS NOT NULL").fetchall()]
    t.valeur = {
        "gagnees": len(gagnees),
        "ca_gagne": sum(mesures) if mesures else NON_PUBLIE,
        "ca_gagne_mesure_sur": f"{len(mesures)} sur {len(gagnees)}",
        "potentiel": sum(x["ca_annuel"] for x in
                         cx.execute("SELECT ca_annuel FROM opportunites"
                                    " WHERE type<>'REJET' AND ca_annuel IS NOT NULL"))
                     if potentiel else NON_PUBLIE,
        "marge": MARGE_NON_MESUREE,
        "cout": NON_MESURE,
    }

    t.par_source = par_source(cx)
    return t


def par_source(cx) -> dict:
    """Source → résultats → pertinence → opportunités → contacts → contrats.

    Côte à côte, sans classement. Le tri est ALPHABÉTIQUE, délibérément : un
    tri par volume ferait lire un classement de mérite là où il n'y en a pas.
    """
    from .suivi import Statut
    sortie: dict = {}
    for l in cx.execute("SELECT source, count(*) n,"
                        " count(DISTINCT url) u FROM trouvailles GROUP BY source"):
        sortie[l["source"]] = {"resultats": l["n"], "urls": l["u"],
                               "opportunites": 0, "retenues": 0, "contactees": 0,
                               "gagnees": 0, "perdues": 0,
                               "vrais_positifs": 0, "faux_positifs": 0}
    for l in cx.execute(
            "SELECT a.source, o.type, o.etat, count(*) n"
            " FROM opportunites o JOIN avis a ON a.id=o.avis_id"
            " GROUP BY a.source, o.type, o.etat"):
        c = sortie.setdefault(l["source"], {
            "resultats": 0, "urls": 0, "opportunites": 0, "retenues": 0,
            "contactees": 0, "gagnees": 0, "perdues": 0,
            "vrais_positifs": 0, "faux_positifs": 0})
        c["opportunites"] += l["n"]
        if l["type"] not in ("REJET", "PAS ENCORE UNE OPPORTUNITÉ"):
            c["retenues"] += l["n"]
        if l["etat"] == Statut.CONTACTEE.value:
            c["contactees"] += l["n"]
        elif l["etat"] == Statut.GAGNEE.value:
            c["gagnees"] += l["n"]
        elif l["etat"] == Statut.PERDUE.value:
            c["perdues"] += l["n"]
    for j in mod_verdicts.tous(cx):
        if not j.source:
            continue
        c = sortie.get(j.source)
        if c is None:
            continue
        if j.verdict is mod_verdicts.Verdict.VRAI_POSITIF:
            c["vrais_positifs"] += 1
        elif j.verdict is mod_verdicts.Verdict.FAUX_POSITIF:
            c["faux_positifs"] += 1
    return sortie


def rapport(cx) -> str:
    t = mesurer(cx)
    L = ["LA BOUCLE COMMERCIALE — MESURÉE", "=" * 88, ""]

    L.append("DÉCOUVERTE")
    for cle, libelle in (("resultats_bruts", "résultats bruts"),
                         ("urls_uniques", "URL uniques"),
                         ("doublons", "doublons"), ("sources", "sources"),
                         ("requetes", "requêtes")):
        L.append(f"  {libelle:<28} {t.decouverte[cle]:>6}")

    L.append("")
    L.append("QUALIFICATION")
    for cle, libelle in (("candidates", "pages candidates"),
                         ("surveillees", "pages SURVEILLÉES"),
                         ("collectees", "pages réellement lues"),
                         ("qualifiees", "pages qualifiées"),
                         ("preuves", "dont PREUVE DE CONTENU"),
                         ("opportunites", "opportunités")):
        L.append(f"  {libelle:<28} {t.qualification[cle]:>6}")

    L.append("")
    L.append("SIGNAL ≠ BESOIN ≠ POSTULABLE — comptés séparément")
    for cle, libelle in (("signaux", "SIGNAL"), ("faits", "FAIT"),
                         ("hypotheses", "HYPOTHÈSE"),
                         ("postulables", "état POSTULABLE"),
                         ("attribuees", "état ATTRIBUÉ")):
        L.append(f"  {libelle:<28} {t.qualification[cle]:>6}")
    L.append("  Les additionner donnerait un total qui ne veut rien dire.")

    L.append("")
    L.append("QUALITÉ — jugée par un humain, jamais par le radar")
    if not t.qualite["juges"]:
        L.append(f"  {NON_MESURE} — aucun résultat relu.")
        L.append("  Ce n'est pas « zéro erreur » : c'est l'absence de relecture.")
    else:
        for v in mod_verdicts.Verdict:
            L.append(f"  {v.emoji} {v.value:<26} {t.qualite[v.value]:>6}")
        for cle, libelle in (("precision", "PRÉCISION"), ("rappel", "RAPPEL")):
            v = t.qualite[cle]
            L.append(f"  {libelle:<28} {v:>6.0%}" if isinstance(v, float)
                     else f"  {libelle:<28} {v}")

    L.append("")
    L.append("COMMERCIAL — le parcours de la relation")
    for s in _statuts():
        L.append(f"  {s.value:<28} {t.commercial[s.value]:>6}")
    L.append(f"  {'jamais regardées':<28} {t.commercial['sans_statut']:>6}")
    L.append(f"  {'attributions':<28} {t.commercial['attributions']:>6}"
             f"   dont {t.commercial['renouvellements']} avec renouvellement")

    if t.commercial["actions"]:
        L.append("")
        L.append("ACTIONS — la classification ne les décide pas seule")
        for action, n in sorted(t.commercial["actions"].items(),
                                key=lambda x: -x[1]):
            L.append(f"  {action:<44} {n:>5}")

    L.append("")
    L.append("VALEUR — jamais estimée")
    L.append(f"  {'affaires GAGNÉES':<28} {t.valeur['gagnees']:>6}")
    ca = t.valeur["ca_gagne"]
    L.append(f"  {'CA gagné':<28} "
             + (f"{ca:>6,.0f} €".replace(",", " ") if isinstance(ca, (int, float))
                else f"{ca}")
             + f"   (mesuré sur {t.valeur['ca_gagne_mesure_sur']})")
    pot = t.valeur["potentiel"]
    L.append(f"  {'potentiel publié':<28} "
             + (f"{pot:>6,.0f} €".replace(",", " ")
                if isinstance(pot, (int, float)) else f"{pot}"))
    L.append(f"  {'MARGE':<28} {t.valeur['marge']}")
    L.append(f"  {'COÛT':<28} {t.valeur['cout']}")
    L.append("  La marge reste NON MESURÉE tant que les coûts d'exploitation")
    L.append("  ne sont pas au profil. Aucun coût n'est fabriqué.")

    L.append("")
    L.append("PAR SOURCE — côte à côte, SANS CLASSEMENT")
    L.append(f"  {'SOURCE':<26} {'RÉS.':>6} {'URL':>5} {'OPP.':>5} "
             f"{'RETENUES':>9} {'CONTACT':>8} {'GAGNÉ':>6} {'VP':>4} {'FP':>4}")
    for source in sorted(t.par_source):
        c = t.par_source[source]
        L.append(f"  {source[:26]:<26} {c['resultats']:>6} {c['urls']:>5} "
                 f"{c['opportunites']:>5} {c['retenues']:>9} "
                 f"{c['contactees']:>8} {c['gagnees']:>6} "
                 f"{c['vrais_positifs']:>4} {c['faux_positifs']:>4}")
    if not t.par_source:
        L.append("  aucune source — aucune découverte en base")
    L.append("")
    L.append("  Le tri est ALPHABÉTIQUE, délibérément. Un tri par volume ferait")
    L.append("  lire un classement de mérite là où il n'y en a pas. Une petite")
    L.append("  source peut valoir mieux qu'une grosse — et le radar ne décide")
    L.append("  PAS encore laquelle privilégier. Il observe.")

    manques = mod_verdicts.tous(cx, verdict=mod_verdicts.Verdict.FAUX_NEGATIF)
    if manques:
        L.append("")
        L.append("CE QUE LE RADAR A MANQUÉ — jamais masqué")
        for j in manques:
            L.append("  " + j.ligne())

    L.append("")
    L.append("APPRENTISSAGE — préparé, PAS activé")
    L.append("  Ces chiffres existent pour qu'on puisse un jour apprendre")
    L.append("  quelle source produit du business. Aucun poids, aucun seuil,")
    L.append("  aucune priorité, aucun lexique n'est modifié à partir d'eux.")
    L.append("  Le radar observe d'abord.")
    return "\n".join(L)
