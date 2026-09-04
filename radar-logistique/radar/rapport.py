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

# LES HUIT BLOCS DU PIPELINE COMMERCIAL, dans l'ordre où on agit.
BLOCS_PIPELINE = [
    ("🔥 À ATTAQUER MAINTENANT", "attaquer"),
    ("📞 À CONTACTER", "contacter"),
    ("🤝 SOUS-TRAITANCE / PARTENARIAT", "partenariat"),
    ("👀 À SURVEILLER", "surveiller"),
    ("🔄 RENOUVELLEMENTS / ATTRIBUTIONS", "renouvellement"),
    ("🎓 NOUVEAUX MÉTIERS ACCESSIBLES", "metier"),
    ("⚠️ À VÉRIFIER", "verifier"),
    # Lues, comprises, et sans matière commerciale à cette date. Ni un rejet
    # (rien ne dit que l'entreprise n'aura jamais de besoin), ni une file
    # d'attente (il n'y a rien à surveiller). Ce bloc existe parce qu'une
    # vraie page mesurée y est tombée : sans lui, elle encombrait « à
    # surveiller » avec un score de 24/100.
    ("⚪ PAS ENCORE DES OPPORTUNITÉS", "observation"),
    ("❌ REJETS MOTIVÉS", "rejet"),
]


def bloc_de(ligne) -> str:
    """Dans quel bloc du pipeline cette opportunité tombe.

    Lu sur ce qu'il y a À FAIRE, jamais sur la provenance : un besoin privé
    exploitable et un marché public ouvert sont tous deux « à attaquer ».
    """
    if ligne["type"] == "REJET":
        return "rejet"
    if ligne["type"] == "PAS ENCORE UNE OPPORTUNITÉ":
        return "observation"
    action = (ligne["action"] or "").upper()
    if ligne["type"] == "A_CONSTRUIRE":
        return "metier"
    if "VÉRIFIER" in action:
        return "verifier"
    if ligne["etat_procedure"] in ("ATTRIBUÉ", "ANNONCÉ"):
        return "renouvellement"
    if action.startswith("PROPOSER"):
        return "partenariat"
    if action == "POSTULER":
        return "attaquer"
    if "CONTACTER" in action:
        # Un besoin ÉNONCÉ s'attaque ; un signal se qualifie d'abord.
        return "contacter" if ligne["nature"] == "FAIT" else "surveiller"
    return "surveiller"

# Les familles de besoin, dans l'ordre où elles se lisent. Le classement se fait
# sur des FAITS portés par l'opportunité — jamais sur le nom de la source :
# un besoin privé peut arriver par un moteur de recherche, une page ou une
# bourse de fret, et un besoin public par trois portails différents.
FAMILLES_ORDRE = [
    ("BESOINS PRIVÉS", None), ("MARCHÉS PUBLICS", None),
    ("SOUS-TRAITANCE ET PARTENARIAT", None), ("ENTREPRISES À DÉMARCHER", None),
    ("SIGNAUX ÉCONOMIQUES", None), ("RENOUVELLEMENTS À ANTICIPER", None),
    ("MÉTIERS À CONSTRUIRE", None),
]


def famille_de(ligne) -> str:
    """À quelle famille de besoin cette opportunité appartient.

    Lu sur ce que l'opportunité EST, pas sur d'où elle vient.
    """
    if ligne["type"] == "A_CONSTRUIRE":
        return "MÉTIERS À CONSTRUIRE"
    if ligne["etat_procedure"] == "ATTRIBUÉ" or ligne["etat_procedure"] == "ANNONCÉ":
        return "RENOUVELLEMENTS À ANTICIPER"
    # Hors procédure et sans échéance : c'est la NATURE qui départage.
    #   « nous recherchons un transporteur »  → besoin EXPRIMÉ (FAIT)
    #   « distributeur, trois sites »         → besoin DÉDUIT (hypothèse)
    # Trancher sur la seule absence d'échéance rangeait le premier parmi les
    # entreprises à démarcher : on aurait prospecté quelqu'un qui a déjà écrit
    # ce qu'il cherche.
    if ligne["etat_procedure"] == "HORS PROCÉDURE" and not ligne["echeance"]:
        if ligne["nature"] == "FAIT":
            return "BESOINS PRIVÉS"
        if ligne["nature"] == "HYPOTHÈSE":
            return "ENTREPRISES À DÉMARCHER"
    if ligne["nature"] in ("SIGNAL", "HYPOTHÈSE"):
        return "SIGNAUX ÉCONOMIQUES"
    if (ligne["action"] or "").startswith("PROPOSER"):
        return "SOUS-TRAITANCE ET PARTENARIAT"
    if (ligne["secteur"] or "").lower().startswith("pub"):
        return "MARCHÉS PUBLICS"
    return "BESOINS PRIVÉS"

# LA COMPLÉTUDE DÉPEND DU TYPE DE BESOIN, PAS D'UNE GRILLE UNIQUE.
#
# Une seule liste de champs — acheteur, échéance, montant, durée, lots… — est
# la fiche signalétique d'un avis de marché public. L'appliquer à tout mesurait
# un signal de recrutement à l'aune de champs qui n'existent pas chez lui :
# « lots 0 % », « échéance 14 % ». Un besoin privé paraissait incomplet alors
# qu'il était complet POUR CE QU'IL EST.
#
# Chaque famille déclare donc ce qui compte chez elle. Un champ absent de sa
# grille n'est pas un trou : il est hors sujet.
CHAMPS_PAR_FAMILLE = {
    "MARCHÉS PUBLICS": (
        ("acheteur", "acheteur"), ("échéance", "echeance"), ("montant", "montant"),
        ("durée", "duree_mois"), ("lots", "lot_numero"), ("zone", "zone"),
        ("exigences", "exigences"), ("état", "etat_procedure")),
    "BESOINS PRIVÉS": (
        ("entreprise", "acheteur"), ("besoin", "intitule"), ("zone", "zone"),
        ("volume/montant", "montant"), ("cadence", "cadence"),
        ("contact", "contact")),
    "SOUS-TRAITANCE ET PARTENARIAT": (
        ("entreprise", "acheteur"), ("besoin", "intitule"), ("zone", "zone"),
        ("cadence", "cadence"), ("contact", "contact")),
    "ENTREPRISES À DÉMARCHER": (
        ("entreprise", "acheteur"), ("zone", "zone"), ("contact", "contact"),
        ("indice de besoin", "intitule")),
    "SIGNAUX ÉCONOMIQUES": (
        ("entreprise", "acheteur"), ("nature du signal", "nature"),
        ("zone", "zone"), ("date de détection", "calcule_le")),
    "RENOUVELLEMENTS À ANTICIPER": (
        ("acheteur", "acheteur"), ("titulaire", "intitule"), ("montant", "montant"),
        ("durée", "duree_mois"), ("zone", "zone"), ("état", "etat_procedure")),
    "MÉTIERS À CONSTRUIRE": (
        ("entreprise", "acheteur"), ("besoin", "intitule"), ("zone", "zone"),
        ("durée", "duree_mois"), ("cadence", "cadence")),
}

# Grille de repli quand la famille n'est pas connue : le strict minimum qu'un
# besoin commercial doit porter, quelle que soit sa forme.
CHAMPS_COMPLETUDE = (
    ("demandeur", "acheteur"), ("besoin", "intitule"), ("zone", "zone"),
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
    etats: dict = field(default_factory=dict)         # état de procédure -> nombre
    fiabilites: dict = field(default_factory=dict)    # niveau -> nombre
    croisement: list = field(default_factory=list)    # (fiabilité, score, titre, action)
    transitions: list = field(default_factory=list)
    signaux: list = field(default_factory=list)       # événements pouvant générer du CA
    a_verifier_liste: list = field(default_factory=list)   # informations ambiguës
    actions: dict = field(default_factory=dict)       # action -> [(score, titre, source)]
    familles: dict = field(default_factory=dict)      # famille de besoin -> lignes
    pipeline: dict = field(default_factory=dict)     # bloc commercial -> lignes
    completude_par_famille: dict = field(default_factory=dict)
    familles_effectif: dict = field(default_factory=dict)

    def _pct(self, n: int) -> str:
        return f"{n:>5}  ({n / self.total:.0%})" if self.total else f"{n:>5}"

    # ------------------------------------------------------- ce qu'on va faire --
    def _pipeline(self) -> list:
        """LE PIPELINE COMMERCIAL — huit blocs, dans l'ordre où on agit.

        Le rapport ne commence pas par « TED : 132 avis ». Il commence par ce
        qu'il y a à gagner. La source arrive tout au bout de chaque ligne,
        comme une provenance, et le détail par source vient à la fin.
        """
        L = ["RADAR COMMERCIAL", "=" * 72,
             "Opportunités de chiffre d'affaires provenant de DIFFÉRENTES FAMILLES",
             "DE SOURCES PRÉVUES PAR L'ARCHITECTURE — qualifiées économiquement,",
             "faits, signaux et hypothèses distingués.",
             ""]
        for titre, cle in BLOCS_PIPELINE:
            lignes = self.pipeline.get(cle, [])
            L.append(f"{titre}   ({len(lignes)})")
            if not lignes:
                L.append("    — rien dans cet échantillon")
                continue
            for score, intitule, action, source, etat, nature in lignes[:6]:
                L.append(f"    [{score:>3}] {intitule[:44]:<46}"
                         f"{(action or '')[:22]:<24}{(nature or '')[:9]:<10}"
                         f"vu sur {source}")
            if len(lignes) > 6:
                L.append(f"    … et {len(lignes) - 6} autre(s)")
        L.append("")
        # Deux compteurs, jamais mélangés — et jamais dans la même phrase que
        # le nombre d'opportunités trouvées, pour qu'aucun des deux ne se lise
        # comme une validation de l'autre.
        try:
            from .validation import etat as _etat
            e = _etat()
            L.append(f"  TESTS DE COHÉRENCE : {e.tests_coherence} (données fabriquées)"
                     f"  ·  DONNÉES RÉELLES OBSERVÉES : {len(e.mesures)}"
                     f"  ·  PAGES RÉELLES PORTANT UN BESOIN : "
                     f"{e.pages_portant_un_besoin}")
            L.append("  Le premier compteur ne valide rien commercialement.")
            L.append("")
        except Exception:            # noqa: BLE001 — un rapport ne meurt pas là-dessus
            pass
        L.append("  DÉTECTER → QUALIFIER → CONTACTER → CONVERTIR → EXÉCUTER")
        L.append("  → RENOUVELER → DÉVELOPPER.  Un marché ouvert n'est qu'UN cas")
        L.append("  du premier stade.")
        return L

    def _occasions(self) -> list:
        """Les occasions de chiffre d'affaires, avant toute statistique.

        On ouvre le radar pour voir ce qu'il y a à gagner, pas pour compter
        combien d'avis telle source a publiés. La source figure au bout de
        chaque ligne, comme une provenance — pas comme un classement.
        """
        L = ["DEUX MOTEURS", "=" * 72, ""]
        L.append("CAPTER — ce que je peux attaquer maintenant")
        if self.capter:
            for score, typ, action, source, titre, etat in self.capter:
                emoji = EMOJIS.get(typ, "·")
                L.append(f"  {emoji} [{score:>3}] {titre[:42]:<42} {(etat or '?')[:11]:<12}"
                         f"{action[:22]:<24} vu sur {source}")
        else:
            L.append("  rien à attaquer dans cet échantillon — ce n'est pas une panne,")
            L.append("  c'est une mesure.")

        L += ["", "DÉVELOPPER — ce qui demande une relation ou de la préparation"]
        if self.developper:
            for score, typ, action, source, titre, etat in self.developper:
                emoji = EMOJIS.get(typ, "·")
                L.append(f"  {emoji} [{score:>3}] {titre[:42]:<42} {(etat or '?')[:11]:<12}"
                         f"{action[:22]:<24} vu sur {source}")
        else:
            L.append("  aucune piste de développement dans cet échantillon")

        L += ["", "SIGNAUX — des événements, pas encore des contrats"]
        if self.signaux:
            for score, titre, source, nature in self.signaux:
                L.append(f"  ◈ [{score:>3}] {titre[:50]:<50} {nature[:10]:<11} "
                         f"vu sur {source}")
            L.append("  Un signal n'est pas une commande : il dit qu'un besoin est")
            L.append("  probable. Une hypothèse l'est encore moins. Ni l'un ni")
            L.append("  l'autre n'est présenté comme un fait.")
        else:
            L.append("  aucun signal dans cet échantillon")

        L += ["", "À VÉRIFIER — informations ambiguës, ni jetées ni promues"]
        if self.a_verifier_liste:
            for score, titre, source, motif in self.a_verifier_liste:
                L.append(f"  ? [{score:>3}] {titre[:46]:<46} vu sur {source}")
                L.append(f"        {motif[:66]}")
        else:
            L.append("  rien d'ambigu dans cet échantillon")

        L += ["", "PAR FAMILLE DE BESOIN"]
        if self.familles:
            for titre, _ in FAMILLES_ORDRE:
                trouvees = self.familles.get(titre, [])
                L.append(f"  {titre:<32} {len(trouvees):>3}")
                for score, intitule, source in trouvees[:3]:
                    L.append(f"      [{score:>3}] {intitule[:48]:<48} {source}")
            L.append("  Un appel d'offres est UNE famille parmi douze. Aucune n'a")
            L.append("  de privilège : c'est l'économie qui classe.")
        else:
            L.append("  NON MESURÉ")

        L += ["", "TOP ACTIONS — ce que je fais demain matin"]
        if self.actions:
            for action, lignes in sorted(self.actions.items(),
                                         key=lambda x: -max(l[0] for l in x[1])):
                L.append(f"  {action}  ({len(lignes)})")
                for score, titre, source in lignes[:3]:
                    L.append(f"      [{score:>3}] {titre[:52]:<52} {source}")
        else:
            L.append("  rien à faire sur cet échantillon")
        return L

    def en_texte(self, avec_fiches=True) -> str:
        L = [self.mode.bandeau(), ""] + self._pipeline() + ["", "=" * 72, ""]
        L += self._occasions()
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

        L += ["", "ÉTAT DES PROCÉDURES"]
        if self.etats:
            for etat, n in sorted(self.etats.items(), key=lambda x: -x[1]):
                L.append(f"  {etat or 'NON LU':<14} {n:>5}")
            L.append("  Aucun de ces états n'est un rejet : fermé, annulé ou "
                     "infructueux restent")
            L.append("  des pistes. Seule l'ACTION change.")
        else:
            L.append("  NON MESURÉ")

        if self.transitions:
            L += ["", "CHANGEMENTS D'ÉTAT — les événements commerciaux du cycle"]
            for l in self.transitions:
                marque = "⚡" if l["origine"] == "collecte" else "✎"
                L.append(f"  {marque} {l['constate_le'][:10]} "
                         f"{(l['ancien_etat'] or 'découverte'):<12} → "
                         f"{l['nouvel_etat']:<12} {(l['intitule'] or '')[:40]}")
            L.append("  ⚡ la source a changé   ·   ✎ nous avons corrigé notre lecture")

        L += ["", "LOTS"]
        if self.lots:
            L.append(f"  opportunités issues d'un lot   {self.lots.get('lots', 0):>5}")
            L.append(f"  marchés parents concernés      {self.lots.get('marches', 0):>5}")
            L.append(f"  opportunités sans lot publié   {self.lots.get('sans_lot', 0):>5}")
        else:
            L.append("  NON MESURÉ")

        L += ["", "COMPLÉTUDE — mesurée avec la grille de CHAQUE famille"]
        if self.completude_par_famille:
            for famille, champs in self.completude_par_famille.items():
                total = self.familles_effectif.get(famille, 0)
                if not total:
                    continue
                L.append(f"  {famille}  ({total})")
                for libelle, n in champs.items():
                    if n is None:
                        L.append(f"      {libelle:<18} NON MESURÉ — hors schéma")
                    else:
                        L.append(f"      {libelle:<18} {n:>3}/{total}"
                                 f"   {n / total:.0%}")
            L.append("  Un champ absent d'une grille n'est pas un trou : il est")
            L.append("  hors sujet. On ne mesure pas un signal avec les champs")
            L.append("  d'un avis de marché.")
        else:
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

        L += ["", "FIABILITÉ DE L'INFORMATION ≠ VALEUR ÉCONOMIQUE"]
        for niveau in ("FORTE", "MOYENNE", "FAIBLE", "NULLE"):
            L.append(f"  {niveau:<10} {self.fiabilites.get(niveau, 0):>5}")
        L.append("  Une information peu fiable peut être excellente commercialement.")
        L.append("  Elle remonte donc HAUT, avec « ACTION : VÉRIFIER » — jamais")
        L.append("  dévalorisée dans le score.")
        if self.croisement:
            L.append("")
            L.append(f"  {'score':>6}  {'fiabilité':<10} {'action':<26} intitulé")
            for fiab, score, titre, action in self.croisement:
                L.append(f"  {score:>6}  {(fiab or '—'):<10} {(action or '?')[:24]:<26} "
                         f"{titre[:34]}")

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

    if "etat_procedure" in connues:
        for l in cx.execute("SELECT etat_procedure e, count(*) n FROM opportunites"
                            " WHERE type <> 'REJET' GROUP BY etat_procedure"):
            r.etats[l["e"] or "NON LU"] = l["n"]
    if "fiabilite" in connues:
        for l in cx.execute("SELECT fiabilite f, count(*) n FROM opportunites"
                            " WHERE type <> 'REJET' GROUP BY fiabilite"):
            r.fiabilites[l["f"] or "NON MESURÉE"] = l["n"]
        # Le croisement qui prouve la séparation : les meilleurs scores, avec
        # leur fiabilité à côté. Une ligne FAIBLE tout en haut est normale.
        for l in cx.execute(
                "SELECT fiabilite, score, intitule, action FROM opportunites"
                " WHERE type <> 'REJET' ORDER BY score DESC LIMIT 8"):
            r.croisement.append((l["fiabilite"], l["score"],
                                 l["intitule"] or "(sans intitulé)", l["action"]))
    try:
        r.transitions = cx.execute(
            "SELECT h.ancien_etat, h.nouvel_etat, h.origine, h.constate_le, o.intitule"
            " FROM etats_historique h LEFT JOIN opportunites o ON o.avis_id = h.avis_id"
            " WHERE h.ancien_etat IS NOT NULL ORDER BY h.id DESC LIMIT 15").fetchall()
    except Exception:                      # base d'une version antérieure
        r.transitions = []

    r.selections = _selections(cx, connues, cible or {}, proche_km, limite_top)

    # Les occasions, moteur par moteur. La source n'est qu'une étiquette de
    # provenance : elle ne trie rien, elle ne bonifie rien.
    for moteur, cible_liste in (("CAPTER", r.capter), ("DEVELOPPER", r.developper)):
        for l in cx.execute(
                "SELECT o.score, o.type, o.action, o.intitule, o.etat_procedure, a.source"
                " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
                " WHERE o.type <> 'REJET' AND o.moteur = ?"
                " ORDER BY o.score DESC LIMIT ?", (moteur, limite_top)):
            cible_liste.append((l["score"], l["type"], l["action"] or "?",
                                l["source"], l["intitule"] or "(sans intitulé)",
                                l["etat_procedure"]))

    # SIGNAUX = dimension C (nature), surtout PAS dimension B (état).
    #
    # « Devenir partenaire transporteur » est HORS PROCÉDURE sur B et pourtant
    # un FAIT sur C : l'entreprise dit elle-même ce qu'elle cherche. Le ranger
    # parmi les signaux reviendrait à présenter un fait comme une inférence —
    # exactement la confusion que les quatre dimensions existent pour empêcher.
    if "nature" in connues:
        for l in cx.execute(
                "SELECT o.score, o.intitule, a.source, o.nature FROM opportunites o"
                " JOIN avis a ON a.id = o.avis_id"
                " WHERE o.type <> 'REJET' AND o.nature IN ('SIGNAL', 'HYPOTHÈSE')"
                " ORDER BY o.score DESC LIMIT ?", (limite_top,)):
            r.signaux.append((l["score"], l["intitule"] or "(sans intitulé)",
                              l["source"], l["nature"]))
    if "etat_procedure" in connues:
        for l in cx.execute(
                "SELECT o.score, o.intitule, o.motif, a.source FROM opportunites o"
                " JOIN avis a ON a.id = o.avis_id"
                " WHERE o.type <> 'REJET' AND o.etat_procedure = 'INCONNU'"
                " ORDER BY o.score DESC LIMIT ?", (limite_top,)):
            r.a_verifier_liste.append((l["score"], l["intitule"] or "(sans intitulé)",
                                       l["source"], l["motif"] or "état non démontré"))

    if "nature" in connues:
        par_famille: dict = {}
        for l in cx.execute(
                "SELECT o.avis_id, o.score, o.intitule, o.type, o.action, o.nature,"
                " o.etat_procedure, o.echeance, o.secteur, a.source"
                " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
                " WHERE o.type <> 'REJET' ORDER BY o.score DESC"):
            famille = famille_de(l)
            r.familles.setdefault(famille, []).append(
                (l["score"], l["intitule"] or "(sans intitulé)", l["source"]))
            par_famille.setdefault(famille, []).append(l["avis_id"])

        # Chaque famille est mesurée avec SA grille. Compter les champs d'un
        # avis public sur un signal de recrutement produisait « lots 0 % » —
        # un trou qui n'en est pas un.
        for famille, ids in par_famille.items():
            r.familles_effectif[famille] = len(ids)
            grille = CHAMPS_PAR_FAMILLE.get(famille, CHAMPS_COMPLETUDE)
            mesures: dict = {}
            marques = ",".join("?" * len(ids))
            for libelle, colonne in grille:
                if colonne not in connues:
                    mesures[libelle] = None
                    continue
                mesures[libelle] = cx.execute(
                    f"SELECT count(*) c FROM opportunites"
                    f" WHERE avis_id IN ({marques})"
                    f" AND {colonne} IS NOT NULL AND {colonne} <> ''",
                    ids).fetchone()["c"]
            r.completude_par_famille[famille] = mesures

    if "nature" in connues:
        mesurable = ("o.score_mesurable" if "score_mesurable" in connues
                     else "1 AS score_mesurable")
        for l in cx.execute(
                f"SELECT o.score, {mesurable}, o.intitule, o.type, o.action, o.nature,"
                " o.etat_procedure, o.motif, a.source FROM opportunites o"
                " JOIN avis a ON a.id = o.avis_id ORDER BY o.score DESC"):
            # « — » et non « 24 » : un nombre affiché prétend être une mesure.
            note = l["score"] if l["score_mesurable"] else "—"
            r.pipeline.setdefault(bloc_de(l), []).append(
                (note, l["intitule"] or "(sans intitulé)",
                 l["action"] if l["type"] != "REJET" else (l["motif"] or "")[:22],
                 l["source"], l["etat_procedure"], l["nature"]))

    # Ce qu'il y a à FAIRE, regroupé par geste. C'est la sortie du produit.
    for l in cx.execute(
            "SELECT o.score, o.intitule, o.action, a.source FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id WHERE o.type <> 'REJET'"
            " ORDER BY o.score DESC"):
        r.actions.setdefault(l["action"] or "?", []).append(
            (l["score"], l["intitule"] or "(sans intitulé)", l["source"]))

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
