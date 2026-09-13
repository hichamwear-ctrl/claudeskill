"""Un moteur de recherche de FIXTURE — pour éprouver la chaîne, jamais le marché.

    LES RÉSULTATS QU'IL REND N'ONT JAMAIS ÉTÉ RENDUS PAR UN MOTEUR.

Il existe parce que l'accès aux moteurs réels est fermé et que construire une
chaîne de découverte qu'on ne peut pas exécuter reviendrait à écrire du code
non prouvé. Il répond à une seule question : « la chaîne se comporte-t-elle
correctement quand des résultats arrivent ? »

Il ne répond PAS à : « qu'y a-t-il sur le marché belge ? ». Rien de ce qu'il
produit n'est une mesure.

DEUX VERROUS, ET ILS SONT STRUCTURELS
=====================================

1. `mode` vaut DEMO, et c'est une propriété du moteur — pas un paramètre qu'un
   appelant choisit. `trouvailles.depuis_moteur()` la lit à la source.

2. `rechercher()` REFUSE de s'exécuter en mode RÉEL. Une fixture ne peut pas
   entrer dans la base réelle, exactement comme une ligne sans preuve de
   collecte ne le peut pas depuis l'origine du projet.

AUCUN NOM DE FOURNISSEUR N'EST ÉCRIT ICI
========================================

Les noms des moteurs viennent du FICHIER de fixture, jamais du code. Ce module
ne connaît ni Google, ni Brave, ni aucun autre : il lit un fichier déclaratif,
et c'est tout. La même discipline que pour les adaptateurs de sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .mode import Mode
from .moteurs_recherche import MoteurRecherche, Resultat

# Le fichier doit le déclarer, mot pour mot. Un fichier qui ne dit pas qu'il
# est une fixture n'est pas chargé : on ne devine pas la nature d'une donnée.
MARQUE = "FIXTURE"


class FixtureEnModeReel(Exception):
    """Levée quand une fixture est interrogée pour alimenter la base réelle."""


class FixtureInvalide(ValueError):
    """Fichier illisible, non marqué, ou sans moteur déclaré."""


@dataclass
class MoteurFixture(MoteurRecherche):
    """Rend les résultats déclarés dans un fichier. Respecte le contrat entier.

    `disponible` est vrai : une fixture répond toujours. Cela ne veut pas dire
    qu'un moteur réel répondrait — cela veut dire que le mécanisme peut être
    éprouvé.
    """
    nom: str = "fixture"
    resultats_declares: list = field(default_factory=list)
    origine: str | None = None          # le fichier d'où viennent les données

    # ── le contrat ──
    @property
    def mode(self) -> Mode:
        """DEMO, toujours. Une fixture ne peut pas se déclarer réelle."""
        return Mode.DEMO

    @property
    def disponible(self) -> bool:
        return True

    @property
    def motif_indisponibilite(self) -> str | None:
        return None

    def rechercher(self, requete, mode: Mode = Mode.DEMO) -> list[Resultat]:
        """Les résultats déclarés pour cette requête, dans l'ordre du fichier.

        Le RANG est la position dans cet ordre : c'est une observation sur la
        façon dont la source présente ses résultats, jamais un jugement sur
        leur valeur.

        Une requête sans résultat déclaré rend une liste vide. Ce n'est pas un
        rejet : c'est l'absence de résultat, et elle se mesure.
        """
        if mode is Mode.REEL:
            raise FixtureEnModeReel(
                f"« {self.nom} » est une FIXTURE ({self.origine or 'source inconnue'}). "
                "Ses résultats n'ont jamais été rendus par un moteur de recherche "
                "et ne peuvent pas entrer dans la base réelle.")
        texte = self._texte(requete)
        quand = self._maintenant()
        sortie = []
        for position, d in enumerate(self.resultats_declares, start=1):
            if texte and d.get("requete") and d["requete"] != texte:
                continue
            sortie.append(Resultat(
                titre=d.get("titre", ""), url=d.get("url", ""),
                extrait=d.get("extrait", ""), requete=d.get("requete") or texte,
                fournisseur=self.nom, consulte_le=quand,
                rang=len(sortie) + 1, page_source=d.get("page_source")))
        return sortie

    def etat(self) -> str:
        return (f"{self.nom:<14} FIXTURE — éprouve le mécanisme, "
                "ne mesure aucun marché")


def depuis_fichier(chemin) -> list[MoteurFixture]:
    """Charge UN fichier déclaratif et rend PLUSIEURS moteurs de fixture.

    Plusieurs, parce que l'architecture est multi-sources : éprouver le
    recouvrement entre moteurs exige d'en avoir plus d'un.
    """
    import yaml
    p = Path(chemin)
    if not p.exists():
        raise FixtureInvalide(f"fixture introuvable : {p}")
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:                                       # noqa: BLE001
        raise FixtureInvalide(f"fixture illisible : {e}") from e

    if str(d.get("mode", "")).strip().upper() != MARQUE:
        raise FixtureInvalide(
            f"{p} ne se déclare pas « mode: {MARQUE} ». On ne charge pas un "
            "fichier dont la nature n'est pas écrite : une donnée fabriquée "
            "doit dire qu'elle l'est.")

    moteurs = d.get("moteurs") or []
    if not moteurs:
        raise FixtureInvalide(f"{p} ne déclare aucun moteur")
    return [MoteurFixture(nom=str(m.get("nom") or "fixture"),
                          resultats_declares=list(m.get("resultats") or []),
                          origine=str(p))
            for m in moteurs]


def registre(chemin):
    """Les moteurs de fixture, dans un Registre — comme des moteurs normaux.

    L'ordre est celui du fichier. C'est un ordre d'ESSAI, pas un classement :
    aucune source n'a d'avantage, ici pas plus qu'ailleurs.
    """
    from .moteurs_recherche import Registre
    return Registre(depuis_fichier(chemin))
