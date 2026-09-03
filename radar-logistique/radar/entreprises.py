"""Registre des entreprises — une entreprise découverte ne disparaît jamais.

Elle devient une entité surveillée, qui produit ses propres recherches et donc
ses propres opportunités. C'est ce qui transforme une liste de résultats en
boucle commerciale.

Deux façons d'entrer : découverte automatiquement (Google, presse, BCE, un avis
d'attribution), ou ajoutée à la main par l'exploitant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse

from .deduplication import _plat


class Etat(Enum):
    DECOUVERTE = "DÉCOUVERTE"      # vue une fois, pas encore évaluée
    SURVEILLEE = "SURVEILLÉE"      # dans la rotation des recherches
    ECARTEE = "ÉCARTÉE"            # sans intérêt ou inaccessible — motif écrit


class Motif(Enum):
    """Pourquoi cette entreprise mérite d'être regardée. Jamais supposé :
    chaque motif vient d'un fait observé dans une source."""
    TITULAIRE = "a remporté un marché"
    RECRUTE = "recrute des chauffeurs"
    OUVRE_SITE = "ouvre un entrepôt ou une agence"
    CHERCHE_PARTENAIRE = "cherche un partenaire ou un sous-traitant"
    PAGE_FOURNISSEUR = "publie une page fournisseur ou partenaire"
    ACHETEUR = "achète du transport"
    EXPANSION = "se développe en Belgique"
    MANUEL = "ajoutée manuellement"


@dataclass
class Entreprise:
    nom: str
    domaine: str | None = None
    etat: Etat = Etat.DECOUVERTE
    motifs: list[str] = field(default_factory=list)
    origine: str | None = None            # la source qui l'a fait apparaître
    decouverte_le: str | None = None
    derniere_visite: str | None = None
    besoins_detectes: int = 0
    marches_gagnes: int = 0
    montant_gagne: float = 0.0
    bce: str | None = None
    contact: str | None = None
    motif_ecart: str | None = None
    profondeur: int = 0                   # 0 = trouvée en surface

    @property
    def cle(self) -> str:
        return self.domaine or _plat(self.nom)

    def interessante(self) -> bool:
        """Un fait observé suffit. On n'écarte pas faute d'informations."""
        return self.etat is not Etat.ECARTEE and bool(self.motifs)

    def ligne(self) -> str:
        visite = (self.derniere_visite or "jamais")[:10]
        return (f"{self.nom[:34]:<36} {self.etat.value:<12} "
                f"besoins={self.besoins_detectes:<3} marchés={self.marches_gagnes:<3} "
                f"vue={visite}  {'; '.join(self.motifs[:2])[:44]}")


def domaine_de(url: str | None) -> str | None:
    if not url:
        return None
    hote = urlparse(str(url)).netloc.lower().removeprefix("www.")
    return hote or None


def nom_probable(texte: str) -> str | None:
    """Extrait un nom d'entreprise plausible. Renvoie None plutôt que de forcer :
    un nom inventé pollue le registre pour toujours."""
    if not texte:
        return None
    m = re.search(r"\b([A-ZÉÈÀ][\w&'’.-]+(?:\s+[A-ZÉÈÀ][\w&'’.-]+){0,3})\s*"
                  r"(?:SA|SRL|SPRL|NV|BV|BVBA|SCRL|ASBL|VZW|GmbH|SAS|SARL)\b", texte)
    if m:
        return m.group(0).strip()
    return None


class Registre:
    def __init__(self):
        self.entreprises: dict[str, Entreprise] = {}

    # ------------------------------------------------------ entrées --
    def decouvrir(self, nom, *, domaine=None, motif: Motif = None, origine=None,
                  profondeur=0) -> Entreprise:
        cle = domaine or _plat(nom)
        e = self.entreprises.get(cle)
        if e is None:
            e = Entreprise(nom=nom, domaine=domaine, origine=origine,
                           profondeur=profondeur,
                           decouverte_le=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            self.entreprises[cle] = e
        if domaine and not e.domaine:
            e.domaine = domaine
        if motif and motif.value not in e.motifs:
            e.motifs.append(motif.value)
        return e

    def surveiller(self, nom, *, domaine=None, motif: Motif = Motif.MANUEL) -> Entreprise:
        """Ajout manuel : « surveille cette entreprise »."""
        e = self.decouvrir(nom, domaine=domaine, motif=motif, origine="manuel")
        e.etat = Etat.SURVEILLEE
        return e

    def ecarter(self, cle, motif: str):
        e = self.entreprises.get(cle)
        if e:
            e.etat = Etat.ECARTEE
            e.motif_ecart = motif
        return e

    # ------------------------------------------------- depuis le moteur --
    def depuis_attribution(self, opp) -> Entreprise | None:
        """Un titulaire est toujours intéressant : il devra exécuter."""
        if not opp.titulaire:
            return None
        e = self.decouvrir(opp.titulaire, motif=Motif.TITULAIRE,
                           origine=opp.source)
        e.marches_gagnes += 1
        if opp.montant:
            e.montant_gagne += float(opp.montant)
        e.etat = Etat.SURVEILLEE
        return e

    def depuis_opportunite(self, opp) -> Entreprise | None:
        """L'acheteur d'un besoin devient une entreprise connue : il rachètera."""
        nom = opp.acheteur
        if not nom:
            return None
        motif = Motif.CHERCHE_PARTENAIRE if opp.est_signal else Motif.ACHETEUR
        domaine = domaine_de(opp.lien_dossier or opp.plateforme)
        e = self.decouvrir(nom, domaine=domaine, motif=motif, origine=opp.source)
        e.besoins_detectes += 1
        if opp.contact and not e.contact:
            e.contact = opp.contact
        return e

    # ------------------------------------------------------- lecture --
    def a_surveiller(self, limite: int | None = None) -> list[Entreprise]:
        """Celles qui méritent des recherches ciblées, les plus prometteuses
        d'abord : un titulaire récent avant une entreprise vue une fois."""
        candidats = [e for e in self.entreprises.values() if e.interessante()]
        candidats.sort(key=lambda e: (-e.marches_gagnes, -e.besoins_detectes,
                                      e.derniere_visite or ""))
        return candidats[:limite] if limite else candidats

    def rapport(self) -> str:
        L = ["REGISTRE DES ENTREPRISES", "=" * 96, ""]
        if not self.entreprises:
            return "\n".join(L + ["  aucune entreprise découverte — "
                                  "aucune source n'a encore été consultée."])
        for e in self.a_surveiller():
            L.append("  " + e.ligne())
        ecartees = [e for e in self.entreprises.values() if e.etat is Etat.ECARTEE]
        L.append("")
        L.append(f"  {len(self.entreprises)} entreprise(s) · "
                 f"{sum(1 for e in self.entreprises.values() if e.etat is Etat.SURVEILLEE)} "
                 f"surveillée(s) · {len(ecartees)} écartée(s)")
        for e in ecartees[:5]:
            L.append(f"    écartée : {e.nom[:40]} — {e.motif_ecart}")
        return "\n".join(L)
