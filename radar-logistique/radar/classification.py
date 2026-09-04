"""🟢 DIRECT · 🟡 RENFORCEMENT · 🟣 À CONSTRUIRE · 🔵 PROSPECT · 🔴 REJET

CHANGEMENT par rapport à la version précédente : 🟡 signifiait « sous-traitance »
et signifie désormais « je suis titulaire mais je dois me renforcer ». La
sous-traitance descend en 🔵, et 🟣 est nouveau.

Deux règles gouvernent tout :

  · ce que je ne peux pas porter seul, un autre le portera — il lui faudra des
    bras, donc 🔵 et jamais 🔴 ;
  · l'absence de vocabulaire connu n'est JAMAIS un motif de rejet. Un métier
    inconnu passe par le test 🟣 avant toute conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .role import Role


class Type(Enum):
    DIRECT = "DIRECT"
    RENFORCEMENT = "RENFORCEMENT"
    A_CONSTRUIRE = "A_CONSTRUIRE"
    PROSPECT = "PROSPECT"
    REJET = "REJET"

    @property
    def emoji(self) -> str:
        return {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
                "PROSPECT": "🔵", "REJET": "🔴"}[self.value]

    @property
    def notifiable(self) -> bool:
        return self is not Type.REJET


class Moteur(Enum):
    CAPTER = "CAPTER"          # je peux agir : postuler, contacter, proposer
    DEVELOPPER = "DEVELOPPER"  # fermé, mais action commerciale possible


class Action(Enum):
    POSTULER = "POSTULER"
    CONTACTER_ACHETEUR = "CONTACTER L'ACHETEUR"
    CONTACTER_ENTREPRISE = "CONTACTER L'ENTREPRISE"
    CONTACTER_TITULAIRE = "CONTACTER LE TITULAIRE"
    PROPOSER_SOUS_TRAITANCE = "PROPOSER SOUS-TRAITANCE"
    PROPOSER_PARTENARIAT = "PROPOSER PARTENARIAT"
    PROPOSER_GROUPEMENT = "PROPOSER UN GROUPEMENT"
    SURVEILLER = "SURVEILLER"
    VERIFIER_ETAT = "VÉRIFIER L'ÉTAT À LA SOURCE"
    ABANDONNER = "ABANDONNER"


# Blocages qui disent « trop gros pour moi », pas « je ne sais pas faire ».
# Ceux-là mènent en 🔵, jamais en 🔴.
BLOCAGES_DE_TAILLE = ("véhicules exigés", "chiffre d'affaires", "m² exigés",
                      "chauffeurs exigés")

# Part du besoin qu'il faut couvrir pour qu'un groupement soit crédible : en
# dessous, on n'apporte pas assez pour être associé, on est sous-traitant.
SEUIL_GROUPEMENT = 0.25


@dataclass
class Classement:
    type: Type
    moteur: Moteur
    action: Action
    motif: str
    raisons: list[str] = field(default_factory=list)
    raisons_rejet: list[str] = field(default_factory=list)


def _de_taille(message: str) -> bool:
    return any(m in message for m in BLOCAGES_DE_TAILLE)


def classer(*, role, activite_reconnue, exclusion, zone_ok, zone_motif,
            deadline_ouverte, deadline_motif, attribue, informatif,
            bilan_capacite, construction=None, est_signal=False,
            source_privee=False, nature=None, etat=None,
            procedure_detectee=False) -> Classement:
    """Décide de la catégorie, du moteur et de l'action unique.

    Aucun paramètre ne nomme une source, et c'est délibéré : brancher TED,
    Google, une bourse de fret ou la page d'une PME ne change rien ici. Ce qui
    entre, ce sont des faits sur le BESOIN — objet, zone, échéance, exigences —
    et la capacité de l'entreprise à le servir.
    """
    from .nature import Nature
    nature = nature or Nature.FAIT

    # ── 1. Impossibilités objectives sur l'objet ──
    if role is Role.FOURNISSEUR:
        return Classement(Type.REJET, Moteur.CAPTER, Action.ABANDONNER,
                          "marché de fourniture — l'acheteur veut un bien",
                          raisons_rejet=["l'entreprise vend une prestation, pas un produit"])
    if exclusion:
        return Classement(Type.REJET, Moteur.CAPTER, Action.ABANDONNER,
                          f"activité juridiquement inaccessible ({exclusion})",
                          raisons_rejet=[f"activité exclue : {exclusion}"])
    if not zone_ok:
        return Classement(Type.REJET, Moteur.CAPTER, Action.ABANDONNER,
                          zone_motif or "zone incompatible",
                          raisons_rejet=[zone_motif or "zone incompatible"])

    # ── 3. L'ÉTAT DE LA PROCÉDURE décide de l'ACTION ──
    #
    # Aucun de ces cas n'est un rejet : un marché fermé, annulé ou attribué
    # garde toute sa valeur commerciale. Il change seulement de moteur.
    from .procedure import Etat as EtatProcedure
    etat = etat or (EtatProcedure.ATTRIBUE if attribue else
                    EtatProcedure.INFORMATIF if informatif else
                    EtatProcedure.POSTULABLE if deadline_ouverte else EtatProcedure.FERME)

    if etat is EtatProcedure.ATTRIBUE:
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.CONTACTER_TITULAIRE,
                          "marché déjà attribué — le titulaire devra exécuter",
                          raisons=["le titulaire aura besoin de capacité locale",
                                   "anticiper la remise en concurrence"])
    if etat is EtatProcedure.ANNONCE:
        # La meilleure fenêtre commerciale du cycle : le besoin est identifié,
        # la procédure n'est pas ouverte, et personne n'est encore arrivé.
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.SURVEILLER,
                          "ANNONCÉ — le besoin est identifié, la procédure n'est "
                          "pas encore ouverte",
                          raisons=["potentiel : futur marché",
                                   "action secondaire : contacter l'acheteur si pertinent",
                                   "surveiller l'ouverture — la transition déclenchera "
                                   "une alerte forte"])
    if etat is EtatProcedure.INFORMATIF:
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.SURVEILLER,
                          "informatif — aucun besoin identifié, aucune action directe",
                          raisons=["conservé : le contexte peut servir plus tard"])
    if etat is EtatProcedure.ANNULE:
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.SURVEILLER,
                          "procédure annulée — le besoin, lui, n'a pas disparu",
                          raisons=["une annulation est très souvent suivie d'une relance"])
    if etat is EtatProcedure.INFRUCTUEUX:
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.CONTACTER_ACHETEUR,
                          "procédure sans suite — l'acheteur cherche toujours",
                          raisons=["personne n'a répondu ou aucune offre n'a convenu",
                                   "c'est le meilleur moment pour se faire connaître"])
    if etat is EtatProcedure.FERME:
        return Classement(Type.PROSPECT, Moteur.DEVELOPPER, Action.SURVEILLER,
                          "FERMÉ — attribution NON PUBLIÉE",
                          raisons=[deadline_motif or "dépôt clos",
                                   "aucune attribution constatée : ce n'est PAS un "
                                   "marché attribué",
                                   "surveiller la publication du résultat"])
    # ── Signal : un prospect, jamais un contrat ──
    #
    # On lit la NATURE (dimension C), pas un drapeau posé par l'adaptateur : un
    # événement — « nous ouvrons un dépôt à Gand » — trouvé par un moteur de
    # recherche ne portait aucun drapeau et ressortait 🟢 DIRECT. Un événement
    # observé devenait un contrat prêt à signer.
    #
    # Ce test vient APRÈS les états de procédure : une attribution est elle
    # aussi un signal, mais un signal dont on connaît déjà l'action —
    # contacter le titulaire, pas « qualifier ».
    from .nature import Nature
    if est_signal or nature is Nature.SIGNAL:
        return Classement(Type.PROSPECT, Moteur.CAPTER, Action.CONTACTER_ENTREPRISE,
                          "signal d'un besoin logistique — à qualifier",
                          raisons=["inférence, pas un marché ouvert"])

    if etat is EtatProcedure.INCONNU and procedure_detectee:
        # Le cas le plus important : on ne sait pas, et on le dit. L'opportunité
        # reste dans le radar — elle n'est ni jetée, ni promue en POSTULABLE.
        return Classement(Type.PROSPECT, Moteur.CAPTER, Action.VERIFIER_ETAT,
                          "ÉTAT À VÉRIFIER — la source ne permet pas de conclure",
                          raisons=["ni ouvert ni attribué de façon démontrable",
                                   "vérifier à la source avant d'engager du temps"])

    # On ne dépose un dossier que sur un besoin PUBLIÉ. Sur une hypothèse —
    # une page qui dit « devenir partenaire transporteur », sans date ni
    # demandeur nommé — l'action juste est d'appeler, pas de candidater.
    depot = nature.depot_attendu and not source_privee
    action_defaut = Action.POSTULER if depot else Action.CONTACTER_ENTREPRISE

    # ── 4. Blocages de capacité : taille ou nature ? ──
    if bilan_capacite.bloquants:
        de_taille = [b for b in bilan_capacite.bloquants if _de_taille(b)]
        autres = [b for b in bilan_capacite.bloquants if not _de_taille(b)]
        if autres:
            return Classement(Type.REJET, Moteur.CAPTER, Action.ABANDONNER, autres[0],
                              raisons_rejet=autres)
        # Trop grand seul ne veut pas dire hors d'atteinte : reste le groupement
        # momentané (répondre à plusieurs, en titulaire solidaire) et la
        # sous-traitance (travailler pour celui qui l'emportera). On chiffre
        # laquelle est plausible plutôt que de proposer les deux en vrac.
        part = bilan_capacite.part_couverte()
        raisons = ["prestation dans mon savoir-faire"]
        if part is not None:
            raisons.append(f"tu couvres {part:.0%} du besoin avec tes moyens mobilisables")
        if part is not None and part >= SEUIL_GROUPEMENT:
            raisons.append("part suffisante pour entrer dans un groupement momentané "
                           "avec une ou deux autres entreprises")
            action = Action.PROPOSER_GROUPEMENT
        else:
            raisons.append("part trop faible pour un groupement — entrée par "
                           "sous-traitance d'une zone ou d'une tournée")
            action = Action.PROPOSER_SOUS_TRAITANCE
        return Classement(Type.PROSPECT, Moteur.CAPTER, action,
                          f"trop grand pour être porté seul — {de_taille[0]}",
                          raisons=raisons)

    # ── 5. Métier reconnu ou non ──
    if not activite_reconnue:
        # L'absence de vocabulaire ne rejette RIEN : on passe par le test 🟣.
        if construction is not None and construction.eligible:
            return Classement(Type.A_CONSTRUIRE, Moteur.CAPTER, action_defaut,
                              construction.motif, raisons=construction.leviers)
        raisons = (construction.manques if construction else
                   ["prestation non reconnue et aucune formation mentionnée"])
        return Classement(Type.PROSPECT, Moteur.CAPTER, Action.SURVEILLER,
                          "métier hors périmètre actuel — à qualifier manuellement",
                          raisons=raisons)

    # ── 6. Reste le cas normal : direct ou renforcement ──
    if bilan_capacite.mobilisations:
        return Classement(Type.RENFORCEMENT, Moteur.CAPTER, action_defaut,
                          "titulaire possible après mobilisation de moyens",
                          raisons=list(bilan_capacite.mobilisations))
    return Classement(Type.DIRECT, Moteur.CAPTER, action_defaut,
                      "exécutable avec la structure actuelle",
                      raisons=list(bilan_capacite.atouts))
