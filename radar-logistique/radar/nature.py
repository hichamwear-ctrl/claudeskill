"""FAIT, SIGNAL ou HYPOTHÈSE — ce que la donnée est, pas d'où elle vient.

Le centre du radar n'est ni la source, ni l'appel d'offres : c'est le besoin
commercial et sa rentabilité. Mais tous les besoins ne sont pas connus avec la
même certitude, et cette différence doit être VISIBLE sans jamais devenir un
avantage de score.

  FAIT       le besoin est publié et daté. Un marché ouvert, une tournée
             proposée sur une bourse de fret, une consultation en cours.
  SIGNAL     un événement observable laisse penser qu'un besoin existe.
             Recrutement de quinze chauffeurs, ouverture d'un dépôt, marché
             attribué à un titulaire qui devra exécuter.
  HYPOTHESE  une page dit quelque chose qui ressemble à un besoin, sans qu'on
             sache s'il est actuel. « Devenir partenaire transporteur »
             trouvé par un moteur de recherche.

Ce que la nature change :
  · l'action proposée — on ne dépose pas un dossier sur une hypothèse ;
  · ce que la fiche affiche — on ne présente jamais une inférence comme un fait.

Ce que la nature NE change PAS :
  · le score. Un besoin réel vaut ce qu'il rapporte, pas ce qui l'a révélé.

Et surtout : la nature ne se déduit JAMAIS du nom de la source. Un appel
d'offres public n'est pas un fait « parce que c'est officiel » ; il est un fait
parce qu'il porte un objet, une échéance et un acheteur. Une page d'entreprise
qui publie un appel à partenaires daté est un fait, elle aussi.
"""

from __future__ import annotations

from enum import Enum


class Nature(Enum):
    FAIT = "FAIT"
    SIGNAL = "SIGNAL"
    HYPOTHESE = "HYPOTHÈSE"

    @property
    def emoji(self) -> str:
        return {"FAIT": "◆", "SIGNAL": "◈", "HYPOTHÈSE": "◇"}[self.value]

    @property
    def libelle(self) -> str:
        return {
            "FAIT": "besoin publié",
            "SIGNAL": "besoin déduit d'un événement observable",
            "HYPOTHÈSE": "besoin possible, non confirmé",
        }[self.value]

    @property
    def depot_attendu(self) -> bool:
        """Sur un fait, on peut déposer un dossier. Sur le reste, on parle."""
        return self is Nature.FAIT


def qualifier(opp) -> Nature:
    """Lit la nature dans les FAITS portés par l'opportunité.

    Aucune mention de source ici, et c'est le point : brancher une nouvelle
    source ne demande pas de toucher à cette fonction.
    """
    if getattr(opp, "est_signal", False) or getattr(opp, "signal_code", None):
        return Nature.SIGNAL
    if getattr(opp, "attribue", False):
        # Un marché attribué est un fait ; le besoin de sous-traitance qu'il
        # laisse deviner est un signal. C'est ce besoin-là qui nous intéresse.
        return Nature.SIGNAL

    # Un besoin est un FAIT quand la source dit ce qui est demandé ET par qui,
    # ou ce qui est demandé ET pour quand.
    objet = bool((getattr(opp, "intitule", "") or "").strip()
                 and (opp.intitule or "").strip() != "(sans intitulé)")
    demandeur = bool(getattr(opp, "acheteur", None))
    quand = bool(getattr(opp, "echeance_brute", None)
                 or getattr(opp, "date_demarrage", None))
    if objet and (demandeur or quand):
        return Nature.FAIT
    return Nature.HYPOTHESE
