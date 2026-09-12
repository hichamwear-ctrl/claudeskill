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
from .portee import Portee, positions

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

    # Une relation NON ÉTABLIE n'est ni un oui ni un non : c'est une question.
    incertain: bool = False

    def echecs(self) -> list[str]:
        return [c for c, ok in self.conditions.items() if not ok]


def _ou(plat: str, expression: str):
    """La position d'une expression, ou None. Sert à savoir OÙ, pas SI."""
    p = positions(plat, expression)
    if p:
        return p[0]
    return plat.find(expression) if plat.strip().startswith(expression) else None


def _trouve(plat: str, marques) -> str | None:
    for m in marques:
        if f" {m} " in plat or plat.strip().startswith(m):
            return m
    return None


def _duree_formation_jours(texte: str, portee=None, autour: int | None = None) -> int | None:
    """Lit la durée ANNONCÉE POUR LA FORMATION. None si elle n'est pas écrite.

    Cherchée dans l'unité de discours où la formation est mentionnée, et
    nulle part ailleurs. Mesuré sans cette borne : « Contrat de 36 mois
    reconductible », lu 1 200 caractères plus loin, devenait « formation de
    1 080 jours » — une durée de contrat présentée au commercial comme une
    durée de formation, et le chemin 🟣 À CONSTRUIRE fermé pour rien.
    """
    plat = normaliser(texte)
    if portee is not None and autour is not None:
        unite = portee.unite_de(autour)
        if unite is not None:
            plat = portee.plat[unite.debut:unite.fin]
        else:
            plat = portee.plat[max(0, autour - portee.fenetre):autour + portee.fenetre]
    for motif, facteur in ((r"(\d+)\s*semaines?", 7), (r"(\d+)\s*mois", 30),
                           (r"(\d+)\s*jours?", 1)):
        m = re.search(motif, plat)
        if m:
            return int(m.group(1)) * facteur
    return None


def evaluer(*, texte: str, familles_reconnues, jours_avant_demarrage=None,
            duree_mois=None, cadence=None, blocs=None, portee=None) -> Verdict:
    """Applique les six conditions. Toutes doivent passer."""
    plat = normaliser(f"{texte}")
    portee = portee if portee is not None else Portee.construire(texte, blocs)
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
    # OÙ les moyens ont été reconnus : une montée en compétence n'est crédible
    # que si la formation porte sur LA prestation qui mobilise ces moyens.
    positions_leviers = [q for q in (_ou(plat, l.split("« ")[1].rstrip(" »)"))
                                     for l in v.leviers) if q is not None]

    # 2. Activité de terrain ou exécutable depuis le dépôt.
    v.conditions["activité de terrain"] = any(
        a in ("vehicule", "depot") for a in
        [l.split(" (")[0] for l in v.leviers])

    # 3. Formation réellement mentionnée dans la source.
    v.formation = _trouve(plat, MARQUES_FORMATION)
    v.conditions["formation mentionnée"] = bool(v.formation)
    if not v.formation:
        v.manques.append("aucune formation mentionnée dans la source")

    # 3 bis. LA FORMATION DOIT PORTER SUR CES MOYENS-LÀ.
    #
    # Mesuré : un levier reconnu dans un bloc et une formation mentionnée
    # 1 400 caractères plus loin donnaient le même verdict que s'ils étaient
    # dans la même phrase. Deux faits sans rapport suffisaient à ouvrir le
    # chemin 🟣. S'ils sont ailleurs, on ne rejette pas — on dit que la
    # relation n'est pas établie.
    p_formation = positions(plat, v.formation)[:1] if v.formation else []
    if v.formation and positions_leviers:
        # `meme_ensemble` et non `meme_unite` : la relation est de l'ordre du
        # paragraphe, pas de la phrase.
        liee = any(portee.meme_ensemble(p_formation[0], q) for q in positions_leviers) \
            if p_formation else False
        v.conditions["formation liée aux moyens"] = liee
        if not liee:
            v.incertain = True
            v.manques.append(
                f"« {v.formation} » et « {v.leviers[0]} » ont été lus dans "
                f"{portee.situer(p_formation[0])} et {portee.situer(positions_leviers[0])} "
                f"— rien ne dit que la formation porte sur ces moyens")

    # 4. Délai suffisant avant le démarrage.
    duree_f = _duree_formation_jours(
        texte, portee, p_formation[0] if p_formation else None)
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
    # Une obligation légale ne bloque que si elle porte sur CETTE prestation.
    # Lue dans un bloc sans rapport — une mention générale, un autre marché —
    # elle reste affichée mais ne condamne rien : on ne rejette pas sur une
    # exigence venue arbitrairement d'ailleurs.
    p_oblig = _ou(plat, v.obligation_legale) if v.obligation_legale else None
    porte_ici = bool(v.obligation_legale) and (
        p_oblig is None
        or any(portee.meme_ensemble(p_oblig, q)
               for q in positions_leviers + list(p_formation)))
    v.conditions["pas d'obligation légale préalable"] = not porte_ici
    if v.obligation_legale and porte_ici:
        v.manques.append(
            f"« {v.obligation_legale} » exigé avant intervention — une formation "
            "technique ne le remplace pas")
    elif v.obligation_legale:
        v.incertain = True
        v.manques.append(
            f"« {v.obligation_legale} » observé en {portee.situer(p_oblig)} — "
            f"hors de la prestation décrite, non retenu comme bloquant : à vérifier")

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
