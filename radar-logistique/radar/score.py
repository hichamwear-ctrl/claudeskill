"""Le score TRIE, il n'écarte pas.

Poids principal : la rareté de la combinaison exigée. Un lot que deux cents
transporteurs peuvent servir vaut moins qu'un lot qui en exige quatre — la
marge est là où la concurrence n'est pas.

Une composante non calculable ne pénalise pas : elle est neutre et signalée.
Pénaliser l'absence de donnée reviendrait à enterrer un bon marché mal renseigné.
"""

from __future__ import annotations

# Exigences qui éliminent réellement des concurrents, et ce qu'elles pèsent.
LIBELLES = {
    "afsca_requis": "AFSCA",
    "licence_transport_requise": "licence de transport",
    "froid_requis": "température dirigée",
    "surface_min_m2": "site de tri",
    "tri_colis_requis": "capacité de tri",
    "reference_segment": "référence similaire",
}

RARETE = {
    "afsca_requis": 30,
    "licence_transport_requise": 22,
    "froid_requis": 20,
    "surface_min_m2": 18,
    "tri_colis_requis": 15,
    "reference_segment": 12,
}


def calculer(exigences, resultat_elig, *, jours_restants=None, montant=None) -> tuple[int, list[str]]:
    """Renvoie (score sur 100, explications lisibles)."""
    explications: list[str] = []

    # 1. Rareté : somme des barrières que l'exploitant franchit.
    franchies = [e for e in exigences if e.code in RARETE]
    brut = sum(RARETE[e.code] for e in franchies)
    rarete = min(brut, 100)
    if franchies:
        noms = ", ".join(LIBELLES.get(e.code, e.code) for e in franchies)
        explications.append(f"barrières franchies ({noms}) : peu de concurrents recevables")
    else:
        explications.append("aucune barrière technique : concurrence probablement large")

    # 2. Correspondance établie contre réserves ouvertes.
    total_pistes = len(resultat_elig.atouts) + len(resultat_elig.reserves)
    adequation = 100 * len(resultat_elig.atouts) / total_pistes if total_pistes else 50
    if resultat_elig.reserves:
        explications.append(f"{len(resultat_elig.reserves)} point(s) à vérifier avant de déposer")

    # 3. Délai : très court pénalise, non renseigné reste neutre.
    if jours_restants is None:
        delai = 50
        explications.append("délai non déterminé — score de délai neutre")
    elif jours_restants < 5:
        delai = 20
        explications.append(f"seulement {jours_restants} j pour monter le dossier")
    elif jours_restants < 12:
        delai = 60
    else:
        delai = 100

    # 4. Montant : neutre si non publié.
    if montant in (None, 0):
        valeur = 50
        explications.append("montant non publié — score de valeur neutre")
    elif montant >= 500_000:
        valeur = 100
    elif montant >= 150_000:
        valeur = 80
    elif montant >= 50_000:
        valeur = 60
    else:
        valeur = 40

    score = round(0.40 * rarete + 0.25 * adequation + 0.20 * delai + 0.15 * valeur)
    return min(score, 100), explications
