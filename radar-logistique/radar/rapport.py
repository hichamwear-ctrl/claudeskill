"""Le rapport de mesure — ce que le radar a RÉELLEMENT trouvé.

Il ne force jamais un TOP 20 : s'il n'y a rien de bon dans l'échantillon, il le
dit. Et il porte son mode en tête, pour qu'une capture d'écran ne puisse pas
être prise pour un résultat réel si elle n'en est pas un.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .mode import Mode

# Les sélections du rapport réel. Chacune répond à une question posée
# explicitement : « qu'est-ce qui est près du dépôt ? », « qu'est-ce qui est
# trop gros pour moi seul ? ». Une sélection vide le dit — elle ne disparaît
# pas de la page.
@dataclass
class Selection:
    titre: str
    explication: str
    vide: str
    lignes: list = field(default_factory=list)


EMOJIS = {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
          "PROSPECT": "🔵", "REJET": "🔴"}

CHAMPS_COMPLETUDE = (
    ("acheteur", "acheteur"), ("échéance", "echeance"), ("montant", "montant"),
    ("durée", "duree_mois"), ("cadence", "cadence"), ("lots", "lot_numero"),
    ("contact", "contact"), ("zone", "zone"), ("exigences", "exigences"),
)


@dataclass
class Rapport:
    mode: Mode
    genere_le: str = ""
    sources: dict = field(default_factory=dict)
    total: int = 0
    par_type: dict = field(default_factory=dict)
    par_moteur: dict = field(default_factory=dict)
    completude: dict = field(default_factory=dict)
    rejets: dict = field(default_factory=dict)
    incidents: dict = field(default_factory=dict)
    doublons: dict = field(default_factory=dict)
    a_verifier: int = 0
    top: list = field(default_factory=list)
    livre: object = None
    etats_sources: dict = field(default_factory=dict)   # nom -> état déclaré
    lots: dict = field(default_factory=dict)
    marge_non_mesuree: int = 0
    selections: list = field(default_factory=list)
    capter: list = field(default_factory=list)        # (score, type, action, source, titre)
    developper: list = field(default_factory=list)
    rendement: dict = field(default_factory=dict)     # source -> compteurs observés

    def _pct(self, n: int) -> str:
        return f"{n:>5}  ({n / self.total:.0%})" if self.total else f"{n:>5}"

    # ------------------------------------------------------- ce qu'on va faire --
    def _occasions(self) -> list:
        """Les occasions de chiffre d'affaires, avant toute statistique.

        On ouvre le radar pour voir ce qu'il y a à gagner, pas pour compter
        combien d'avis telle source a publiés. La source figure au bout de
        chaque ligne, comme une provenance — pas comme un classement.
        """
        L = ["RADAR COMMERCIAL", "=" * 72, ""]
        L.append("CAPTER — ce que je peux attaquer maintenant")
        if self.capter:
            for score, typ, action, source, titre in self.capter:
                emoji = EMOJIS.get(typ, "·")
                L.append(f"  {emoji} [{score:>3}] {titre[:46]:<46} {action[:22]:<24} "
                         f"vu sur {source}")
        else:
            L.append("  rien à attaquer dans cet échantillon — ce n'est pas une panne,")
            L.append("  c'est une mesure.")

        L += ["", "DÉVELOPPER — ce qui demande une relation ou de la préparation"]
        if self.developper:
            for score, typ, action, source, titre in self.developper:
                emoji = EMOJIS.get(typ, "·")
                L.append(f"  {emoji} [{score:>3}] {titre[:46]:<46} {action[:22]:<24} "
                         f"vu sur {source}")
        else:
            L.append("  aucune piste de développement dans cet échantillon")
        return L

    def en_texte(self, avec_fiches=True) -> str:
        L = [self.mode.bandeau(), ""] + self._occasions()
        L += ["", "=" * 72, "",
              f"MESURE — générée le {self.genere_le}", ""]

        L.append("COLLECTE")
        if self.sources:
            for nom, infos in sorted(self.sources.items()):
                quand = infos.get("derniere") or "date de collecte NON ENREGISTRÉE"
                L.append(f"  {nom:<16} CONSULTÉE  {infos['n']:>6} avis   "
                         f"dernière collecte {quand[:19]}")
        else:
            L.append("  aucune source — la base est vide")
        # Les sources déclarées mais absentes de la base ne sont pas passées
        # sous silence : elles apparaissent avec leur état réel.
        for nom, infos in sorted(self.etats_sources.items()):
            if nom in self.sources:
                continue
            etat = infos["etat"] if isinstance(infos, dict) else str(infos)
            motif = infos.get("motif") if isinstance(infos, dict) else None
            L.append(f"  {nom:<16} {etat:<17} {motif or 'aucun avis dans cette base'}")
        L.append(f"  total analysé    {self.total:>6}")

        if self.rendement:
            L += ["", "RENDEMENT OBSERVÉ PAR SOURCE",
                  "  Volume ≠ valeur. Une source qui publie beaucoup et ne produit rien",
                  "  d'exploitable descend ; une petite source qui produit descend moins.",
                  f"  {'source':<16}{'lues':>7}{'retenues':>10}{'CAPTER':>8}"
                  f"{'DÉVELOPPER':>12}   part utile"]
            for nom, r in sorted(self.rendement.items(),
                                 key=lambda x: -(x[1]["retenues"] / (x[1]["lues"] or 1))):
                part = (f"{r['retenues'] / r['lues']:.0%}" if r["lues"] else "NON MESURÉE")
                L.append(f"  {nom:<16}{r['lues']:>7}{r['retenues']:>10}"
                         f"{r['capter']:>8}{r['developper']:>12}   {part}")

        L += ["", "LOTS"]
        if self.lots:
            L.append(f"  opportunités issues d'un lot   {self.lots.get('lots', 0):>5}")
            L.append(f"  marchés parents concernés      {self.lots.get('marches', 0):>5}")
            L.append(f"  opportunités sans lot publié   {self.lots.get('sans_lot', 0):>5}")
        else:
            L.append("  NON MESURÉ")

        L += ["", "COMPLÉTUDE DES DONNÉES"]
        for libelle, n in self.completude.items():
            if n is None:
                L.append(f"  {libelle:<16} NON MESURÉ — champ absent du schéma")
            else:
                L.append(f"  {libelle:<16} {self._pct(n)}")

        L += ["", "CLASSIFICATION"]
        for emoji, cle in (("🟢", "DIRECT"), ("🟡", "RENFORCEMENT"), ("🟣", "A_CONSTRUIRE"),
                           ("🔵", "PROSPECT"), ("🔴", "REJET")):
            L.append(f"  {emoji} {cle:<14} {self._pct(self.par_type.get(cle, 0))}")
        L.append(f"  CAPTER           {self._pct(self.par_moteur.get('CAPTER', 0))}")
        L.append(f"  DÉVELOPPER       {self._pct(self.par_moteur.get('DEVELOPPER', 0))}")

        L += ["", "PRINCIPAUX MOTIFS DE REJET"]
        if self.rejets:
            for motif, n in sorted(self.rejets.items(), key=lambda x: -x[1])[:8]:
                L.append(f"  {n:>5}  {motif[:56]}")
        else:
            L.append("  aucun rejet")

        L += ["", "QUALITÉ"]
        for libelle, cle in (("doublons certains", "certains"),
                             ("doublons probables", "probables"),
                             ("doublons possibles", "possibles")):
            L.append(f"  {libelle:<20} {self.doublons.get(cle, 0):>5}")
        L.append(f"  {'points À VÉRIFIER':<20} {self.a_verifier:>5}")
        if self.incidents:
            for etape, n in sorted(self.incidents.items(), key=lambda x: -x[1]):
                L.append(f"  incident « {etape} » {n:>5}  — avis conservés, consultables")
        else:
            L.append(f"  {'incidents':<20} {0:>5}")

        L += ["", "ÉCONOMIE"]
        L.append(f"  {'MARGE NON MESURÉE':<20} {self.marge_non_mesuree:>5}"
                 f"   (coûts d'exploitation absents du profil)")
        L.append("  NON MESURÉE ne veut pas dire nulle : la donnée manque, "
                 "le calcul n'est pas fait.")

        if self.livre is not None:
            L += ["", self.livre.rapport()]

        for sel in self.selections:
            L += ["", "─" * 72, sel.titre, f"  {sel.explication}", ""]
            if not sel.lignes:
                L.append(f"  {sel.vide}")
                continue
            for score, titre, complement in sel.lignes:
                marque = f"[{score:>3}] " if score is not None else "      "
                L.append(f"  {marque}{titre[:52]:<52} {complement}")

        L += ["", "=" * 72, ""]
        if not self.top:
            L.append("AUCUNE OPPORTUNITÉ FORTE DÉTECTÉE DANS CET ÉCHANTILLON.")
            L.append("")
            L.append("Le radar ne force pas un classement : rien ici ne mérite ton temps")
            L.append("aujourd'hui. Ce n'est pas une panne, c'est une mesure.")
            return "\n".join(L)

        if avec_fiches:
            L.append(f"LES {len(self.top)} FICHES EN DÉTAIL")
            L += ["", "=" * 72, ""]
            for _, _, _, fiche in self.top:
                L.append(fiche)
                L.append("\n" + "─" * 72 + "\n")
        return "\n".join(L)


def _lignes(cx, sql, params=(), complement=lambda l: "") -> list:
    return [(l["score"], l["intitule"] or "(sans intitulé)", complement(l))
            for l in cx.execute(sql, params)]


def _euros(valeur) -> str:
    return f"{valeur:,.0f} €".replace(",", " ") if valeur is not None else "montant NON PUBLIÉ"


def _selections(cx, connues: set, cible: dict, proche_km: float, limite: int) -> list:
    """Les sélections que le premier rapport réel doit porter.

    Chacune est une QUESTION, pas un filtre décoratif. Quand la colonne
    nécessaire n'existe pas dans cette base, la sélection le dit au lieu
    d'afficher une liste vide qui se lirait « il n'y a rien ».
    """
    ouvertes = "type <> 'REJET' AND moteur = 'CAPTER'"
    sels = []

    # 1. Près du dépôt — moins de route, plus de marge.
    if "distance_km" not in connues:
        sels.append(Selection(
            "PRÈS DU DÉPÔT", "distance publiée au dépôt",
            "NON MESURÉ — la colonne distance_km est absente de cette base"))
    else:
        sels.append(Selection(
            "PRÈS DU DÉPÔT", f"à {proche_km:g} km ou moins du dépôt de Bruxelles",
            "aucune distance publiée ne descend sous ce seuil — "
            "la distance n'est presque jamais publiée, ce n'est pas une absence d'opportunités",
            _lignes(cx, f"SELECT score, intitule, distance_km d FROM opportunites"
                        f" WHERE {ouvertes} AND distance_km IS NOT NULL AND distance_km <= ?"
                        f" ORDER BY score DESC LIMIT ?", (proche_km, limite),
                    lambda l: f"{l['d']:g} km")))

    # 2. Le corridor : collecte à l'étranger, livraison belge.
    sels.append(Selection(
        "CORRIDOR ÉTRANGER → BE", "collecte hors Belgique, livraison belge — le modèle exact",
        "aucun corridor identifié dans cet échantillon",
        _lignes(cx, f"SELECT score, intitule, acheteur FROM opportunites"
                    f" WHERE {ouvertes} AND zone = 'corridor'"
                    f" ORDER BY score DESC LIMIT ?", (limite,),
                lambda l: (l["acheteur"] or "acheteur NON PUBLIÉ")[:24])))

    # 3. Ce qui tient dans la capacité actuelle.
    plafond = cible.get("montant_total_confortable_max")
    sels.append(Selection(
        "PETITS CONTRATS À MA TAILLE",
        f"exécutables sans renfort — montant publié sous {_euros(plafond)}",
        "aucun contrat de cette taille dans cet échantillon",
        _lignes(cx, f"SELECT score, intitule, montant m FROM opportunites"
                    f" WHERE {ouvertes} AND type IN ('DIRECT','A_CONSTRUIRE')"
                    f" AND montant IS NOT NULL AND montant <= ?"
                    f" ORDER BY score DESC LIMIT ?", (plafond or 0, limite),
                lambda l: _euros(l["m"]))))

    # 4. Ce qui vaut le coup MAIS demande de grandir. Ce bloc est la raison
    #    d'être de la règle « la taille actuelle est un point de départ » :
    #    ces lignes ne sont pas des rejets, ce sont des chantiers.
    sels.append(Selection(
        "TROP GROS SEUL — RENFORT OU PARTENARIAT",
        "à louer, recruter, sous-traiter ou grouper : jamais à jeter",
        "aucune opportunité ne demande de renfort dans cet échantillon",
        _lignes(cx, f"SELECT score, intitule, type t, montant m FROM opportunites"
                    f" WHERE {ouvertes} AND type IN ('RENFORCEMENT','PROSPECT')"
                    f" ORDER BY score DESC LIMIT ?", (limite,),
                lambda l: f"{l['t'][:12]:<12} {_euros(l['m'])}")))

    # 5. DÉVELOPPER : marchés déjà attribués. On ne postule pas, on appelle.
    sels.append(Selection(
        "À DÉVELOPPER — MARCHÉS DÉJÀ ATTRIBUÉS",
        "le titulaire devra exécuter : c'est un client de sous-traitance possible",
        "aucune attribution mémorisée dans cet échantillon",
        [(None, (l["intitule"] or "(sans intitulé)"),
          f"titulaire {(l['titulaire'] or 'NON PUBLIÉ')[:28]}  {_euros(l['montant'])}")
         for l in cx.execute(
             "SELECT o.intitule, a.titulaire, a.montant FROM attributions a"
             " JOIN opportunites o ON o.avis_id = a.avis_id"
             " ORDER BY a.montant IS NULL, a.montant DESC LIMIT ?", (limite,))]))
    return sels


def construire(cx, mode: Mode, limite_top=20, livre=None, etats_sources=None,
               cible=None, proche_km=50) -> Rapport:
    r = Rapport(mode=mode,
                genere_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                livre=livre, etats_sources=dict(etats_sources or {}))

    for l in cx.execute(
            "SELECT a.source AS s, count(*) n, max(a.derniere_vue) d"
            " FROM opportunites o JOIN avis a ON a.id = o.avis_id GROUP BY a.source"):
        r.sources[l["s"]] = {"n": l["n"], "derniere": l["d"]}
    r.total = sum(v["n"] for v in r.sources.values())

    for l in cx.execute("SELECT type, count(*) n FROM opportunites GROUP BY type"):
        r.par_type[l["type"]] = l["n"]
    for l in cx.execute("SELECT moteur, count(*) n FROM opportunites"
                        " WHERE type <> 'REJET' GROUP BY moteur"):
        r.par_moteur[l["moteur"] or "?"] = l["n"]
    for l in cx.execute("SELECT motif, count(*) n FROM opportunites"
                        " WHERE type = 'REJET' GROUP BY motif"):
        r.rejets[l["motif"] or "motif non enregistré"] = l["n"]
    for l in cx.execute("SELECT etape, count(*) n FROM incidents GROUP BY etape"):
        r.incidents[l["etape"]] = l["n"]

    # Tolérant : une colonne absente du schéma est signalée, pas fatale.
    connues = {l[1] for l in cx.execute("PRAGMA table_info(opportunites)")}
    for libelle, colonne in CHAMPS_COMPLETUDE:
        if colonne not in connues:
            r.completude[libelle] = None
            continue
        r.completude[libelle] = cx.execute(
            f"SELECT count(*) c FROM opportunites"
            f" WHERE {colonne} IS NOT NULL AND {colonne} <> ''").fetchone()["c"]

    r.lots = {
        "lots": cx.execute("SELECT count(*) c FROM opportunites"
                           " WHERE lot_numero IS NOT NULL AND lot_numero <> ''").fetchone()["c"],
        "marches": cx.execute("SELECT count(DISTINCT marche_ref) c FROM opportunites"
                              " WHERE marche_ref IS NOT NULL AND marche_ref <> ''").fetchone()["c"],
        "sans_lot": cx.execute("SELECT count(*) c FROM opportunites"
                               " WHERE lot_numero IS NULL OR lot_numero = ''").fetchone()["c"],
    }
    r.marge_non_mesuree = cx.execute(
        "SELECT count(*) c FROM opportunites WHERE marge = ? OR marge IS NULL",
        ("NON MESURÉE",)).fetchone()["c"]

    r.a_verifier = cx.execute(
        "SELECT count(*) c FROM opportunites WHERE fiche LIKE '%A_VERIFIER%'").fetchone()["c"]

    r.selections = _selections(cx, connues, cible or {}, proche_km, limite_top)

    # Les occasions, moteur par moteur. La source n'est qu'une étiquette de
    # provenance : elle ne trie rien, elle ne bonifie rien.
    for moteur, cible_liste in (("CAPTER", r.capter), ("DEVELOPPER", r.developper)):
        for l in cx.execute(
                "SELECT o.score, o.type, o.action, o.intitule, a.source"
                " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
                " WHERE o.type <> 'REJET' AND o.moteur = ?"
                " ORDER BY o.score DESC LIMIT ?", (moteur, limite_top)):
            cible_liste.append((l["score"], l["type"], l["action"] or "?",
                                l["source"], l["intitule"] or "(sans intitulé)"))

    # Rendement observé : ce que chaque source produit RÉELLEMENT. Jamais une
    # priorité déclarée d'avance, jamais un zéro pour une source non consultée.
    for l in cx.execute(
            "SELECT a.source s, count(*) lues,"
            " sum(o.type <> 'REJET') retenues,"
            " sum(o.type <> 'REJET' AND o.moteur = 'CAPTER') capter,"
            " sum(o.type <> 'REJET' AND o.moteur = 'DEVELOPPER') developper"
            " FROM opportunites o JOIN avis a ON a.id = o.avis_id GROUP BY a.source"):
        r.rendement[l["s"]] = {"lues": l["lues"], "retenues": l["retenues"] or 0,
                               "capter": l["capter"] or 0,
                               "developper": l["developper"] or 0}

    for l in cx.execute(
            "SELECT score, intitule, action, fiche FROM opportunites"
            " WHERE type <> 'REJET' AND moteur = 'CAPTER'"
            " ORDER BY score DESC LIMIT ?", (limite_top,)):
        r.top.append((l["score"], l["intitule"] or "(sans intitulé)",
                      l["action"] or "?", l["fiche"] or ""))
    return r
