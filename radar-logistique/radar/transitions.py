"""LES CHANGEMENTS D'ÉTAT SONT DES ÉVÉNEMENTS COMMERCIAUX.

Une opportunité a UN fil de vie, pas trois existences :

    03/09 POSTULABLE  ·  14/09 FERMÉ  ·  28/09 ATTRIBUÉ
    → 1 opportunité, 3 observations, 2 transitions

Et chaque transition vaut une action. « Le marché est maintenant ouvert » est
l'information la plus précieuse que ce radar puisse produire : elle arrive
avant que tout le monde ne l'ait vue.

────────────────────────────────────────────────────────────────────────────
DEUX CHOSES QU'ON NE CONFOND JAMAIS
────────────────────────────────────────────────────────────────────────────

    LA SOURCE A CHANGÉ            le portail dit autre chose qu'hier
    NOUS AVONS CHANGÉ NOTRE       nous avons tranché un mot que nous lisions
    INTERPRÉTATION                mal — le marché, lui, n'a pas bougé

Les confondre ferait sonner une alerte « nouvelle chance de postuler » alors
que rien ne s'est produit. Seule une transition d'origine `collecte` peut
déclencher une alerte commerciale.

────────────────────────────────────────────────────────────────────────────
CE QUI N'ÉMET JAMAIS D'ALERTE
────────────────────────────────────────────────────────────────────────────
  · une collecte qui ne change rien (sinon : un événement par passage) ;
  · une transition vers INCONNU (on a perdu la certitude, pas gagné une
    occasion) ;
  · une transition dont la confiance est FAIBLE ou NULLE — on ne réveille
    personne pour une hypothèse ;
  · une correction de vocabulaire.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import maintenant
from .procedure import Confiance, Etat

COLLECTE = "collecte"
REVISION = "revision_vocabulaire"


@dataclass
class Effet:
    """Ce qu'une transition provoque, en clair."""
    intensite: str            # forte | normale | silencieuse
    message: str
    annule_postuler: bool = False
    recuperer_titulaire: bool = False


# Les règles, déclarées. Ajouter un cas ne demande pas de toucher au moteur.
REGLES = {
    (Etat.POSTULABLE, Etat.FERME): Effet(
        "silencieuse", "dépôt clos — les alertes POSTULER en attente sont annulées",
        annule_postuler=True),
    (Etat.POSTULABLE, Etat.ANNULE): Effet(
        "normale", "procédure annulée avant la clôture — souvent relancée",
        annule_postuler=True),
    (Etat.FERME, Etat.ATTRIBUE): Effet(
        "normale", "titulaire connu — passer en DÉVELOPPER et le contacter",
        recuperer_titulaire=True),
    (Etat.POSTULABLE, Etat.ATTRIBUE): Effet(
        "normale", "attribué — passer en DÉVELOPPER et contacter le titulaire",
        annule_postuler=True, recuperer_titulaire=True),
    (Etat.ANNONCE, Etat.POSTULABLE): Effet(
        "forte", "LE MARCHÉ EST MAINTENANT OUVERT — le besoin annoncé se concrétise"),
    (Etat.INFRUCTUEUX, Etat.POSTULABLE): Effet(
        "forte", "NOUVELLE CHANCE DE POSTULER — la procédure est relancée"),
    (Etat.ANNULE, Etat.POSTULABLE): Effet(
        "forte", "RELANCE APRÈS ANNULATION — la procédure rouvre"),
    (Etat.FERME, Etat.POSTULABLE): Effet(
        "forte", "RÉOUVERTURE — le dépôt est de nouveau possible"),
    (Etat.INFORMATIF, Etat.POSTULABLE): Effet(
        "forte", "LE MARCHÉ EST MAINTENANT OUVERT"),
    (Etat.FERME, Etat.INFRUCTUEUX): Effet(
        "normale", "sans suite — l'acheteur cherche toujours, c'est le moment"),
    (Etat.ATTRIBUE, Etat.ANNULE): Effet(
        "normale", "attribution annulée — la procédure peut repartir"),
}

EFFET_PAR_DEFAUT = Effet("silencieuse", "changement d'état enregistré")

# Les règles sont écrites avec des membres d'`Etat` pour rester lisibles ; on
# les indexe par libellé parce que l'état stocké peut aussi valoir
# « HORS PROCÉDURE », qui n'appartient à aucune énumération.
REGLES_PAR_LIBELLE = {(a.value, b.value): e for (a, b), e in REGLES.items()}


@dataclass
class Transition:
    avis_id: int
    ancien: str | None          # libellé tel qu'il est écrit en base
    nouveau: str
    ancienne_confiance: str | None
    nouvelle_confiance: str
    preuve: str
    source: str
    origine: str = COLLECTE
    version_vocabulaire: int | None = None
    effet: Effet = field(default_factory=lambda: EFFET_PAR_DEFAUT)

    @property
    def premiere_observation(self) -> bool:
        return self.ancien is None

    @property
    def alerte(self) -> bool:
        """Une transition mérite-t-elle de réveiller quelqu'un ?"""
        if self.premiere_observation or self.origine != COLLECTE:
            return False
        if self.nouveau in (Etat.INCONNU.value, "HORS PROCÉDURE"):
            return False
        if self.nouvelle_confiance in (Confiance.FAIBLE.value, Confiance.NULLE.value):
            return False
        return self.effet.intensite in ("forte", "normale")

    def libelle(self) -> str:
        depuis = self.ancien or "première observation"
        return f"{depuis} → {self.nouveau} : {self.effet.message}"


def etat_precedent(cx, avis_id: int):
    """L'état déjà en base, sous la forme EXACTE qui y est écrite.

    On compare des libellés, pas des membres d'énumération. « HORS PROCÉDURE »
    est un libellé légitime — c'est ce que porte tout besoin privé — mais ce
    n'est pas une valeur de `Etat`. Le convertir levait une ValueError, l'état
    précédent ressortait None, et CHAQUE collecte d'un besoin privé écrivait
    une transition « découverte ». Le fil de vie se remplissait de bruit pour
    exactement la moitié privée du produit.
    """
    ligne = cx.execute(
        "SELECT etat_procedure, confiance_etat FROM opportunites WHERE avis_id=?",
        (avis_id,)).fetchone()
    if ligne is None or not ligne["etat_procedure"]:
        return None, None
    return ligne["etat_procedure"], ligne["confiance_etat"]


def constater(cx, avis_id: int, lecture, source: str, *, origine: str = COLLECTE,
              version_vocabulaire: int | None = None) -> Transition | None:
    """Compare l'état observé à celui en base. Écrit SEULEMENT s'il a changé.

    Renvoie None quand rien n'a bougé : une collecte identique ne doit fabriquer
    aucun événement, sinon le fil de vie devient un journal de passages du
    collecteur.
    """
    ancien, ancienne_conf = etat_precedent(cx, avis_id)
    nouveau = lecture.etat_affiche
    if ancien == nouveau:
        return None

    preuve = (str(lecture.preuves[0]) if lecture.preuves
              else "aucune preuve — état non démontré")
    t = Transition(
        avis_id=avis_id, ancien=ancien, nouveau=nouveau,
        ancienne_confiance=ancienne_conf, nouvelle_confiance=lecture.confiance.value,
        preuve=preuve, source=source, origine=origine,
        version_vocabulaire=version_vocabulaire,
        effet=REGLES_PAR_LIBELLE.get((ancien, nouveau), EFFET_PAR_DEFAUT))
    cx.execute(
        "INSERT INTO etats_historique(avis_id, ancien_etat, nouvel_etat,"
        " ancienne_confiance, nouvelle_confiance, preuve, source, origine,"
        " version_vocabulaire, constate_le) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (avis_id, ancien, nouveau, ancienne_conf, lecture.confiance.value,
         preuve, source, origine, version_vocabulaire, maintenant()))
    return t


def appliquer(cx, t: Transition, opp, corps: str) -> str | None:
    """Traduit la transition en actes. Renvoie le motif d'envoi, ou None."""
    from . import envoi

    if t.effet.annule_postuler:
        # On n'annule QUE ce qui n'est pas parti. Un message déjà en vol ne se
        # rattrape pas : on ne réécrit pas l'histoire, on marque l'intention.
        cx.execute(
            "UPDATE envois SET etat='perime',"
            " erreur='état devenu ' || ? || ' avant l''envoi', maj_le=?"
            " WHERE source=? AND ref_source=? AND etat='a_envoyer'",
            (t.nouveau, maintenant(), opp.source, opp.ref_source))

    if not t.alerte:
        return None

    motif = f"{t.ancien or 'NOUVEAU'}->{t.nouveau}"
    entete = (f"⚡ {t.effet.message}\n" if t.effet.intensite == "forte"
              else f"{t.effet.message}\n")
    envoi.mettre_en_file(cx, opp.source, opp.ref_source,
                         entete + "\n" + corps, motif=motif,
                         intensite=t.effet.intensite)
    return motif


def fil_de_vie(cx, avis_id: int) -> list:
    return cx.execute(
        "SELECT ancien_etat, nouvel_etat, preuve, origine, constate_le"
        " FROM etats_historique WHERE avis_id=? ORDER BY id", (avis_id,)).fetchall()
