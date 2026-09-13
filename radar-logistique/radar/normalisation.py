"""Du contenu réel d'une page connue à une opportunité analysable.

    COLLECTE DIRECTE → CONTENU RÉEL → ADAPTATEUR → OPPORTUNITÉ → CHAÎNE

C'est le raccord qui manquait entre le circuit SOURCE CONNUE et le moteur
d'analyse. Il ne contient AUCUNE règle nouvelle : il applique exactement les
mêmes étapes déclarées que la mesure de référence sur page réelle — le profil
`sources/page_web.yaml`, le lecteur `radar/page.py`, le détecteur de porte
d'entrée, l'adaptateur, puis `traiter()`.

AUCUN MOTEUR DE RECHERCHE N'INTERVIENT. Ce module n'importe ni Google, ni
Brave, ni aucun autre : il part d'octets déjà reçus.

CE QU'IL NE FAIT PAS
====================

Il ne décide pas qu'il y a une affaire. Il met la page en état d'être jugée,
et c'est la chaîne — rôle, ontologie, état, nature, fiabilité, capacités,
score, classification — qui juge. Aucune de ces règles n'est touchée ici.

Il ne complète aucun champ absent. Ce que la page ne dit pas reste INCONNU.
"""

from __future__ import annotations

from . import circuit as mod_circuit, porte
from .adaptateur import Adaptateur, vers_opportunite
from .mode import estampiller
from .page import lire as lire_page

# Le texte remis au moteur sémantique est borné, comme dans la mesure de
# référence : au-delà, on ne lit pas mieux, on ralentit seulement.
TEXTE_MAX = 20000

# Les champs que l'on transporte tels que le lecteur les a trouvés. La liste
# est celle de la mesure de référence — elle n'est pas élargie ici.
CHAMPS_TRANSPORTES = ("intitule", "acheteur", "objet", "contact_email")


def charge_de_page(html: str, url: str, profil: dict) -> tuple[dict, object]:
    """La charge brute remise à l'adaptateur, et la lecture qui l'a produite.

    Elle ne contient QUE ce qui a été réellement lu dans la page.
    """
    lec = lire_page(html, profil)
    charge = {"url": url,
              **{c: v for c, v in lec.champs.items() if c in CHAMPS_TRANSPORTES}}
    # Le texte visible entier : ce n'est pas un champ « rempli », c'est la
    # page elle-même, matière du moteur sémantique.
    charge["texte"] = lec.texte[:TEXTE_MAX]
    # Le MÊME texte, porté par son emplacement. Seules les exclusions le
    # lisent, pour distinguer ce qui caractérise le besoin de ce qui décrit
    # seulement le site.
    charge["segments"] = [{"texte": t, "origine": o} for t, o in lec.segments]
    # Les blocs non fusionnés : deux fragments ne se combinent que dans un
    # même bloc. Sans eux, la lecture retombe sur les phrases.
    charge["blocs"] = [{"texte": t, "zone": z} for t, z in lec.blocs]
    # La <meta description> n'est pas du texte visible et n'a donc pas de
    # zone. Elle décrit pourtant le sujet de la page : elle entre comme
    # segment caractérisant, jamais comme métadonnée négligeable.
    if lec.champs.get("objet"):
        charge["segments"].append({"texte": lec.champs["objet"],
                                   "origine": "description de la page"})
    # PAR OÙ CONTACTER. Constaté sur le HTML réel, transporté tel quel.
    # N'entre dans AUCUNE décision : ni état, ni score, ni nature, ni classement.
    charge["porte_entree"] = porte.lire(html, url).en_dict()
    return charge, lec


def depuis_collecte(collecte, profil: dict, *, source: str = "entreprise",
                    circuit: str = mod_circuit.CONNUE, consulte_le=None):
    """Une page réellement collectée → une Opportunite prête pour `traiter()`.

    Rend `(opportunite, lecture)`, ou `(None, None)` si rien n'a été lu :
    une page non consultée ne produit pas d'opportunité vide, et surtout pas
    une opportunité « sans besoin ». Elle ne produit RIEN, et ce qu'elle
    contient reste INCONNU.
    """
    if collecte is None or not getattr(collecte, "lue", False):
        return None, None
    html = collecte.octets.decode("utf-8", errors="replace")
    charge, lec = charge_de_page(html, collecte.url, profil)
    # LA PREUVE DE COLLECTE. Elle est apposée ici parce que c'est ici que la
    # donnée arrive du réseau — le mode RÉEL la contrôle et refuse sans elle.
    charge = estampiller(charge, source=source, reference=collecte.url)
    opp = vers_opportunite(
        Adaptateur.depuis_config(profil), charge, source,
        {"secteur": profil.get("secteur_par_defaut"),
         "consulte_le": consulte_le or getattr(collecte, "consulte_le", None),
         # Le CHEMIN par lequel l'information est arrivée. Traçabilité et
         # métriques uniquement : il n'entre dans aucun score.
         "circuit": circuit})
    return opp, lec
