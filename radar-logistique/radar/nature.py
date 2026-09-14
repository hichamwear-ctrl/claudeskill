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
    # ── DÉCISION MÉTIER 2 · une seule entrée, et elle a un jumeau ──
    # « Travailler comme partenaire de PostNL » est le même acte que
    # « Devenir partenaire de livraison — Colis Privé » : un donneur d'ordre
    # publie qu'il cherche des partenaires. `devenir partenaire` est dans
    # cette liste depuis l'origine et vaut à Colis Privé son verdict VRAI
    # POSITIF ; sa formulation jumelle n'y était pas, et PostNL — désigné par
    # la relecture comme la meilleure piste du jeu du 14/09 — ressortait
    # HYPOTHÈSE, action CLASSER SANS SUITE.
    "travailler comme partenaire",
)

# ── LA PART DE BESOIN_DIRECT QUI NE DEMANDE PAS UNE PRESTATION ────────────
#
# Ce n'est PAS une liste de plus : c'est une PARTITION de celle du dessus.
# Chaque entrée ci-dessous est déjà dans BESOIN_DIRECT ; aucune expression
# nouvelle n'apparaît ici, et `qualifier()` continue de lire BESOIN_DIRECT
# entière, sans le moindre changement de nature.
#
# Ce que la partition sépare — deux familles, et rien d'autre :
#
#   INVITATION            « Rejoignez-nous » · « Wanted » · « Devenez… »
#                         on s'adresse au lecteur ; personne ne dit ce qui
#                         lui manque. N'importe quelle entreprise de
#                         n'importe quel secteur l'écrit.
#
#   RECRUTEMENT DE        « Nous recrutons » — on embauche des salariés.
#   PERSONNEL             C'est la DÉCISION MÉTIER DE 7d, déjà prise et déjà
#                         mesurée : « Nous recrutons 20 chauffeurs » est un
#                         recrutement, pas l'achat d'une prestation de
#                         transport. La déplacer ici ne la change pas, elle
#                         l'applique au même endroit que le reste.
#
# Les deux restent des besoins exprimés — `besoin_exprime_dans` les voit — et
# une page qui les porte reste CANDIDATE, donc relisible. Elles ne valent
# simplement pas, à elles seules, PREUVE POSITIVE à la porte des pages.
#
# Quand la prestation EST demandée, le détecteur de rôle le dit et la porte
# s'ouvre par là : « Nous recrutons des sous-traitants » ressort PRESTATAIRE.
BESOIN_SANS_PRESTATION = (
    # invitations
    "devenez", "devenir partenaire", "travailler comme partenaire", "rejoignez",
    "word partner", "join our", "become a", "wanted", "gezocht", "gesucht",
    # recrutement de personnel — décision 7d
    "nous recrutons",
)

# Ce qui reste : le besoin ÉNONCÉ d'une prestation. Dérivé, jamais recopié —
# ajouter une expression dans BESOIN_DIRECT la fait entrer ici
# automatiquement, ce qui est le comportement voulu : on n'oublie pas de
# mettre à jour une deuxième liste.
BESOIN_ENONCE = tuple(m for m in BESOIN_DIRECT if m not in BESOIN_SANS_PRESTATION)

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
    # ── DÉCISION MÉTIER 2 · les formulations TROP AMBIGUËS POUR UN FAIT ──
    #
    # Ces deux-là ont été étudiées pour BESOIN_DIRECT, et refusées là :
    #
    #   « Sous-traitance transport en Belgique | Partenaire DPD & DHL »
    #       une entreprise DÉCRIT ce qu'elle fait. Personne ne demande rien.
    #       En faire un FAIT aurait présenté une auto-description comme un
    #       besoin publié — précisément ce que la distinction FAIT / SIGNAL /
    #       HYPOTHÈSE existe pour empêcher.
    #
    #   « Devenir livreur indépendant en Belgique : guide complet »
    #       formulation signalée comme sensible, et elle l'est : mesurée sur
    #       huit contextes, elle promeut aussi bien une page de recrutement
    #       qu'un dossier de presse ou une page tarifaire.
    #
    # Comme SIGNAL, elles disent ce qu'elles sont vraiment : il se passe
    # quelque chose chez quelqu'un — un programme de partenaires existe, une
    # entreprise se déclare sous-traitante — et PERSONNE N'A RIEN DEMANDÉ.
    # La fiche l'écrit en toutes lettres, et l'action reste un contact, pas
    # un dépôt.
    #
    # Mesuré sur le jeu réel du 14/09 : Shippr et Bulbul redeviennent
    # visibles (🔵 PROSPECT · SIGNAL · CONTACTER L'ENTREPRISE) sans qu'aucun
    # des deux guides administratifs ni le billet de blog ne bouge.
    "sous traitance transport", "devenir livreur",
    # Même famille, même raison. Effet MESURÉ sur le jeu du 14/09 : AUCUN —
    # aucune des 28 adresses ne porte cette formulation. Elle est ajoutée
    # pour la cohérence de la famille, et ce compte rendu le dit plutôt que
    # de laisser croire qu'elle a servi.
    "devenir sous traitant",
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
    return offre_de_service_dans(_texte_de(opp))


# ── LIRE UN TEXTE, LIRE UNE OPPORTUNITÉ ───────────────────────────────────
#
# Les mêmes listes servent maintenant à DEUX appelants : cette qualification
# (qui reçoit une opportunité déjà normalisée) et la porte des pages
# (radar/ancrage.py, qui ne reçoit qu'un texte). Une seule lecture, exposée
# aux deux, plutôt que deux implémentations qui divergeraient au premier ajout
# dans les listes ci-dessus.
#
# `activite.normaliser` fait exactement ce que ces trois fonctions faisaient
# chacune dans leur coin — minuscules, accents retirés, ponctuation réduite à
# des espaces, texte encadré d'espaces pour chercher des mots entiers.

def _texte_de(opp) -> str:
    return (f"{getattr(opp, 'intitule', '') or ''} "
            f"{getattr(opp, 'texte', '') or ''}")


def _contient_texte(texte, marqueurs) -> bool:
    from .activite import normaliser
    plat = normaliser(texte or "")
    return any(f" {m} " in plat for m in marqueurs)


def besoin_exprime_dans(texte) -> bool:
    """Quelqu'un écrit qu'il cherche quelque chose."""
    return _contient_texte(texte, BESOIN_DIRECT)


def besoin_enonce_dans(texte) -> bool:
    """Le besoin est ÉNONCÉ par celui qui l'a — pas seulement proposé au lecteur.

    « Nous recherchons un partenaire » énonce une demande : quelqu'un dit ce
    qu'il lui manque. « Rejoignez-nous » invite, et n'importe quelle entreprise
    de n'importe quel secteur peut l'écrire sans rien demander à personne.

    Les deux restent des besoins exprimés — `besoin_exprime_dans` les voit
    tous les deux, et `qualifier` ci-dessous n'a pas changé. Mais seul le
    premier vaut PREUVE POSITIVE à la porte des pages : sans cette
    distinction, une page « Become part of our team » d'un cabinet comptable
    serait promue et collectée comme une piste de transport.
    """
    return _contient_texte(texte, BESOIN_ENONCE)


def evenement_observable_dans(texte) -> bool:
    return _contient_texte(texte, EVENEMENT_OBSERVABLE)


def offre_de_service_dans(texte) -> bool:
    """Ce texte VEND-il du transport, au lieu d'en chercher ?

    La règle est celle d'`est_une_offre` depuis l'origine, à la lettre — y
    compris son garde-fou : LA DEMANDE L'EMPORTE, TOUJOURS. « Devenir
    partenaire transporteur — nos tarifs » porte les deux ; c'est une
    demande, et cette fonction rend False.

    Elle est exposée sur un TEXTE pour que la porte des pages
    (radar/pertinence.py) puisse lire la même contre-preuve que la chaîne,
    au lieu d'en écrire une seconde qui divergerait au premier ajout dans
    OFFRE_DE_SERVICE.
    """
    if besoin_exprime_dans(texte):
        return False        # la demande l'emporte, toujours
    return _contient_texte(texte, OFFRE_DE_SERVICE)


# Le libellé que l'adaptateur écrit quand la source n'a PAS déclaré de titre.
# Ce n'est pas un titre : c'est la trace de son absence.
SANS_INTITULE = "(sans intitulé)"


def titre_declare(opp) -> bool:
    """La SOURCE a-t-elle déclaré un titre ? Jamais deviné, jamais fabriqué."""
    t = (getattr(opp, "intitule", "") or "").strip()
    return bool(t) and t != SANS_INTITULE


def _matiere_lue(opp) -> bool:
    """Y a-t-il quelque chose À LIRE — un titre déclaré, ou un corps lu ?

    DÉCISION MÉTIER 3. Cette fonction remplace un test qui ne regardait que
    l'intitulé :

        objet = bool(intitulé non vide et différent de « (sans intitulé) »)

    Toutes les branches qui rendent FAIT ci-dessous exigent `objet`. Une page
    sans titre déclaré ne pouvait donc JAMAIS être un fait, quoi qu'elle
    contienne. Mesuré sur un même corps de page, mot pour mot identique :

        titre « Nos partenaires »  →  🟢 DIRECT     · FAIT      · preuve MOYENNE
        titre « Actualités »       →  🟢 DIRECT     · FAIT      · preuve MOYENNE
        aucun titre                →  ⚪ PAS ENCORE · HYPOTHÈSE · preuve FAIBLE

    Le titre « Actualités » n'a aucun rapport avec le besoin, et donnait le
    même verdict que le titre pertinent : ce n'est donc pas le CONTENU du
    titre que la règle lisait, c'est la PRÉSENCE du champ. Une source qui
    omet une balise valait moins qu'une source qui en pose une vide de sens.

    Ce qui compte, c'est qu'il y ait de la matière à lire. Ce qui décide
    ensuite reste inchangé : un besoin exprimé, un événement observable, un
    type déclaré, une date. Le titre n'a jamais été, et n'est toujours pas,
    une preuve à lui seul — `titre_declare` reste disponible pour l'écrire
    quand il manque, et AUCUN titre n'est fabriqué à partir du corps.
    """
    return titre_declare(opp) or bool((getattr(opp, "texte", "") or "").strip())


def _contient(opp, marqueurs) -> bool:
    return _contient_texte(_texte_de(opp), marqueurs)


def _evenement_observable(opp) -> bool:
    return evenement_observable_dans(_texte_de(opp))


def _besoin_exprime(opp) -> bool:
    return besoin_exprime_dans(_texte_de(opp))


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
    objet = _matiere_lue(opp)
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
