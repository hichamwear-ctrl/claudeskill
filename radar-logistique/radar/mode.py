"""DEMO ou RÉEL — jamais confondus.

Après l'épisode des dix fausses opportunités BDA présentées comme un résultat,
la séparation ne peut plus reposer sur une convention.

Ce que ce module garantit RÉELLEMENT : un enregistrement sans preuve de
collecte est REFUSÉ en mode RÉEL. Une fixture n'en porte pas, donc elle ne peut
pas entrer par accident dans la base réelle.

Ce qu'il ne garantit pas, et il faut le dire : quelqu'un qui fabriquerait
délibérément un bloc de collecte complet passerait. La protection vise la
confusion, pas la falsification volontaire.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

CLE_COLLECTE = "_collecte"


class Mode(Enum):
    DEMO = "DEMO"
    REEL = "RÉEL"

    @property
    def base_par_defaut(self) -> str:
        """Deux fichiers distincts : jamais la même base."""
        return "radar-demo.sqlite3" if self is Mode.DEMO else "radar-reel.sqlite3"

    def bandeau(self) -> str:
        if self is Mode.DEMO:
            return ("╔" + "═" * 68 + "╗\n"
                    "║  MODE : DEMO — DONNÉES FICTIVES                                    ║\n"
                    "║  NE PAS UTILISER COMMERCIALEMENT                                   ║\n"
                    "╚" + "═" * 68 + "╝")
        return ("╔" + "═" * 68 + "╗\n"
                "║  MODE : RÉEL — données réellement collectées                        ║\n"
                "╚" + "═" * 68 + "╝")


class CollecteInvalide(Exception):
    """Levée quand un enregistrement prétend au mode RÉEL sans preuve."""


@dataclass
class Collecte:
    """La preuve qu'une ligne vient vraiment d'Internet."""
    source: str
    reference: str          # URL réelle ou identifiant officiel
    collecte_le: str        # horodatage ISO
    empreinte: str          # empreinte du contenu au moment de la collecte

    def en_dict(self) -> dict:
        return {"source": self.source, "reference": self.reference,
                "collecte_le": self.collecte_le, "empreinte": self.empreinte}


def empreinte_contenu(charge) -> str:
    """Empreinte stable du contenu brut, indépendante de l'ordre des clés."""
    texte = json.dumps(charge, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:32]


def estampiller(charge: dict, *, source: str, reference: str) -> dict:
    """Appelé par les COLLECTEURS, au moment où la donnée arrive du réseau.

    C'est le seul endroit qui a le droit de créer une preuve de collecte.
    """
    marque = Collecte(source=source, reference=reference,
                      collecte_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      empreinte=empreinte_contenu(charge))
    return {**charge, CLE_COLLECTE: marque.en_dict()}


def lire_collecte(charge: dict) -> Collecte | None:
    bloc = (charge or {}).get(CLE_COLLECTE)
    if not isinstance(bloc, dict):
        return None
    manquants = [c for c in ("source", "reference", "collecte_le", "empreinte")
                 if not bloc.get(c)]
    if manquants:
        return None
    return Collecte(**{c: bloc[c] for c in
                      ("source", "reference", "collecte_le", "empreinte")})


def verifier(charge: dict, mode: Mode) -> Collecte | None:
    """Contrôle d'entrée. En RÉEL, refuse tout ce qui n'est pas prouvé.

    Le contrôle est double : la preuve doit exister, et l'empreinte doit
    correspondre au contenu — une ligne modifiée après collecte est rejetée.
    """
    if mode is Mode.DEMO:
        return lire_collecte(charge)

    marque = lire_collecte(charge)
    if marque is None:
        raise CollecteInvalide(
            "MODE RÉEL : enregistrement sans preuve de collecte "
            f"(bloc « {CLE_COLLECTE} » absent ou incomplet). "
            "Une donnée de démonstration ne peut pas entrer dans la base réelle.")

    sans_marque = {k: v for k, v in charge.items() if k != CLE_COLLECTE}
    attendue = empreinte_contenu(sans_marque)
    if attendue != marque.empreinte:
        raise CollecteInvalide(
            f"MODE RÉEL : contenu modifié depuis la collecte "
            f"(empreinte {marque.empreinte[:12]} ≠ {attendue[:12]}).")
    return marque
