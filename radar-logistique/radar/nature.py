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


# Un besoin énoncé À LA PREMIÈRE PERSONNE et au présent est un FAIT : quelqu'un
# l'a écrit. Ce qui reste une hypothèse, c'est ce que NOUS en déduisons.
#
#   « Nous recherchons un transporteur »              → FAIT
#   « L'entreprise recrute quinze chauffeurs »        → SIGNAL
#   « Elle aura probablement besoin de sous-traitants » → HYPOTHÈSE
#
# Le demandeur n'a pas besoin d'être nommé pour que le fait existe : une page
# qui dit « nous cherchons » dit qui cherche, même si son nom n'est pas
# extractible. Le déduire du domaine reviendrait à inventer un nom — interdit.
BESOIN_DIRECT = (
    "nous recherchons", "nous cherchons", "nous recrutons", "nous confions",
    "nous souhaitons", "nous faisons appel", "recherchons un", "recherchons des",
    "cherchons un", "cherchons des", "devenez", "devenir partenaire",
    "rejoignez", "notre societe recherche", "appel a partenaires",
    "wij zoeken", "wij werken samen", "word partner", "gezocht",
    "we are looking for", "we seek", "join our", "become a", "wanted",
    "wir suchen", "gesucht",
    # Formes réelles rencontrées sur des pages commerciales, moins propres que
    # « nous recherchons un transporteur » — mais tout aussi explicites.
    "besoin de", "besoins de", "recherche fournisseur", "recherche transporteur",
    "recherche prestataire", "recherche partenaire", "recherche de partenaires",
    "souhaitons referencer", "souhaitons confier", "cherchons a externaliser",
    "externaliser une partie", "referencer plusieurs", "faisons appel a",
    # « Appel à sous-traitants » est une demande explicite, pas une déduction :
    # l'entreprise dit ce qu'elle cherche. Elle ressortait HYPOTHÈSE.
    "appel a sous traitants", "appel a partenaires", "appel a candidatures",
    "avis de recherche", "consultation fournisseurs", "referencement ouvert",
)

# ── ÉVÉNEMENTS OBSERVABLES ────────────────────────────────────────────────
# Un fait qui se produit chez quelqu'un d'autre, et dont on DÉDUIT un besoin
# possible. La distinction avec BESOIN_DIRECT est tout le produit :
#
#   « nous cherchons un transporteur »   → FAIT      : ils le disent
#   « nous ouvrons un dépôt à Gand »     → SIGNAL    : ils ne demandent rien
#   « ils auront besoin de sous-traiter » → HYPOTHÈSE : c'est NOUS qui le disons
#
# Sans cette liste, la nature d'un événement dépendait d'un drapeau posé par
# l'adaptateur — donc un même événement trouvé par un moteur de recherche
# tombait en HYPOTHÈSE, alors qu'il est parfaitement observable.
EVENEMENT_OBSERVABLE = (
    "nous ouvrons", "ouverture de", "ouverture d un", "nouveau depot",
    "nouveau site", "nouveau centre", "nouvelle plateforme", "nouvelle agence",
    "s implante", "implantation", "nous inaugurons", "mise en service",
    "recrute", "recrutons", "recrutement", "recherches", "recherchees",
    "chauffeurs recherches", "postes a pourvoir", "va doubler", "vont doubler",
    "en forte croissance", "double sa capacite", "etend son activite",
    "arrivant a echeance", "arrive a echeance", "fin de contrat",
    "renouvellement du contrat", "prestataire actuel", "titulaire actuel",
    "remporte un contrat", "a remporte", "change de prestataire",
    "opent", "opening", "opens new", "wij openen", "recruteert",
    "eroffnet", "expands", "is expanding",
)


# ── OFFRE DE SERVICE : un concurrent, pas un client ───────────────────────
#
# Le défaut que seule une donnée réelle pouvait montrer. Sur seize résultats
# de recherche réels, SEPT étaient des pages de transporteurs vendant leurs
# services — « Transport de Palettes Belgique Pas Cher - Prix »,
# « Transporteur palette Belgique France », « trouver-un-transporteur.com ».
# Toutes ressortaient 🟢 DIRECT, action CONTACTER L'ENTREPRISE.
#
# Commercialement : le commercial appelle sept concurrents en croyant appeler
# des prospects. Il perd sa journée, et il annonce son intérêt à la
# concurrence.
#
# Pourquoi c'était invisible : les douze familles de fixtures décrivent toutes
# une DEMANDE. Aucune ne décrivait une OFFRE. Reconnaître le vocabulaire du
# métier dans un titre suffisait à en faire une opportunité directe — le
# symétrique exact de l'erreur qu'on avait interdite (rejeter faute de mot).
#
# La règle reste conservatrice : ces marqueurs ne DÉMOTENT que s'il n'y a
# AUCUN besoin exprimé. « Devenir partenaire transporteur » porte les deux ;
# la demande l'emporte, toujours.
OFFRE_DE_SERVICE = (
    "pas cher", "moins cher", "moins chere", "moins cheres", "meilleur prix",
    "prix", "tarif", "tarifs", "jusqu a 40", "economisez",
    "devis", "devis gratuit", "comparez", "comparateur", "obtenez",
    "nos services", "nos solutions", "solutions logistiques", "nos tarifs",
    "prestataire de services", "fournisseurs en", "trouver un transporteur",
    "notre flotte", "nous transportons", "nous assurons le transport",
    "specialiste du transport", "votre transporteur", "votre partenaire",
    "goedkoop", "offerte aanvragen", "onze diensten",
    "cheap", "get a quote", "our services", "compare",
    "gunstig", "angebot anfordern", "unsere leistungen",
)


def est_une_offre(opp) -> bool:
    """Cette page VEND-elle du transport, au lieu d'en chercher ?"""
    if _besoin_exprime(opp):
        return False        # la demande l'emporte, toujours
    return _contient(opp, OFFRE_DE_SERVICE)


def _contient(opp, marqueurs) -> bool:
    import re
    import unicodedata
    texte = f"{getattr(opp, 'intitule', '') or ''} {getattr(opp, 'texte', '') or ''}"
    plat = unicodedata.normalize("NFKD", texte)
    plat = "".join(c for c in plat if not unicodedata.combining(c)).lower()
    plat = " " + re.sub(r"[^a-z0-9]+", " ", plat).strip() + " "
    return any(f" {m} " in plat for m in marqueurs)


def _evenement_observable(opp) -> bool:
    import re
    import unicodedata
    texte = f"{getattr(opp, 'intitule', '') or ''} {getattr(opp, 'texte', '') or ''}"
    plat = unicodedata.normalize("NFKD", texte)
    plat = "".join(c for c in plat if not unicodedata.combining(c)).lower()
    plat = " " + re.sub(r"[^a-z0-9]+", " ", plat).strip() + " "
    return any(f" {m} " in plat for m in EVENEMENT_OBSERVABLE)


def _besoin_exprime(opp) -> bool:
    import re
    import unicodedata
    texte = f"{getattr(opp, 'intitule', '') or ''} {getattr(opp, 'texte', '') or ''}"
    plat = unicodedata.normalize("NFKD", texte)
    plat = "".join(c for c in plat if not unicodedata.combining(c)).lower()
    plat = " " + re.sub(r"[^a-z0-9]+", " ", plat).strip() + " "
    return any(f" {m} " in plat for m in BESOIN_DIRECT)


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

    # Un besoin est un FAIT à DEUX conditions seulement :
    #   · quelqu'un l'énonce — « nous recherchons un transporteur » ; ou
    #   · il est daté, donc publié dans un cadre — échéance ou démarrage.
    #
    # Le nom du demandeur ne suffit PAS. « Distributeur régional, trois sites,
    # flotte saturée » nomme une entreprise réelle et ne déclare aucun besoin :
    # le besoin, c'est NOUS qui le déduisons de « flotte saturée ». Compter ce
    # cas comme un fait présentait notre propre inférence comme la parole du
    # client, et rangeait une entreprise à prospecter parmi les besoins exprimés.
    objet = bool((getattr(opp, "intitule", "") or "").strip()
                 and (opp.intitule or "").strip() != "(sans intitulé)")
    # Un besoin ÉNONCÉ prime sur un événement : si l'entreprise ouvre un dépôt
    # ET dit chercher un transporteur, c'est la demande qui compte.
    if objet and _besoin_exprime(opp):
        return Nature.FAIT
    if objet and _evenement_observable(opp):
        return Nature.SIGNAL
    # Une source qui déclare un TYPE ou un STATUT a publié quelque chose de
    # structuré : c'est un fait, même sans date. Un avis de préinformation
    # ressortait HYPOTHÈSE alors qu'il est une publication officielle.
    #
    # `type_avis` DOIT être lu ici comme il l'est par la lecture d'état, qui
    # fait déjà `type_information or type_avis`. Il ne l'était pas, et les deux
    # étages se contredisaient : un avis de marché publié — rubrique normée,
    # état POSTULABLE, guichet de dépôt, montant, durée — sortait FAIT côté
    # état et HYPOTHÈSE côté nature. Or `depot_attendu` ne vaut que sur un
    # FAIT : l'action devenait « CONTACTER L'ENTREPRISE » sur un appel
    # d'offres parfaitement déposable. On téléphone à un pouvoir adjudicateur
    # au lieu de remettre une offre, et le marché est perdu.
    #
    # Le cas ne se voyait pas sur les fixtures, qui portent toutes une
    # échéance — laquelle suffisait, plus bas, à rattraper la nature. Il
    # apparaît dès qu'un avis publie son type et son montant mais laisse la
    # date limite dans les documents, ce qui est courant.
    if objet and (getattr(opp, "type_information", None)
                  or getattr(opp, "type_avis", None)
                  or getattr(opp, "statut_source", None)):
        return Nature.FAIT
    quand = bool(getattr(opp, "echeance_brute", None)
                 or getattr(opp, "date_demarrage", None))
    if objet and quand:
        return Nature.FAIT
    return Nature.HYPOTHESE
