"""Faire entrer une trouvaille dans la chaîne — sans rien transformer en fait.

    MOTEUR → TROUVAILLE → ENTREPRISE ÉVENTUELLE → PAGE CANDIDATE
           → COLLECTE → QUALIFICATION → SURVEILLÉE si preuve suffisante

Ce module relie les trois premiers maillons. Les quatre suivants existent
déjà — collecte directe, qualification de 7b, identité de 7c, chaîne
d'analyse — et il n'y touche pas.

SEPT NIVEAUX, ET ILS NE SE RACCOURCISSENT PAS
=============================================

    TROUVAILLE          un moteur a montré une URL
    ENTREPRISE          une organisation POSSIBLE, identité INCONNUE
    PAGE CANDIDATE      une URL qu'on envisage de surveiller
    PAGE COLLECTÉE      un contenu réellement récupéré
    PAGE QUALIFIÉE      un contenu analysé (7b)
    ENTREPRISE CONFIRMÉE  une identité démontrée (7c)
    OPPORTUNITÉ         un besoin suffisamment établi (la chaîne)

8c relie les trois premiers. Il ne saute aucun niveau, et surtout il ne
fabrique pas le septième.

LA SEULE RELATION PAGE ↔ ENTREPRISE QUI SOIT OBSERVABLE
=======================================================

C'est L'HÔTE. Une page servie par `exemple.be` est servie par l'entité qui
tient `exemple.be`. C'est un fait.

Tout le reste est de la ressemblance : un titre qui contient un nom, deux
raisons sociales voisines, un extrait qui cite une société. On n'en fait rien.
Quand la relation n'est pas prouvée, la page porte `NON ÉTABLI` — et le dire
vaut mieux que le taire.

UN NOM DANS UN TITRE NE PROUVE PAS QUI TIENT LE DOMAINE
=======================================================

Ce sont DEUX faits différents, et les confondre était un vrai défaut, corrigé
avant livraison :

    « Fictif SA ouvre un dépôt à Gand »  sur  presse-fictive.example

    fait 1 — une entité sert presse-fictive.example. Son nom est INCONNU.
    fait 2 — une société nommée « Fictif SA » existe quelque part. Son
             domaine est INCONNU.

Rien ne relie les deux : le site qui PUBLIE l'article n'est pas l'entreprise
dont il PARLE. Créer « Fictif SA » avec la clé « presse-fictive.example »
aurait été exactement ce que la règle interdit — rattacher une page à une
entreprise parce que son nom y figure.

L'entreprise créée ici est donc TOUJOURS désignée par son DOMAINE, jamais par
un nom lu dans un titre ou un extrait. La vraie raison sociale se lira sur la
page elle-même, quand elle aura été COLLECTÉE — c'est le rôle du profil de
lecture, et c'est une preuve, pas une ressemblance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import adresse as mod_adresse, identite as mod_identite, pages as mod_pages
from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE
from .entreprises import Motif, domaine_de, nom_probable


@dataclass
class Bilan:
    """Ce que le chaînage a réellement produit. Aucun de ces nombres n'est
    une opportunité."""
    trouvailles_lues: int = 0
    entreprises_nouvelles: int = 0
    entreprises_connues: int = 0
    pages_candidates: int = 0
    pages_deja_connues: int = 0
    sans_entreprise: int = 0
    rattachements_non_etablis: int = 0
    motifs: list = field(default_factory=list)

    def resume(self) -> str:
        L = ["CHAÎNAGE DES TROUVAILLES", "=" * 72, ""]
        L.append(f"  trouvailles lues           {self.trouvailles_lues}")
        L.append(f"  entreprises nouvelles      {self.entreprises_nouvelles}")
        L.append(f"  entreprises déjà connues   {self.entreprises_connues}")
        L.append(f"  sans entreprise nommable   {self.sans_entreprise}")
        L.append(f"  pages candidates nouvelles {self.pages_candidates}")
        L.append(f"  pages déjà connues         {self.pages_deja_connues}")
        L.append(f"  rattachements NON ÉTABLIS  {self.rattachements_non_etablis}")
        L.append("")
        L.append("  Aucune opportunité n'a été créée : une URL montrée par un")
        L.append("  moteur n'est pas un besoin. Aucune identité n'a été")
        L.append("  confirmée : toutes les entreprises créées ici sont INCONNUES.")
        L.append("  Aucune page n'est surveillée d'office : la qualification sur")
        L.append("  contenu réel décide, et elle exige une collecte.")
        return "\n".join(L)


def _entreprise_de(registre, trouvaille):
    """L'entité qui SERT cette URL — désignée par son domaine, et rien d'autre.

    Pas par un nom lu dans le titre : un nom cité sur une page ne prouve pas
    qui tient le domaine. Un site de presse qui parle d'une entreprise n'est
    pas cette entreprise.

    Sans domaine exploitable, on ne crée rien. Une entreprise sans adresse
    serait une fiche vide qui polluerait le registre pour toujours.
    """
    domaine = domaine_de(trouvaille.url)
    if not domaine:
        return None, None
    return domaine, domaine


def societe_citee(trouvaille) -> str | None:
    """La raison sociale CITÉE dans ce que le moteur a rendu, si sa forme
    juridique la prouve. C'est une observation sur le TEXTE — elle ne dit rien
    de qui tient le domaine, et ce module n'en fait donc rien.

    Exposée pour que l'information ne soit pas perdue : elle servira le jour où
    l'on saura relier une société citée à une entité, avec une preuve.
    """
    return nom_probable(f"{trouvaille.titre or ''} {trouvaille.extrait or ''}")


def chainer(cx, trouvailles, registre, *, motif: Motif = Motif.CHERCHE_PARTENAIRE,
            ontologie=None, detecteur=None) -> Bilan:
    """Fait entrer des trouvailles dans le registre et les pages candidates.

    `registre` est un `entreprises.Registre` — chargé depuis la base par
    l'appelant, et réécrit par lui. Ce module ne persiste pas les entreprises :
    il ne décide pas de la durée de vie du registre.

    Ne crée AUCUNE opportunité, ne confirme AUCUNE identité, ne surveille
    AUCUNE page.
    """
    bilan = Bilan()
    for t in trouvailles or []:
        bilan.trouvailles_lues += 1
        nom, domaine = _entreprise_de(registre, t)

        cle = None
        if nom is None:
            bilan.sans_entreprise += 1
        else:
            connue = registre._retrouver(nom, domaine)[1] is not None
            e = registre.decouvrir(nom, domaine=domaine, motif=motif,
                                   origine=f"{t.source}/découverte")
            cle = e.cle
            if connue:
                bilan.entreprises_connues += 1
            else:
                bilan.entreprises_nouvelles += 1

        # LE RATTACHEMENT. L'hôte de la page est-il celui de l'entreprise ?
        # C'est la seule relation observable. Toute autre serait une
        # ressemblance, et une ressemblance n'est pas une preuve.
        rattachee = cle is not None and domaine_de(t.url) == cle
        if not rattachee:
            bilan.rattachements_non_etablis += 1

        existait = mod_pages.lire(cx, t.url) is not None
        mod_pages.rencontrer(
            cx, t.url,
            entreprise=cle if rattachee else None,
            provenance=mod_pages.DECOUVERTE,
            source=t.source, circuit=t.circuit or CIRCUIT_DECOUVERTE,
            raison=_raison(t, ontologie, detecteur),
            libelle=t.titre or None,
            rattachement=(mod_pages.PAR_DOMAINE if rattachee
                          else mod_pages.NON_ETABLI))
        if existait:
            bilan.pages_deja_connues += 1
        else:
            bilan.pages_candidates += 1
    return bilan


def _raison(t, ontologie, detecteur) -> str:
    """Pourquoi cette page est candidate — et l'indice d'adresse s'il y en a un.

    L'indice est écrit DANS LA RAISON, en toutes lettres, plutôt que dans un
    champ silencieux : c'est ce qui permet de relire plus tard pourquoi une
    page a été mise en tête de la file de lecture. Il n'accorde aucun statut.
    """
    base = (f"montrée par « {t.source} »"
            + (f" pour la requête {t.requete}" if t.requete else ""))
    if ontologie is None or detecteur is None:
        return base
    indice = mod_adresse.lire(t.url, ontologie, detecteur).raison()
    return f"{base} · {indice}" if indice else base


def marquer_identites(cx, registre) -> int:
    """Écrit la provenance « découverte » sur les entreprises encore INCONNUES.

    À appeler APRÈS avoir persisté le registre : la ligne doit exister en base.
    Une identité déjà établie n'est jamais dégradée — voir
    `identite.depuis_decouverte`.
    """
    n = 0
    for cle, e in registre.entreprises.items():
        if not (e.origine or "").endswith("/découverte"):
            continue
        avant = mod_identite.lire(cx, cle)
        if avant.etat is not mod_identite.Etat.INCONNUE:
            continue
        mod_identite.depuis_decouverte(cx, cle, e.domaine or cle,
                                       source=mod_identite.DECOUVERTE)
        n += 1
    return n
