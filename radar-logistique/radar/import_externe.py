"""UN EXPORT PRODUIT AILLEURS — jamais une recherche exécutée par le radar.

    MOTEUR EXTERNE ─► JSON / CSV ─► CE MODULE ─► TROUVAILLES
                                                     │
                                       et RIEN d'autre n'est créé

Il existe parce que l'environnement du radar n'atteint aucun moteur de
recherche. Un poste qui les atteint peut produire un fichier ; ce module le
fait entrer dans la chaîne, à la même place qu'un résultat que nous aurions
obtenu nous-mêmes, et sans jamais prétendre que nous l'avons obtenu.

CE N'EST PAS UN MOTEUR, ET IL NE PEUT PAS FAIRE SEMBLANT D'EN ÊTRE UN
=====================================================================

`ImportExterne` respecte le contrat `MoteurRecherche` pour se brancher aux
mêmes rails, mais :

    · `disponible` est FAUX — il ne peut exécuter aucune recherche ;
    · `rechercher()` LÈVE toujours. Il ne rend pas une liste vide, il refuse.

Une liste vide se confondrait avec « interrogé, rien trouvé ». Un refus, non.
C'est le même verrou structurel que la fixture qui refuse le mode RÉEL, posé
sur l'autre question : non pas « ces données sont-elles réelles ? » mais
« qui est allé les chercher ? ».

LE FICHIER EST UNE ENTRÉE NON FIABLE
====================================

Il n'a pas été produit par le radar. Il peut être tronqué, mal encodé,
réécrit à la main, ou porter des adresses qui n'en sont pas. Chaque ligne est
donc contrôlée, et une ligne refusée est COMPTÉE ET LISTÉE : rien ne disparaît
en silence.

Ce qui fait refuser une ligne, c'est toujours l'impossibilité de la lire comme
une observation — jamais son contenu commercial. Aucun mot-clé n'écarte quoi
que ce soit ici, et l'absence d'un mot n'a jamais rejeté personne.

CE QUE L'IMPORT NE CRÉE JAMAIS
==============================

Ni entreprise, ni entreprise confirmée, ni page surveillée, ni opportunité, ni
score. Il écrit des trouvailles et une ligne au journal des exécutions.

La suite de la chaîne — entreprise possible, page candidate, collecte,
qualification, surveillance — est exactement celle d'un résultat obtenu par le
radar, et elle passe par les mêmes modules. Un import ne saute aucun maillon :

    RÉSULTAT → PAGE → IDENTITÉ → CANDIDATE → QUALIFICATION → SURVEILLÉE
                                                           → OPPORTUNITÉ

AUCUN NOM DE FOURNISSEUR N'EST ÉCRIT ICI
========================================

Le nom du moteur vient du FICHIER, jamais du code. Ce module n'en connaît
aucun et n'en privilégie aucun.
"""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import execution as mod_execution, trouvailles as mod_trouvailles
from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE
from .deduplication import canoniser_url
from .mode import Mode
from .moteurs_recherche import MoteurRecherche, Resultat

# Le fichier doit déclarer d'où il vient, mot pour mot. Un fichier qui ne dit
# pas qu'il a été exécuté hors radar n'est pas chargé : on ne devine pas la
# provenance d'une donnée, pas plus qu'on ne devine sa nature.
PROVENANCE = mod_execution.HORS_RADAR

# Les seuls schémas qu'une adresse consultable peut porter.
SCHEMAS = ("http", "https")

# Bornes de lecture. Ce ne sont pas des jugements sur le contenu : ce sont les
# limites au-delà desquelles une ligne cesse d'être un résultat de moteur
# plausible et devient un fichier abîmé.
URL_MAX = 2048
TITRE_MAX = 500
EXTRAIT_MAX = 2000
REQUETE_MAX = 500
RANG_MAX = 1000

# Motifs de refus. Écrits en clair, comptés, et listés dans le bilan.
URL_ABSENTE = "URL ABSENTE"
URL_INVALIDE = "URL INVALIDE"
URL_TROP_LONGUE = "URL TROP LONGUE"
MOTEUR_ABSENT = "MOTEUR ABSENT"
MOTEUR_INVALIDE = "MOTEUR INVALIDE"
TITRE_HORS_LIMITE = "TITRE HORS LIMITE"
EXTRAIT_HORS_LIMITE = "EXTRAIT HORS LIMITE"
REQUETE_HORS_LIMITE = "REQUÊTE HORS LIMITE"
PROVENANCE_ABSENTE = "PROVENANCE NON DÉCLARÉE"
DOUBLON = "DOUBLON DANS LE FICHIER"

COLONNES = ("requete", "moteur", "date_execution", "url", "titre", "extrait",
            "rang")


class ImportInvalide(ValueError):
    """Le FICHIER entier est refusé : illisible, ou sans provenance déclarée.

    Distinct d'une ligne refusée. Une ligne mauvaise ne condamne pas le
    fichier ; un fichier qui ne dit pas d'où il vient, si.
    """


class RechercheNonExecutee(Exception):
    """Levée quand on demande à un import d'exécuter une recherche."""


@dataclass
class Refus:
    """Une ligne qu'on n'a pas pu lire, et pourquoi. Jamais silencieuse."""
    position: int
    motif: str
    url: str | None = None

    def ligne(self) -> str:
        return f"  ligne {self.position:>4}  {self.motif:<24} {(self.url or '—')[:44]}"


# ═══════════════════════════════════════════════════ nettoyage et contrôles
def _nettoyer(texte, limite):
    """Retire les caractères de contrôle et de formatage, garde les mots.

    Un caractère de contrôle ou une marque de direction n'est pas un mot : le
    retirer ne réécrit pas ce que le moteur a dit, cela retire ce qu'il
    n'aurait pas dû transmettre. Les retraits sont comptés.

    Rend (texte, retirés, hors_limite). Au-delà de la limite, on ne tronque
    PAS : tronquer réécrirait les mots du moteur, alors que le journal des
    trouvailles promet de les conserver mot pour mot. On refuse la ligne, et
    le refus est visible.
    """
    if texte is None:
        return None, 0, False
    brut = str(texte)
    sortie, retires = [], 0
    for ch in brut:
        if ch in ("\n", "\r", "\t"):
            sortie.append(" ")
            continue
        if unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cs"):
            retires += 1
            continue
        sortie.append(ch)
    propre = "".join(sortie).strip()
    return propre, retires, len(propre) > limite


def _url_lisible(url) -> str | None:
    """L'adresse si elle est consultable, sinon le motif de refus."""
    brut = str(url or "").strip()
    if not brut:
        return URL_ABSENTE
    if len(brut) > URL_MAX:
        return URL_TROP_LONGUE
    if any(c.isspace() or unicodedata.category(c) in ("Cc", "Cf") for c in brut):
        return URL_INVALIDE
    try:
        p = urlparse(brut)
    except ValueError:
        return URL_INVALIDE
    # Le schéma est contrôlé par liste blanche : tout ce qui n'est pas une
    # page consultable est refusé, y compris les schémas qui exécutent.
    if p.scheme.lower() not in SCHEMAS or not p.netloc:
        return URL_INVALIDE
    return None


def _rang_lisible(valeur):
    """Le rang s'il est lisible, sinon None — et la ligne est CONSERVÉE.

    Le rang ne note rien : il sert au diagnostic de capteur. Perdre une
    adresse parce que son numéro d'ordre est illisible serait disproportionné.
    Il reste donc inconnu, et il n'est jamais remplacé par une position
    devinée : inventer un rang fausserait les métriques de rappel.
    """
    if valeur is None or valeur == "":
        return None, False
    try:
        n = int(str(valeur).strip())
    except (TypeError, ValueError):
        return None, True
    if n < 1 or n > RANG_MAX:
        return None, True
    return n, False


def _date_lisible(valeur):
    """La date d'exécution déclarée si elle est lisible, sinon INCONNUE.

    Jamais la date du jour : le radar n'a pas exécuté cette recherche, il ne
    peut donc pas la dater. Écrire aujourd'hui serait inventer une mesure.
    """
    brut = str(valeur or "").strip()
    if not brut:
        return mod_execution.DATE_INCONNUE, True
    try:
        datetime.fromisoformat(brut.replace("Z", "+00:00"))
    except ValueError:
        return mod_execution.DATE_INCONNUE, True
    return brut, False


# ═══════════════════════════════════════════════════ le bilan
@dataclass
class Bilan:
    """Ce que l'import a réellement fait. Aucun de ces nombres n'est une
    opportunité, et aucun n'est une mesure du marché."""
    fichier: str | None = None
    empreinte: str | None = None
    lignes_lues: int = 0
    inscrites: int = 0
    refus: list = field(default_factory=list)
    doublons: int = 0
    rangs_inconnus: int = 0
    dates_inconnues: int = 0
    caracteres_retires: int = 0
    moteurs: list = field(default_factory=list)
    requetes: list = field(default_factory=list)

    @property
    def refusees(self) -> int:
        return len(self.refus)

    def resume(self) -> str:
        L = [f"IMPORT EXTERNE — {PROVENANCE}", "=" * 72, ""]
        L.append(f"  fichier              {self.fichier or '—'}")
        L.append(f"  empreinte            {(self.empreinte or '—')[:32]}")
        L.append(f"  lignes lues          {self.lignes_lues}")
        L.append(f"  inscrites            {self.inscrites}")
        L.append(f"  refusées             {self.refusees}")
        L.append(f"  doublons du fichier  {self.doublons}")
        L.append(f"  rangs illisibles     {self.rangs_inconnus}"
                 "   — conservés sans rang, jamais renumérotés")
        L.append(f"  dates illisibles     {self.dates_inconnues}"
                 f"   — écrites « {mod_execution.DATE_INCONNUE} »")
        L.append(f"  caractères retirés   {self.caracteres_retires}")
        if self.moteurs:
            L.append(f"  moteurs déclarés     {', '.join(self.moteurs)}")
        if self.refus:
            L.append("")
            L.append("LIGNES REFUSÉES — aucune ne disparaît en silence")
            for r in self.refus:
                L.append(r.ligne())
        L.append("")
        L.append("  Ces résultats n'ont PAS été obtenus par le radar : un moteur")
        L.append("  externe les a rendus, hors de cet environnement.")
        L.append("  Aucune entreprise n'a été confirmée, aucune page n'est")
        L.append("  surveillée, aucune opportunité n'a été créée, aucun score")
        L.append("  n'a bougé. Une adresse montrée n'est pas une page lue.")
        return "\n".join(L)


# ═══════════════════════════════════════════════════ l'adaptateur
@dataclass
class ImportExterne(MoteurRecherche):
    """Un export remis au radar. Respecte le contrat, n'exécute rien.

    Le mode est RÉEL parce que les résultats viennent d'un vrai moteur, sur le
    vrai web : les compter comme fabriqués masquerait de vraies observations
    dans le compartiment des fixtures, où l'on écrit « ne mesure aucun
    marché » — ce qui serait faux.

    Ce que le radar n'a pas fait n'est pas effacé pour autant : le nom de
    source est qualifié par la marque d'import, et le journal des exécutions
    porte « exécuté hors radar » en toutes lettres. La nature de l'exécution
    est écrite, pas déduite d'un mode à deux états qui ne peut pas la porter.
    """
    moteur_annonce: str = ""
    resultats_importes: list = field(default_factory=list)
    date_execution: str | None = None
    fichier: str | None = None
    empreinte: str | None = None
    bilan: Bilan | None = None
    # La requête annoncée par l'en-tête, quand le fichier n'a rendu AUCUN
    # résultat. Sans elle, un export vide serait indiscernable d'une recherche
    # jamais faite — alors qu'il dit « cette requête a été passée, rien n'est
    # revenu ». C'est 0, et 0 est une mesure.
    requete_annoncee: str | None = None

    @property
    def nom(self) -> str:
        return mod_execution.qualifier(self.moteur_annonce)

    @property
    def mode(self) -> Mode:
        return Mode.REEL

    @property
    def execution(self):
        return mod_execution.Execution.IMPORT_EXTERNE

    @property
    def disponible(self) -> bool:
        """Faux, et ce n'est pas une panne : ce n'est pas un moteur.

        `Registre.disponible()` cherche un moteur capable de chercher. Un
        import n'en est jamais un — le déclarer disponible mènerait un
        appelant à lui demander une recherche qu'il ne peut pas faire.
        """
        return False

    @property
    def motif_indisponibilite(self) -> str | None:
        return (f"{PROVENANCE} — ce n'est pas un moteur : aucune recherche ne "
                "peut être exécutée depuis le radar avec cet adaptateur")

    def rechercher(self, requete=None, mode=None):
        """Refuse toujours. Un import ne cherche pas : il restitue.

        Rendre une liste vide se confondrait avec « interrogé, rien trouvé ».
        Un refus ne se confond avec rien.
        """
        raise RechercheNonExecutee(
            f"« {self.moteur_annonce} » n'a pas été interrogé par le radar. "
            f"Ces résultats ont été {PROVENANCE} "
            f"({self.fichier or 'fichier non précisé'}) et ne peuvent pas être "
            "présentés comme une recherche exécutée ici.")

    def resultats(self, requete=None) -> list[Resultat]:
        """Ce que le fichier contient, tel quel. Ce n'est pas une recherche."""
        if requete is None:
            return list(self.resultats_importes)
        return [r for r in self.resultats_importes if r.requete == requete]

    @property
    def requetes(self) -> list[str]:
        vues = []
        for r in self.resultats_importes:
            if r.requete and r.requete not in vues:
                vues.append(r.requete)
        if not vues and self.requete_annoncee:
            return [self.requete_annoncee]
        return vues

    def etat(self) -> str:
        return (f"{self.nom:<20} {PROVENANCE} — "
                f"{len(self.resultats_importes)} résultat(s) remis, "
                "aucune recherche exécutée ici")


# ═══════════════════════════════════════════════════ lecture des fichiers
def _empreinte(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()[:32]


def _lignes_json(charge, chemin):
    """Un objet avec en-tête, ou une liste de lignes complètes."""
    if isinstance(charge, dict):
        entete = {c: charge.get(c) for c in ("provenance", "moteur",
                                             "date_execution", "requete")}
        lignes = charge.get("resultats")
        if lignes is None:
            raise ImportInvalide(f"{chemin} ne déclare aucun «·resultats·»")
        if not isinstance(lignes, list):
            raise ImportInvalide(f"{chemin} : «·resultats·» n'est pas une liste")
        return entete, [l if isinstance(l, dict) else {} for l in lignes]
    if isinstance(charge, list):
        return {}, [l if isinstance(l, dict) else {} for l in charge]
    raise ImportInvalide(f"{chemin} : contenu illisible comme import")


def _lignes_csv(texte, chemin):
    try:
        lecteur = csv.DictReader(texte.splitlines())
        lignes = [dict(l) for l in lecteur]
    except csv.Error as e:
        raise ImportInvalide(f"{chemin} illisible : {e}") from e
    return {}, lignes


def charger(chemin, *, provenance_attendue: str = PROVENANCE) -> list[ImportExterne]:
    """Lit un fichier d'export et rend UN adaptateur par moteur déclaré.

    Plusieurs, parce qu'un même export peut porter les résultats de plusieurs
    moteurs — et que mesurer leur recouvrement exige de ne pas les mélanger.

    Un fichier qui ne déclare pas sa provenance est REFUSÉ. C'est la même
    discipline que pour les fixtures : une donnée dont on ne sait pas d'où
    elle vient ne rentre pas, parce qu'on ne pourrait plus jamais dire au
    lecteur du rapport qui l'a produite.
    """
    p = Path(chemin)
    if not p.exists():
        raise ImportInvalide(f"import introuvable : {p}")
    octets = p.read_bytes()
    if not octets.strip():
        raise ImportInvalide(f"{p} est vide : aucune provenance déclarée")
    texte = octets.decode("utf-8", "replace")
    empreinte = _empreinte(octets)

    if p.suffix.lower() == ".csv":
        entete, lignes = _lignes_csv(texte, p)
    else:
        try:
            entete, lignes = _lignes_json(json.loads(texte), p)
        except json.JSONDecodeError as e:
            raise ImportInvalide(f"{p} illisible : {e}") from e

    return depuis_lignes(lignes, entete=entete, fichier=str(p),
                         empreinte=empreinte,
                         provenance_attendue=provenance_attendue)


def depuis_lignes(lignes, *, entete=None, fichier=None, empreinte=None,
                  provenance_attendue: str = PROVENANCE) -> list[ImportExterne]:
    """Contrôle chaque ligne et construit les adaptateurs.

    Séparée de `charger()` pour que les contrôles soient éprouvables sans
    fichier — et parce que la lecture d'un format et la validation d'une
    donnée sont deux responsabilités.
    """
    entete = entete or {}
    lignes = list(lignes or [])

    declaree = str(entete.get("provenance") or "").strip()
    if not declaree and lignes:
        # En CSV la provenance est portée par les lignes : on exige qu'elles
        # la portent TOUTES. Une seule ligne non déclarée suffirait sinon à
        # faire entrer une observation d'origine inconnue.
        valeurs = {str(l.get("provenance") or "").strip() for l in lignes}
        if len(valeurs) == 1:
            declaree = valeurs.pop()
    if declaree != provenance_attendue:
        raise ImportInvalide(
            f"{fichier or 'ce fichier'} ne déclare pas « {provenance_attendue} » "
            f"(lu : « {declaree or PROVENANCE_ABSENTE} »). On ne charge pas un "
            "fichier dont on ne sait pas qui a exécuté la recherche : le "
            "rapport devrait alors mentir sur sa provenance ou se taire.")

    bilan = Bilan(fichier=fichier, empreinte=empreinte)
    par_moteur: dict[str, ImportExterne] = {}
    vus: set = set()

    for position, brute in enumerate(lignes, start=1):
        bilan.lignes_lues += 1
        l = brute if isinstance(brute, dict) else {}

        moteur = str(l.get("moteur") or entete.get("moteur") or "").strip()
        if not moteur:
            bilan.refus.append(Refus(position, MOTEUR_ABSENT, l.get("url")))
            continue
        try:
            qualifie = mod_execution.qualifier(moteur)
        except mod_execution.NomDeSourceInvalide:
            bilan.refus.append(Refus(position, MOTEUR_INVALIDE, l.get("url")))
            continue

        motif = _url_lisible(l.get("url"))
        if motif:
            bilan.refus.append(Refus(position, motif, l.get("url")))
            continue
        url = str(l.get("url")).strip()

        titre, r1, trop_titre = _nettoyer(l.get("titre"), TITRE_MAX)
        if trop_titre:
            bilan.refus.append(Refus(position, TITRE_HORS_LIMITE, url))
            continue
        extrait, r2, trop_extrait = _nettoyer(l.get("extrait"), EXTRAIT_MAX)
        if trop_extrait:
            bilan.refus.append(Refus(position, EXTRAIT_HORS_LIMITE, url))
            continue
        requete, r3, trop_requete = _nettoyer(
            l.get("requete") or entete.get("requete"), REQUETE_MAX)
        if trop_requete:
            bilan.refus.append(Refus(position, REQUETE_HORS_LIMITE, url))
            continue
        bilan.caracteres_retires += r1 + r2 + r3

        rang, rang_illisible = _rang_lisible(l.get("rang"))
        if rang_illisible:
            bilan.rangs_inconnus += 1

        date, date_illisible = _date_lisible(
            l.get("date_execution") or entete.get("date_execution"))
        if date_illisible:
            bilan.dates_inconnues += 1

        # Le doublon se juge sur l'URL CANONIQUE, avec la canonisation déjà en
        # vigueur ailleurs : en écrire une seconde ferait diverger deux
        # définitions du même fait. La PREMIÈRE occurrence est conservée, avec
        # son rang ; les suivantes sont comptées, jamais réécrites par-dessus.
        cle = (qualifie, requete, canoniser_url(url) or url)
        if cle in vus:
            bilan.doublons += 1
            continue
        vus.add(cle)

        adaptateur = par_moteur.get(qualifie)
        if adaptateur is None:
            adaptateur = par_moteur[qualifie] = ImportExterne(
                moteur_annonce=moteur, date_execution=date, fichier=fichier,
                empreinte=empreinte, bilan=bilan)
        adaptateur.resultats_importes.append(Resultat(
            titre=titre or "", url=url, extrait=extrait or "",
            requete=requete or "", fournisseur=qualifie, consulte_le=date,
            rang=rang))
        bilan.inscrites += 1
        if requete and requete not in bilan.requetes:
            bilan.requetes.append(requete)

    # Un export SANS AUCUN résultat, mais qui déclare son moteur : la recherche
    # a eu lieu et n'a rien rendu. On construit quand même l'adaptateur, pour
    # que le zéro s'inscrive. Sans moteur déclaré, en revanche, on ne saurait
    # attribuer ce zéro à personne — et il resterait NON MESURÉ.
    if not par_moteur and not lignes:
        moteur = str(entete.get("moteur") or "").strip()
        if moteur:
            requete = _nettoyer(entete.get("requete"), REQUETE_MAX)[0]
            par_moteur[mod_execution.qualifier(moteur)] = ImportExterne(
                moteur_annonce=moteur,
                date_execution=_date_lisible(entete.get("date_execution"))[0],
                fichier=fichier, empreinte=empreinte,
                requete_annoncee=requete or None)

    bilan.moteurs = sorted(a.moteur_annonce for a in par_moteur.values())
    for a in par_moteur.values():
        a.bilan = bilan
    return list(par_moteur.values())


# ═══════════════════════════════════════════════════ entrée dans la chaîne
def inscrire(cx, adaptateurs, *, circuit=None) -> Bilan:
    """Inscrit les résultats importés au journal des trouvailles.

    Le mode est lu sur L'ADAPTATEUR, jamais choisi par l'appelant — même
    garantie que `trouvailles.depuis_moteur()`. Le nom de source aussi : un
    appelant ne peut pas faire passer un import pour une recherche du radar.

    Résultat par résultat, et non par lot : l'inscription par lot renumérote
    les rangs manquants d'après la position dans la liste. Pour un import,
    cela fabriquerait un rang que le moteur n'a jamais rendu — un rang
    illisible doit rester inconnu.

    N'appelle aucun chaînage. Un import n'est pas une entreprise, pas une page
    surveillée, pas une opportunité : la suite passe par `chainage`, comme
    pour n'importe quel résultat.
    """
    adaptateurs = ([adaptateurs] if isinstance(adaptateurs, ImportExterne)
                   else list(adaptateurs or []))
    bilan = None
    # Une ligne refusée appartient au FICHIER, pas à une requête : souvent on
    # n'a pas pu lire de quelle requête elle relevait. Elle est donc portée par
    # UNE SEULE ligne d'exécution — la répéter sur chacune multiplierait le
    # compte des refus par le nombre de requêtes du fichier.
    refus_portes: set = set()
    for a in adaptateurs:
        bilan = a.bilan or bilan
        for r in a.resultats_importes:
            mod_trouvailles.inscrire(cx, r, mode=a.mode, source=a.nom,
                                     circuit=circuit or CIRCUIT_DECOUVERTE)
        # Une ligne d'exécution PAR REQUÊTE : c'est la requête qui a été
        # passée, pas le fichier. Une requête sans résultat reste inscrite —
        # c'est un zéro mesuré, et il ne doit pas se confondre avec l'absence
        # de mesure.
        for requete in (a.requetes or [None]):
            marque = (a.fichier, a.empreinte, id(a.bilan))
            refuses = 0
            if a.bilan is not None and marque not in refus_portes:
                refuses = a.bilan.refusees
                refus_portes.add(marque)
            mod_execution.journaliser(
                cx, moteur_declare=a.moteur_annonce, source=a.nom,
                requete=requete, execution_par=PROVENANCE,
                date_execution=a.date_execution, fichier=a.fichier,
                empreinte=a.empreinte,
                resultats=len(a.resultats(requete) if requete else
                              a.resultats_importes),
                refuses=refuses)
    return bilan or Bilan()


def importer(cx, chemin, *, circuit=None) -> Bilan:
    """Charger puis inscrire. Ne chaîne rien, ne qualifie rien, ne note rien."""
    adaptateurs = charger(chemin)
    bilan = inscrire(cx, adaptateurs, circuit=circuit)
    bilan.moteurs = sorted({a.moteur_annonce for a in adaptateurs})
    return bilan


def declarer_muette(cx, *, moteur: str, requete: str, date_execution=None,
                    fichier=None, empreinte=None):
    """Déclare qu'une requête a été passée HORS RADAR et n'a RIEN rendu.

    Zéro résultat est une mesure : le moteur a répondu. Sans cette inscription,
    une requête muette serait indiscernable d'une requête jamais passée — et
    l'on écrirait NON MESURÉ là où il faut écrire 0.
    """
    return mod_execution.journaliser(
        cx, moteur_declare=moteur, source=mod_execution.qualifier(moteur),
        requete=requete, execution_par=PROVENANCE,
        date_execution=_date_lisible(date_execution)[0],
        fichier=fichier, empreinte=empreinte, resultats=0, refuses=0)
