"""🟣 À CONSTRUIRE — le test de cohérence économique et opérationnelle.

Un métier que l'entreprise ne pratique pas encore n'est pas un rejet. Mais une
formation offerte ne suffit pas non plus : il faut un vrai chemin.

Six conditions, TOUTES obligatoires. Et une règle qui ne se négocie pas :
une formation technique rend une compétence accessible, elle n'efface jamais
une obligation légale préalable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .activite import normaliser

# Preuve écrite qu'un accompagnement est proposé. Sans elle, pas de 🟣 :
# le moteur ne suppose jamais qu'une formation existe.
MARQUES_FORMATION = [
    "formation complete", "formation assuree", "formation prise en charge",
    "nous formons", "formation des techniciens", "formation du personnel",
    "accompagnement au demarrage", "accompagnement technique", "formation fournie",
    "opleiding voorzien", "opleiding wordt voorzien",
    "full training provided", "training provided", "training is provided",
]

# Qualifications qui DOIVENT être détenues avant d'intervenir : aucune
# formation commerciale ne les remplace.
MARQUES_OBLIGATION_LEGALE = [
    "agrement", "agreement obligatoire", "habilitation", "certification obligatoire",
    "licence obligatoire", "autorisation prealable", "certificat legal",
    "enregistrement obligatoire", "qualification reglementaire", "vca", "bosec",
    "erkenning", "wettelijke vergunning", "mandatory licence", "mandatory accreditation",
]

# Métiers de terrain où les actifs de l'entreprise servent réellement.
# Ce n'est PAS une liste blanche de métiers : c'est le test du levier.
LEVIERS = {
    "vehicule": ["intervention sur site", "deplacement", "itinerant", "chez le client",
                 "sur site", "depannage", "maintenance", "installation", "pose",
                 "montage", "livraison", "enlevement", "transport"],
    "depot": ["stockage", "pieces detachees", "atelier", "preparation", "materiel",
              "outillage", "entreposage"],
    "equipe": ["technicien", "equipe", "operateur", "personnel", "main d oeuvre",
               "ouvrier", "monteur"],
}

# Ce qui n'a aucun rapport avec les moyens de l'entreprise, même avec formation.
HORS_PERIMETRE = [
    "comptabilite", "expertise comptable", "avocat", "juridique", "conseil juridique",
    "audit financier", "assurance", "courtage", "developpement logiciel",
    "programmation", "marketing", "communication", "traduction", "architecture",
    "medecine", "soins infirmiers", "enseignement", "formation professionnelle",
]


@dataclass
class Verdict:
    eligible: bool = False
    conditions: dict[str, bool] = field(default_factory=dict)
    leviers: list[str] = field(default_factory=list)
    formation: str | None = None
    obligation_legale: str | None = None
    manques: list[str] = field(default_factory=list)
    motif: str = ""

    def echecs(self) -> list[str]:
        return [c for c, ok in self.conditions.items() if not ok]


def _trouve(plat: str, marques) -> str | None:
    for m in marques:
        if f" {m} " in plat or plat.strip().startswith(m):
            return m
    return None


def _duree_formation_jours(texte: str) -> int | None:
    """Lit une durée annoncée. Renvoie None si elle n'est pas écrite — jamais
    une valeur supposée."""
    plat = normaliser(texte)
    for motif, facteur in ((r"(\d+)\s*semaines?", 7), (r"(\d+)\s*mois", 30),
                           (r"(\d+)\s*jours?", 1)):
        m = re.search(motif, plat)
        if m:
            return int(m.group(1)) * facteur
    return None


def evaluer(*, texte: str, familles_reconnues, jours_avant_demarrage=None,
            duree_mois=None, cadence=None) -> Verdict:
    """Applique les six conditions. Toutes doivent passer."""
    plat = normaliser(f"{texte}")
    v = Verdict()

    # 0. Hors périmètre : aucun actif ne peut servir, quelle que soit la formation.
    hors = _trouve(plat, HORS_PERIMETRE)
    if hors:
        v.motif = f"hors périmètre : « {hors} » n'utilise aucun moyen de l'entreprise"
        v.conditions = {"levier d'actif": False, "activité de terrain": False}
        return v

    # 1. Levier d'actif — au moins un moyen de l'entreprise sert réellement.
    for actif, mots in LEVIERS.items():
        trouve = _trouve(plat, mots)
        if trouve:
            v.leviers.append(f"{actif} (« {trouve} »)")
    v.conditions["levier d'actif"] = bool(v.leviers)

    # 2. Activité de terrain ou exécutable depuis le dépôt.
    v.conditions["activité de terrain"] = any(
        a in ("vehicule", "depot") for a in
        [l.split(" (")[0] for l in v.leviers])

    # 3. Formation réellement mentionnée dans la source.
    v.formation = _trouve(plat, MARQUES_FORMATION)
    v.conditions["formation mentionnée"] = bool(v.formation)
    if not v.formation:
        v.manques.append("aucune formation mentionnée dans la source")

    # 4. Délai suffisant avant le démarrage.
    duree_f = _duree_formation_jours(texte)
    if jours_avant_demarrage is None:
        v.conditions["délai suffisant"] = False
        v.manques.append("date de démarrage NON PUBLIÉE — délai non vérifiable")
    elif duree_f is None:
        # Durée de formation non publiée : on ne l'invente pas. Passable si le
        # délai est confortable, à vérifier sinon.
        v.conditions["délai suffisant"] = jours_avant_demarrage >= 60
        if not v.conditions["délai suffisant"]:
            v.manques.append(
                f"durée de formation NON PUBLIÉE et seulement {jours_avant_demarrage} j "
                "avant le démarrage")
    else:
        v.conditions["délai suffisant"] = jours_avant_demarrage >= duree_f * 1.5
        if not v.conditions["délai suffisant"]:
            v.manques.append(
                f"formation de {duree_f} j pour {jours_avant_demarrage} j disponibles")

    # 5. Aucune obligation légale préalable bloquante.
    v.obligation_legale = _trouve(plat, MARQUES_OBLIGATION_LEGALE)
    v.conditions["pas d'obligation légale préalable"] = v.obligation_legale is None
    if v.obligation_legale:
        v.manques.append(
            f"« {v.obligation_legale} » exigé avant intervention — une formation "
            "technique ne le remplace pas")

    # 6. Cohérence économique : récurrent ou assez long pour amortir.
    recurrent = (cadence or "").lower() in ("quotidienne", "hebdomadaire", "mensuelle")
    assez_long = bool(duree_mois and duree_mois >= 12)
    v.conditions["cohérence économique"] = recurrent or assez_long
    if not v.conditions["cohérence économique"]:
        v.manques.append("durée ou récurrence insuffisante pour amortir une montée en compétence")

    v.eligible = all(v.conditions.values())
    if v.eligible:
        v.motif = (f"métier nouveau accessible — formation « {v.formation} », "
                   f"leviers : {', '.join(v.leviers)}")
    else:
        v.motif = "conditions non réunies : " + ", ".join(v.echecs())
    return v
