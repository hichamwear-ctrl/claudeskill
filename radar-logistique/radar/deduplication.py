"""Une même opportunité paraît souvent sur plusieurs sources.

Un avis européen sort sur TED et au BDA ; un signal peut être vu par deux
veilles. On garde UNE opportunité et on retient toutes ses provenances.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


def _plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def empreinte(opp) -> str:
    """Empreinte métier : acheteur + intitulé + échéance + montant + CPV principal.

    Volontairement indépendante de l'identifiant de source — c'est ce qui permet
    de reconnaître le même marché vu ailleurs. Le montant et le CPV servent de
    départage : sans eux, deux marchés réellement distincts d'un même acheteur,
    publiés le même jour sous un intitulé voisin, fusionnaient à tort.
    """
    parts = [
        _plat(opp.acheteur),
        _plat(opp.intitule)[:120],
        str(opp.echeance_brute or ""),
        f"{float(opp.montant):.0f}" if opp.montant else "",
        (sorted(str(c) for c in (opp.cpv or []))[:1] or [""])[0],
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def fusionner(existante, nouvelle):
    """Complète les trous de l'existante avec la nouvelle. N'écrase jamais une
    valeur déjà présente : la première source qui a publié fait foi."""
    for champ in ("acheteur", "contact", "montant", "duree_mois", "lien_dossier",
                  "lien_depot", "plateforme", "texte", "secteur_acheteur"):
        if not getattr(existante, champ, None) and getattr(nouvelle, champ, None):
            setattr(existante, champ, getattr(nouvelle, champ))
    for champ in ("pays_collecte", "pays_livraison", "cpv"):
        fusion = list(dict.fromkeys(getattr(existante, champ, []) + getattr(nouvelle, champ, [])))
        setattr(existante, champ, fusion)
    return existante
