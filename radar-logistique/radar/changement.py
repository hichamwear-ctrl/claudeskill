"""Le contenu de cette page a-t-il bougé depuis la dernière lecture ?

Ce module répond à UNE question, et à une seule :

    PREMIÈRE VISITE · INCHANGÉE · MODIFIÉE

Il ne dit RIEN d'autre. En particulier il ne dit pas :

  · qu'il y a une nouvelle opportunité — c'est la chaîne d'analyse qui décide ;
  · que l'état de la procédure a changé — c'est radar/procedure.py ;
  · que le besoin commercial a évolué — c'est le score et la classification.

Un site qui régénère son HTML, change un jeton de session ou déplace une
bannière produit un CONTENU MODIFIÉ sans le moindre changement commercial.
C'est normal, et c'est pour ça que ce module s'arrête là où il s'arrête :
confondre « la page a bougé » et « il y a une affaire » fabriquerait une
alerte commerciale à chaque passage du collecteur.

La mémoire des empreintes vit dans la table `filigrane`, qui existait déjà
dans le schéma et n'était utilisée par rien.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

PREMIERE = "PREMIÈRE VISITE"
INCHANGEE = "INCHANGÉE"
MODIFIEE = "MODIFIÉE"
NON_COMPARABLE = "NON COMPARABLE"     # rien n'a été lu : on ne compare pas

PREFIXE = "page:"                     # l'espace de noms des pages dans filigrane


def empreinte(octets: bytes | None) -> str | None:
    """Sans octets, pas d'empreinte. Surtout pas celle de la chaîne vide, qui
    ferait passer un échec d'accès pour une page devenue vide."""
    if octets is None:
        return None
    return hashlib.sha256(octets).hexdigest()


def _cle(url: str) -> str:
    return PREFIXE + str(url)


def connue(cx, url) -> str | None:
    l = cx.execute("SELECT valeur FROM filigrane WHERE source=?", (_cle(url),)).fetchone()
    return l["valeur"] if l else None


def comparer(cx, url, nouvelle: str | None) -> str:
    """Compare SANS écrire. Lire l'état ne doit pas le modifier."""
    if not nouvelle:
        return NON_COMPARABLE
    ancienne = connue(cx, url)
    if ancienne is None:
        return PREMIERE
    return INCHANGEE if ancienne == nouvelle else MODIFIEE


def retenir(cx, url, nouvelle: str | None) -> str:
    """Compare PUIS mémorise — mais seulement si quelque chose a été lu.

    Une visite en erreur n'écrase jamais l'empreinte valide de la dernière
    lecture réussie : sinon la visite d'après croirait la page modifiée alors
    que c'est notre accès qui avait échoué.
    """
    verdict = comparer(cx, url, nouvelle)
    if verdict is NON_COMPARABLE or verdict == NON_COMPARABLE:
        return NON_COMPARABLE
    cx.execute(
        "INSERT INTO filigrane(source, valeur, maj_le) VALUES(?,?,?)"
        " ON CONFLICT(source) DO UPDATE SET valeur=excluded.valeur,"
        " maj_le=excluded.maj_le WHERE filigrane.gele=0",
        (_cle(url), nouvelle,
         datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return verdict
