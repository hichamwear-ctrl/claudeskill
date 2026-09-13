"""LA PORTE D'ENTRÉE — par où contacter réellement ce prospect.

Une opportunité sans porte d'entrée n'est pas exploitable : le commercial sait
QUI a un besoin, et pas comment lui parler.

MESURÉ LE 2026-09-13, sur les deux prospects réels du 2026-09-12 :

    Colis Privé  →  CONTACT  donnees-personnelles@colisprive.com
    DHL          →  CONTACT  AUCUN

Le premier est l'adresse du délégué à la protection des données : juridiquement
correcte, commercialement inutile. Le second est un cul-de-sac apparent. Or les
deux pages portent un formulaire de candidature — 16 champs et 47 champs. Sur
deux prospects sur deux, la porte d'entrée réelle était manquée.

────────────────────────────────────────────────────────────────────────────
CE QUE CE MODULE NE FAIT PAS, ET POURQUOI
────────────────────────────────────────────────────────────────────────────

Il est INERTE. Il décrit, il ne décide pas.

  · il n'entre ni dans l'état, ni dans le score, ni dans le CA, ni dans la
    nature, ni dans l'activité, ni dans la classification ;
  · il n'alimente PAS `lien_depot`. Ce champ nourrit `depot_organise` dans
    `procedure.py`, donc la LECTURE D'ÉTAT : un formulaire de candidature
    privé y ferait naître une « procédure » qui n'existe pas. Un formulaire
    est une PORTE, pas un guichet de dépôt d'offre.

Une porte d'entrée ne rend pas un besoin postulable. Elle dit seulement par où
frapper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

# Un champ de saisie dont le type sert à autre chose qu'à décrire un candidat.
TYPES_IGNORES = frozenset({"hidden", "submit", "button", "image", "reset", "search"})

# Ce qu'un formulaire de recherche porte, et qu'une candidature ne porte pas.
INDICES_RECHERCHE = ("search", "recherche", "zoek", "s=", "q=")

# En dessous, ce n'est pas une candidature : c'est une inscription à une
# newsletter ou une barre de recherche.
CHAMPS_MINIMUM = 3

FORMULAIRE = "FORMULAIRE"
EMAIL = "EMAIL"
TELEPHONE = "TÉLÉPHONE"
PAGE = "PAGE PARTENAIRE"
A_VERIFIER = "À VÉRIFIER"

MOTIF_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class Porte:
    """Ce qui a été CONSTATÉ dans la page. Aucune valeur n'est déduite."""
    type: str = ""                       # FORMULAIRE · EMAIL · TÉLÉPHONE · …
    certitude: str = ""                  # OBSERVÉE · À VÉRIFIER
    lien: str | None = None
    champs_a_remplir: int = 0
    informations_demandees: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    telephones: list = field(default_factory=list)
    provenance: str = ""                 # d'où vient ce constat

    @property
    def existe(self) -> bool:
        return bool(self.type)

    def en_lignes(self) -> list[str]:
        """Les lignes de fiche. Vide si rien n'a été observé : on n'écrit pas
        « aucune porte » là où on n'a simplement pas regardé."""
        if not self.existe:
            return []
        tete = f"PORTE D'ENTRÉE {self.type}"
        if self.certitude == A_VERIFIER:
            tete += "  — À VÉRIFIER"
        L = [tete]
        if self.champs_a_remplir:
            L.append(f"  {self.champs_a_remplir} champs à remplir")
        if self.lien:
            L.append(f"  → {self.lien}")
        if self.informations_demandees:
            L.append("  ils demandent : "
                     + " · ".join(self.informations_demandees[:8]))
        if self.emails:
            L.append("  e-mail : " + ", ".join(self.emails[:3]))
        if self.telephones:
            L.append("  téléphone : " + ", ".join(self.telephones[:2]))
        if self.provenance:
            L.append(f"  observé dans : {self.provenance}")
        return L

    def en_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class _Sonde(HTMLParser):
    """Compte ce qui est là. Ne juge rien."""

    def __init__(self):
        super().__init__()
        self.formulaires: list[dict] = []
        self._pile: list[dict] = []
        self.champs_hors_form = 0
        self.mailto: list[str] = []
        self.tel: list[str] = []

    def handle_starttag(self, balise, attrs):
        a = dict(attrs)
        if balise == "form":
            f = {"action": a.get("action"), "champs": 0, "libelles": []}
            self.formulaires.append(f)
            self._pile.append(f)
            return
        if balise in ("input", "textarea", "select"):
            t = (a.get("type") or ("textarea" if balise == "textarea" else "text")).lower()
            if t in TYPES_IGNORES:
                return
            etiquette = (a.get("placeholder") or a.get("name") or a.get("id") or "").strip()
            if self._pile:
                self._pile[-1]["champs"] += 1
                if etiquette:
                    self._pile[-1]["libelles"].append(etiquette)
            else:
                self.champs_hors_form += 1
            return
        if balise == "a":
            h = a.get("href", "")
            if h.startswith("mailto:"):
                self.mailto.append(h[7:].split("?")[0])
            elif h.startswith("tel:"):
                self.tel.append(h[4:])

    def handle_endtag(self, balise):
        if balise == "form" and self._pile:
            self._pile.pop()


def _est_une_recherche(f: dict) -> bool:
    if f["champs"] > 2:
        return False
    signature = " ".join([str(f.get("action") or "")] + f["libelles"]).lower()
    return any(i in signature for i in INDICES_RECHERCHE)


def lire(html: str, url: str = "") -> Porte:
    """Constate la porte d'entrée d'une page HTML. Ne conclut rien d'autre."""
    if not html:
        return Porte()
    s = _Sonde()
    try:
        s.feed(html)
    except Exception:                      # une page malformée reste lisible
        pass

    candidatures = [f for f in s.formulaires
                    if f["champs"] >= CHAMPS_MINIMUM and not _est_une_recherche(f)]
    total_champs = sum(f["champs"] for f in s.formulaires) + s.champs_hors_form
    emails = sorted(set(MOTIF_EMAIL.findall(html)))

    if candidatures:
        # Une balise <form> avec ses champs : c'est une porte, constatée.
        meilleur = max(candidatures, key=lambda f: f["champs"])
        action = next((f["action"] for f in candidatures if f["action"]), None)
        return Porte(
            type=FORMULAIRE, certitude="OBSERVÉE",
            lien=(urljoin(url, action) if (action and url) else action) or url or None,
            champs_a_remplir=meilleur["champs"],
            informations_demandees=meilleur["libelles"][:12],
            emails=s.mailto or emails, telephones=s.tel,
            provenance="balise <form> de la page")

    if total_champs >= CHAMPS_MINIMUM:
        # Des champs de saisie sans <form> autour. Ce PEUT être un formulaire
        # construit en JavaScript — DHL, 47 champs, zéro balise — ou seulement
        # une barre de recherche et un login — pypi.org, 6 champs.
        #
        # Mesuré le 2026-09-13 : 16 · 47 · 6 champs sur trois pages réelles.
        # Trois points ne font pas un seuil. Décider « au-dessus de 8, c'est
        # une candidature » serait ajuster une règle sur le corpus qui l'a
        # inspirée — l'erreur déjà payée deux fois sur ce projet. On ne
        # tranche donc pas : on rapporte le nombre, et on le dit incertain.
        return Porte(
            type=FORMULAIRE, certitude=A_VERIFIER, lien=url or None,
            champs_a_remplir=total_champs,
            emails=s.mailto or emails, telephones=s.tel,
            provenance="champs de saisie sans balise <form>")

    if s.mailto or emails:
        return Porte(type=EMAIL, certitude="OBSERVÉE",
                     emails=s.mailto or emails, telephones=s.tel,
                     provenance="lien mailto:" if s.mailto else "adresse écrite dans la page")

    if s.tel:
        return Porte(type=TELEPHONE, certitude="OBSERVÉE", telephones=s.tel,
                     provenance="lien tel:")

    return Porte()


def depuis_dict(d) -> Porte:
    """Reconstruit une Porte transportée par une charge d'adaptateur."""
    if isinstance(d, Porte):
        return d
    if not isinstance(d, dict):
        return Porte()
    connus = {k: v for k, v in d.items() if k in Porte.__dataclass_fields__}
    return Porte(**connus)
