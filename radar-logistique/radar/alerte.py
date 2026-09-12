"""LE TRANSPORT DES ALERTES — ce qui sort réellement du radar.

La file d'envoi existait depuis longtemps : durable, idempotente, avec reprise
des interrompus et trois issues distinctes. Il lui manquait la dernière chose,
et c'était la plus importante — un moyen de sortir. `radar notifier` répondait
« aucun transport configuré » : le radar qualifiait des opportunités que
personne ne recevait jamais.

Ce module écrit un FICHIER. C'est délibérément le transport le plus pauvre
qui soit, pour trois raisons :

  · il ne demande aucun réseau, aucun compte, aucune clé — il marche le jour
    où on le branche ;
  · une fiche déposée dans un dossier est récupérable par n'importe quoi : un
    commercial qui l'ouvre, une synchronisation, un script qui la poste ;
  · il respecte `envoi.vider(transport)` sans rien y changer, donc le jour où
    un courriel ou un webhook existe, il se substitue en une ligne.

────────────────────────────────────────────────────────────────────────────
IDEMPOTENCE — la propriété qui décide si l'outil est utilisable
────────────────────────────────────────────────────────────────────────────

`vider` peut être relancé après une interruption, et la file peut contenir un
envoi dont on ne sait pas s'il est parti. Écrire deux fois la même alerte
reviendrait à faire travailler un commercial deux fois sur la même affaire.

Le nom du fichier est donc DÉRIVÉ DU CONTENU : les douze premiers caractères
du SHA-256 du corps. Avant d'écrire, on cherche ce même sceau n'importe où
dans l'arborescence. S'il existe déjà, on ne réécrit pas — et ce n'est pas une
erreur : le message était déjà sorti.

Le dossier porte la date, le fichier porte le sceau et un titre lisible. Un
commercial y lit « ce que le radar a trouvé le 12 septembre », pas un dump.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from .base import maintenant

SCEAU = 12          # caractères de l'empreinte retenus dans le nom du fichier


def sceau_de(corps: str) -> str:
    """L'empreinte du message. Deux corps identiques → un seul fichier."""
    return hashlib.sha256((corps or "").encode("utf-8")).hexdigest()[:SCEAU]


def _lisible(texte: str, taille: int = 60) -> str:
    """Un morceau de titre utilisable comme nom de fichier, sans accent."""
    plat = unicodedata.normalize("NFKD", texte or "")
    plat = "".join(c for c in plat if not unicodedata.combining(c))
    plat = re.sub(r"[^A-Za-z0-9]+", "-", plat).strip("-").lower()
    return plat[:taille] or "alerte"


def _titre_du_corps(corps: str) -> str:
    """La première ligne de la fiche EST son titre : « 🟢 DIRECT — … »."""
    for ligne in (corps or "").splitlines():
        if ligne.strip():
            return ligne.strip()
    return "alerte"


class TransportFichier:
    """Dépose chaque alerte dans un dossier daté. Rien d'autre.

    Appelable : `envoi.vider(cx, TransportFichier(dossier))`.
    """

    def __init__(self, dossier, horloge=maintenant):
        self.dossier = Path(dossier)
        self.horloge = horloge
        self.ecrits: list[Path] = []
        self.deja_sortis: list[Path] = []

    # ------------------------------------------------------------------ API
    def __call__(self, corps: str) -> Path:
        """Écrit l'alerte, ou constate qu'elle est déjà sortie.

        Ne lève jamais pour un doublon : un message déjà délivré n'est pas un
        échec. Une erreur d'écriture, elle, remonte — `vider` la rangera en
        « échec », réessayable.
        """
        sceau = sceau_de(corps)
        existant = self.retrouver(sceau)
        if existant is not None:
            self.deja_sortis.append(existant)
            return existant

        quand = self.horloge()
        jour = str(quand)[:10]
        cible = self.dossier / jour
        cible.mkdir(parents=True, exist_ok=True)
        titre = _titre_du_corps(corps)
        chemin = cible / f"{sceau}--{_lisible(titre)}.txt"

        # Écriture atomique : un fichier temporaire puis un renommage. Une
        # interruption ne laisse jamais une fiche à moitié écrite dans le
        # dossier que le commercial consulte.
        provisoire = chemin.with_suffix(".txt.partiel")
        provisoire.write_text(self._enveloppe(corps, quand, sceau), encoding="utf-8")
        provisoire.replace(chemin)
        self.ecrits.append(chemin)
        return chemin

    def retrouver(self, sceau: str):
        """Ce sceau est-il déjà sorti, quel que soit le jour ?"""
        if not self.dossier.exists():
            return None
        for chemin in sorted(self.dossier.glob(f"*/{sceau}--*.txt")):
            return chemin
        return None

    # ------------------------------------------------------------- rendu --
    @staticmethod
    def _enveloppe(corps: str, quand, sceau: str) -> str:
        """L'en-tête minimal qui rend la fiche autonome : quand, et quoi.

        Le corps n'est pas retouché — c'est la fiche commerciale telle que le
        moteur l'a produite, avec ses preuves et ses réserves.
        """
        barre = "═" * 70
        return (f"{barre}\n"
                f"  RADAR COMMERCIAL — ALERTE\n"
                f"  émise le {quand}\n"
                f"  sceau    {sceau}   (le même message ne ressort jamais deux fois)\n"
                f"{barre}\n\n{corps.rstrip()}\n")
