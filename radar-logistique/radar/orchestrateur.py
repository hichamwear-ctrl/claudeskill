"""UN CYCLE COMPLET — et le journal de ce que le bot a RÉELLEMENT fait.

    SOURCE / IMPORT / COLLECTE → DÉCOUVERTE → DÉDUPLICATION → QUALIFICATION
    → IDENTIFICATION → CANDIDAT → OPPORTUNITÉ → NATURE / PROCÉDURE
    → CLASSIFICATION → CAPACITÉ → SCORE → ACTION → SURVEILLANCE
    → NOTIFICATION → SUIVI → RÉSULTAT → APPRENTISSAGE OBSERVÉ

Ce module ORCHESTRE. Il n'écrit aucune règle métier : chaque maillon appelle
le module déjà validé qui en a la charge, et le bot ne fait que les enchaîner
dans l'ordre et compter ce qui s'est passé.

LA GARANTIE CENTRALE DU BOT
===========================

    source injoignable  →  NON MESURÉE
    et JAMAIS              « 0 opportunité pour cette source »

Une absence de résultat n'est pas une preuve d'absence d'opportunité. Un
journal qui confond les deux rend le radar menteur sans que personne le voie
— et c'est le défaut le plus coûteux qu'un radar commercial puisse avoir,
parce qu'il ressemble à un succès.

Les cinq états d'une source sont donc conservés SÉPARÉMENT, en toutes
lettres, et jamais additionnés :

    EXÉCUTÉE · ERREUR · NON DISPONIBLE · NON MESURÉE · DEMANDÉE

TROIS CAPACITÉS QUI NE SE CONFONDENT PAS
========================================

    A · CAPACITÉ DU BOT           ce que le code sait exécuter
    B · CAPACITÉ DE L'ENVIRONNEMENT  ce que la machine autorise
    C · CAPACITÉ DE LA SOURCE     ce que la source permettrait

Le bot sait appeler un moteur (A). L'environnement bloque la sortie réseau
(B). La source n'a donc jamais été testée (C). Le résultat s'écrit
NON MESURÉ — et surtout pas « cette source ne contient rien ».

CE QUE LE BOT NE FAIT JAMAIS
============================

Il ne contacte personne, n'envoie aucun courriel, ne postule à rien,
n'accepte aucun marché. Il ne modifie ni règle, ni score, ni seuil, ni
lexique, ni ontologie, ni priorité de source. Il ne transforme pas une
hypothèse en fait, ni un signal en opportunité, ni une attribution en marché
postulable.

Il prépare. L'humain décide.

IDEMPOTENCE
===========

Relancer le même cycle sur les mêmes données ne crée ni seconde opportunité,
ni seconde entreprise, ni seconde notification. La déduplication d'URL, la
clé d'avis et le sceau de notification s'en chargent, chacun à son niveau.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import notification as mod_notification

COMPLET = "COMPLET"
PARTIEL = "PARTIEL"
ERREUR = "ERREUR"

NON_MESUREE = "NON MESURÉE"


@dataclass
class EtatSource:
    """Ce qu'une source a RÉELLEMENT fait pendant ce cycle."""
    nom: str
    etat: str = NON_MESUREE
    resultats: int | str = NON_MESUREE
    opportunites: int | str = NON_MESUREE
    motif: str | None = None
    derniere_consultation: str | None = None

    def ligne(self) -> str:
        r = self.resultats if isinstance(self.resultats, str) else str(self.resultats)
        o = self.opportunites if isinstance(self.opportunites, str) else str(self.opportunites)
        return (f"  {self.nom[:26]:<28} {self.etat:<16} {r:>12} rés."
                f" {o:>12} opp."
                + (f"   {self.motif[:44]}" if self.motif else ""))


@dataclass
class Cycle:
    """Le journal d'un passage. Chaque nombre est un compte d'observations."""
    cycle_id: str
    debut: str
    fin: str | None = None
    statut: str = PARTIEL
    sources: dict = field(default_factory=dict)
    resultats_bruts: int = 0
    urls_uniques: int = 0
    doublons: int = 0
    pages_analysees: int = 0
    candidats: int = 0
    entreprises: int = 0
    opportunites: int = 0
    signaux: int = 0
    postulables: int = 0
    attribues: int = 0
    rejetes: int = 0
    notifications: int = 0
    erreurs: list = field(default_factory=list)

    # ── les cinq états, jamais additionnés ──
    def _noms(self, etat) -> list[str]:
        return sorted(s.nom for s in self.sources.values() if s.etat == etat)

    @property
    def demandees(self) -> list[str]:
        return sorted(self.sources)

    @property
    def executees(self) -> list[str]:
        return self._noms("EXÉCUTÉE")

    @property
    def en_erreur(self) -> list[str]:
        return self._noms("ERREUR")

    @property
    def non_disponibles(self) -> list[str]:
        return self._noms("NON DISPONIBLE")

    @property
    def non_mesurees(self) -> list[str]:
        return self._noms(NON_MESUREE)


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _identifiant() -> str:
    """Horodatage À LA MILLISECONDE, plus un jeton court.

    À la seconde près, deux cycles lancés coup sur coup portaient le MÊME
    identifiant et le second écrasait le premier au journal — le bot perdait
    la trace d'un passage qu'il avait bel et bien effectué. Un journal qui
    oublie un cycle ne vaut pas mieux que pas de journal.
    """
    import secrets
    quand = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")[:-3]
    return f"{quand}-{secrets.token_hex(2)}"


def demarrer(cycle_id=None) -> Cycle:
    return Cycle(cycle_id=cycle_id or _identifiant(), debut=_maintenant())


def declarer_source(cycle: Cycle, nom: str, *, etat=NON_MESUREE, resultats=None,
                    opportunites=None, motif=None, derniere=None) -> EtatSource:
    """Déclare une source AVANT de l'interroger.

    Elle naît NON MESURÉE. C'est l'état par défaut et c'est volontaire : tant
    qu'on ne l'a pas interrogée, on ne sait rien d'elle — surtout pas qu'elle
    ne contient rien.
    """
    s = EtatSource(nom=nom, etat=etat,
                   resultats=NON_MESUREE if resultats is None else resultats,
                   opportunites=NON_MESUREE if opportunites is None else opportunites,
                   motif=motif, derniere_consultation=derniere)
    cycle.sources[nom] = s
    return s


def _mesurer(cx, cycle: Cycle) -> None:
    """Lit l'état de la base APRÈS coup. Rien n'est recalculé de tête."""
    from .pages import Acces, Statut as StatutPage

    def compte(sql, args=()):
        return cx.execute(sql, args).fetchone()[0]

    cycle.resultats_bruts = compte("SELECT count(*) FROM trouvailles")
    cycle.urls_uniques = compte("SELECT count(DISTINCT url) FROM trouvailles")
    cycle.doublons = cycle.resultats_bruts - cycle.urls_uniques
    cycle.pages_analysees = compte(
        "SELECT count(*) FROM pages_surveillees WHERE acces=?",
        (Acces.CONSULTEE.value,))
    cycle.candidats = compte(
        "SELECT count(*) FROM pages_surveillees WHERE statut=?",
        (StatutPage.CANDIDATE.value,))
    cycle.entreprises = compte("SELECT count(*) FROM entreprises")
    cycle.opportunites = compte("SELECT count(*) FROM opportunites")
    cycle.signaux = compte("SELECT count(*) FROM opportunites WHERE nature='SIGNAL'")
    cycle.postulables = compte(
        "SELECT count(*) FROM opportunites WHERE etat_procedure='POSTULABLE'")
    cycle.attribues = compte("SELECT count(*) FROM attributions")
    cycle.rejetes = compte("SELECT count(*) FROM opportunites WHERE type='REJET'")


def _statut(cycle: Cycle) -> str:
    """COMPLET seulement si TOUTES les sources demandées ont répondu.

    Un cycle où une source est restée injoignable n'est pas complet, même si
    tout le reste a parfaitement fonctionné. Le dire PARTIEL est la seule
    façon de ne pas laisser croire qu'on a tout vu.
    """
    if cycle.erreurs and not cycle.executees:
        return ERREUR
    if not cycle.sources:
        return PARTIEL
    return COMPLET if len(cycle.executees) == len(cycle.sources) else PARTIEL


def terminer(cx, cycle: Cycle) -> Cycle:
    _mesurer(cx, cycle)
    cycle.fin = _maintenant()
    cycle.statut = _statut(cycle)
    cx.execute(
        "INSERT INTO journal_cycles(cycle_id, debut, fin, statut,"
        " sources_demandees, sources_executees, sources_erreur,"
        " sources_non_disponibles, sources_non_mesurees, resultats_bruts,"
        " urls_uniques, doublons, pages_analysees, candidats, entreprises,"
        " opportunites, signaux, postulables, attribues, rejetes,"
        " notifications, erreurs, detail)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(cycle_id) DO UPDATE SET fin=excluded.fin,"
        "   statut=excluded.statut, resultats_bruts=excluded.resultats_bruts,"
        "   urls_uniques=excluded.urls_uniques, doublons=excluded.doublons,"
        "   pages_analysees=excluded.pages_analysees,"
        "   candidats=excluded.candidats, entreprises=excluded.entreprises,"
        "   opportunites=excluded.opportunites, signaux=excluded.signaux,"
        "   postulables=excluded.postulables, attribues=excluded.attribues,"
        "   rejetes=excluded.rejetes, notifications=excluded.notifications,"
        "   erreurs=excluded.erreurs",
        (cycle.cycle_id, cycle.debut, cycle.fin, cycle.statut,
         json.dumps(cycle.demandees, ensure_ascii=False),
         json.dumps(cycle.executees, ensure_ascii=False),
         json.dumps(cycle.en_erreur, ensure_ascii=False),
         json.dumps(cycle.non_disponibles, ensure_ascii=False),
         json.dumps(cycle.non_mesurees, ensure_ascii=False),
         cycle.resultats_bruts, cycle.urls_uniques, cycle.doublons,
         cycle.pages_analysees, cycle.candidats, cycle.entreprises,
         cycle.opportunites, cycle.signaux, cycle.postulables,
         cycle.attribues, cycle.rejetes, cycle.notifications,
         json.dumps(cycle.erreurs, ensure_ascii=False),
         json.dumps({n: vars(s) for n, s in cycle.sources.items()},
                    ensure_ascii=False, default=str)))
    return cycle


# ═══════════════════════════════════════════════════ le cycle
def executer(cx, moteur, adaptateur, *, imports=None, collectes=None,
             moteurs_declares=None, profil=None, cycle_id=None,
             notifier: bool = True) -> Cycle:
    """UN CYCLE. Chaque maillon appelle le module qui en a la charge.

    `imports` : fichiers d'export de recherche produits HORS RADAR.
    `collectes` : fichiers de pages lues HORS RADAR.
    `moteurs_declares` : les moteurs connus, disponibles ou non — ils
        apparaissent au journal même sans être interrogés, précisément pour
        qu'on voie qu'ils n'ont PAS été interrogés.
    """
    from . import (collecte_importee as col, import_externe as imp,
                   parcours, trouvailles as tr)
    from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE
    from .mode import Mode

    cycle = demarrer(cycle_id)

    # ── 1. LES MOTEURS DÉCLARÉS — vus, et non interrogés ──
    for m in moteurs_declares or []:
        nom = getattr(m, "nom", str(m))
        if getattr(m, "disponible", False):
            declarer_source(cycle, nom, etat=NON_MESUREE,
                            motif="disponible mais NON INTERROGÉ par ce cycle")
        else:
            declarer_source(cycle, nom, etat="NON DISPONIBLE",
                            motif=getattr(m, "motif_indisponibilite", None))

    # ── 2. IMPORTS — une recherche exécutée AILLEURS ──
    avant = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
    for chemin in imports or []:
        try:
            bilan = imp.importer(cx, chemin)
        except Exception as e:                                   # noqa: BLE001
            cycle.erreurs.append(f"import {chemin} : {e}")
            declarer_source(cycle, f"import:{chemin}", etat="ERREUR",
                            motif=str(e)[:80])
            continue
        for nom in bilan.moteurs or []:
            from .execution import qualifier
            declarer_source(cycle, qualifier(nom), etat="EXÉCUTÉE",
                            resultats=bilan.inscrites, opportunites=0,
                            motif=f"{imp.PROVENANCE} — {bilan.refusees} refusée(s)",
                            derniere=_maintenant())

    # ── 3. DÉCOUVERTE → … → ACTION, par la chaîne déjà validée ──
    if imports:
        p = parcours.executer(cx, moteur, adaptateur, mode=Mode.REEL,
                              defauts={"circuit": CIRCUIT_DECOUVERTE})
        apres = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        produites = apres - avant
        for s in cycle.sources.values():
            if s.etat == "EXÉCUTÉE" and s.opportunites == 0:
                s.opportunites = produites
                produites = 0

    # ── 4. COLLECTE — des pages lues AILLEURS, puis la veille ──
    for chemin in collectes or []:
        try:
            trace, fichier, visitees = col.surveiller(
                cx, chemin, moteur, profil=profil)
            declarer_source(cycle, f"collecte:{fichier}", etat="EXÉCUTÉE",
                            resultats=visitees, opportunites=trace.opportunites,
                            motif=col.PROVENANCE, derniere=_maintenant())
        except Exception as e:                                   # noqa: BLE001
            cycle.erreurs.append(f"collecte {chemin} : {e}")
            declarer_source(cycle, f"collecte:{chemin}", etat="ERREUR",
                            motif=str(e)[:80])

    # ── 5. NOTIFICATIONS — préparées, jamais envoyées ──
    if notifier:
        cycle.notifications = len(
            mod_notification.preparer(cx, cycle_id=cycle.cycle_id))

    return terminer(cx, cycle)


# ═══════════════════════════════════════════════════ rapport
def rapport(cx, cycle: Cycle) -> str:
    from . import tableau, verdicts

    L = ["═" * 78, f"RADAR COMMERCIAL — CYCLE {cycle.cycle_id}", "═" * 78, ""]
    L.append(f"STATUT : {cycle.statut}")
    L.append(f"  début {cycle.debut}   fin {cycle.fin}")
    if cycle.statut == PARTIEL:
        L.append("  PARTIEL : au moins une source n'a pas répondu. Ce n'est pas")
        L.append("  un échec du cycle — c'est un aveu sur ce qu'on n'a pas vu.")
    L.append("")

    L.append("SOURCES")
    if not cycle.sources:
        L.append("  aucune source déclarée pour ce cycle")
    L.append(f"  {'SOURCE':<28} {'ÉTAT':<16} {'RÉSULTATS':>12} {'OPPORTUNITÉS':>17}")
    for nom in cycle.demandees:
        L.append(cycle.sources[nom].ligne())
    L.append("")
    for libelle, noms in (("exécutées", cycle.executees),
                          ("en ERREUR", cycle.en_erreur),
                          ("NON DISPONIBLES", cycle.non_disponibles),
                          ("NON MESURÉES", cycle.non_mesurees)):
        L.append(f"  {libelle:<20} {len(noms)}"
                 + (f"   {', '.join(noms)[:52]}" if noms else ""))
    if cycle.non_mesurees or cycle.non_disponibles:
        L.append("")
        L.append("  ⚠ UNE SOURCE NON MESURÉE N'A PAS « RENDU ZÉRO ». Le bot ne")
        L.append("  l'a pas interrogée, ou n'a pas pu. On ne sait donc RIEN de")
        L.append("  ce qu'elle contient — surtout pas qu'elle ne contient rien.")

    L.append("")
    L.append("DÉCOUVERTE")
    for cle, libelle in (("resultats_bruts", "résultats bruts"),
                         ("urls_uniques", "URL uniques"),
                         ("doublons", "doublons regroupés")):
        L.append(f"  {libelle:<28} {getattr(cycle, cle):>6}")

    L.append("")
    L.append("QUALIFICATION")
    for cle, libelle in (("pages_analysees", "pages réellement lues"),
                         ("candidats", "pages candidates"),
                         ("entreprises", "entreprises au registre")):
        L.append(f"  {libelle:<28} {getattr(cycle, cle):>6}")

    L.append("")
    L.append("OPPORTUNITÉS")
    for cle, libelle in (("opportunites", "opportunités en base"),
                         ("signaux", "dont SIGNAL"),
                         ("postulables", "état POSTULABLE"),
                         ("attribues", "attributions (≠ postulable)"),
                         ("rejetes", "REJET")):
        L.append(f"  {libelle:<28} {getattr(cycle, cle):>6}")

    L.append("")
    L.append(f"ALERTES — {cycle.notifications} préparée(s) par ce cycle")
    L.append("  Le bot n'a envoyé AUCUN message et n'a contacté personne.")
    L.append("  Une opportunité non notifiée reste en base : ne pas réveiller")
    L.append("  quelqu'un n'est pas supprimer une affaire.")

    if cycle.erreurs:
        L.append("")
        L.append("ERREURS")
        for e in cycle.erreurs:
            L.append(f"  · {e[:72]}")

    L.append("")
    L.append("QUALITÉ")
    m = verdicts.metriques(cx)
    if not m["juges"]:
        L.append("  NON MESURÉE — aucun résultat n'a été relu par un humain.")
        L.append("  Ce n'est pas « zéro erreur » : c'est l'absence de relecture.")
    else:
        for v in verdicts.Verdict:
            L.append(f"  {v.emoji} {v.value:<26} {m[v.value]:>5}")
        L.append(f"  {'PRÉCISION':<28} {m['precision'] if isinstance(m['precision'], str) else format(m['precision'], '.0%')}")

    L.append("")
    L.append("ACTIONS HUMAINES À EFFECTUER")
    actions = cx.execute(
        "SELECT action, count(*) n FROM opportunites"
        " WHERE action IS NOT NULL AND type NOT IN ('REJET',"
        " 'PAS ENCORE UNE OPPORTUNITÉ') GROUP BY action ORDER BY n DESC")
    vides = True
    for l in actions:
        vides = False
        L.append(f"  {l['action']:<46} {l['n']:>4}")
    if vides:
        L.append("  aucune — rien ne demande votre intervention dans cet état")
    L.append("")
    L.append("  `radar notifications` pour lire les cartes.")
    L.append("  `radar tableau` pour la boucle complète.")
    return "\n".join(L)


def journal(cx, limite: int = 10) -> str:
    L = ["JOURNAL DES CYCLES", "=" * 92, ""]
    lignes = cx.execute(
        "SELECT * FROM journal_cycles ORDER BY id DESC LIMIT ?",
        (int(limite),)).fetchall()
    if not lignes:
        L.append("  aucun cycle exécuté")
        return "\n".join(L)
    L.append(f"  {'CYCLE':<18} {'STATUT':<9} {'RÉS.':>6} {'OPP.':>6} "
             f"{'NOTIF':>6}  SOURCES NON MESURÉES")
    for l in lignes:
        non_mesurees = json.loads(l["sources_non_mesurees"] or "[]")
        L.append(f"  {l['cycle_id']:<18} {l['statut']:<9} "
                 f"{l['resultats_bruts']:>6} {l['opportunites']:>6} "
                 f"{l['notifications']:>6}  "
                 + (", ".join(non_mesurees)[:44] or "—"))
    L.append("")
    L.append("  Une source NON MESURÉE n'a pas rendu zéro : elle n'a pas été")
    L.append("  interrogée. Les deux ne se confondent jamais dans ce journal.")
    return "\n".join(L)
