#!/usr/bin/env python3
"""Collecteur TED — à lancer depuis une machine ayant un accès réseau.

Ce script ne sait RIEN de la forme des réponses, et c'est volontaire : il
enregistre le brut tel quel. C'est `radar.cli recenser` qui mesure ensuite
quelles clés existent réellement. Deviner les noms de champs ici reproduirait
exactement le bug qui a coûté le plus cher sur le projet précédent.

    python3 outils/collecter_ted.py --pages 20 --sortie reponses-ted.json
    python -m radar.cli recenser --source ted --echantillon reponses-ted.json
    python -m radar.cli sonder   --source ted --entree     reponses-ted.json

Zéro dépendance : bibliothèque standard uniquement.

AVERTISSEMENT — l'URL et le format de requête ci-dessous n'ont PAS pu être
vérifiés : aucun accès réseau depuis l'environnement de développement. Si
l'appel échoue, le script affiche la réponse exacte du serveur pour que tu
corriges l'endpoint ou la requête. Il ne prétendra jamais avoir réussi.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# À corriger si l'API a changé — le script te dira quoi.
ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
UA = "radar-logistique/1.0 (collecte de marchés publics; contact: exploitant)"

# Familles CPV du transport et de la logistique. Volontairement large :
# on filtrera après mesure, pas avant.
CPV = ["60000000", "60100000", "60160000", "60170000", "60180000",
       "63100000", "63120000", "64120000", "79620000"]


def construire_requete(page: int, taille: int, jours: int, pays: list[str]) -> dict:
    cpv = " OR ".join(f"classification-cpv={c}" for c in CPV)
    zone = " OR ".join(f"buyer-country={p}" for p in pays) if pays else ""
    morceaux = [f"({cpv})"]
    if zone:
        morceaux.append(f"({zone})")
    morceaux.append(f"publication-date>=today(-{jours})")
    return {"query": " AND ".join(morceaux), "page": page, "limit": taille,
            "scope": "ALL", "paginationMode": "PAGE_NUMBER"}


def appeler(corps: dict, delai: float) -> tuple[int, object]:
    donnees = json.dumps(corps).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=donnees, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        return e.code, detail
    except urllib.error.URLError as e:
        return 0, f"réseau injoignable : {e.reason}"
    finally:
        time.sleep(delai)


def extraire_lot(charge) -> list:
    """Trouve la liste d'avis sans supposer son nom : on prend la plus longue
    liste de dictionnaires présente dans la réponse."""
    if isinstance(charge, list):
        return charge
    if not isinstance(charge, dict):
        return []
    candidats = []
    for cle, valeur in charge.items():
        if isinstance(valeur, list) and valeur and isinstance(valeur[0], dict):
            candidats.append((len(valeur), cle, valeur))
    if not candidats:
        return []
    candidats.sort(reverse=True)
    return candidats[0][2]


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description="Collecte de réponses TED brutes")
    p.add_argument("--pages", type=int, default=10)
    p.add_argument("--taille", type=int, default=100, help="avis par page")
    p.add_argument("--jours", type=int, default=365, help="profondeur d'historique")
    p.add_argument("--pays", nargs="*", default=["BEL", "NLD", "LUX", "DEU", "FRA"])
    p.add_argument("--delai", type=float, default=2.5, help="pause entre requêtes, en secondes")
    p.add_argument("--sortie", default="reponses-ted.json")
    a = p.parse_args(argv)

    tout, vus = [], set()
    for page in range(1, a.pages + 1):
        statut, charge = appeler(construire_requete(page, a.taille, a.jours, a.pays), a.delai)

        if statut != 200:
            print(f"\nÉCHEC page {page} — code {statut}", file=sys.stderr)
            print(f"Réponse du serveur :\n{charge}\n", file=sys.stderr)
            print("Corrige ENDPOINT ou construire_requete() en haut de ce fichier.",
                  file=sys.stderr)
            if not tout:
                return 2                      # rien collecté : on échoue franchement
            print(f"{len(tout)} avis déjà collectés — ils sont enregistrés.", file=sys.stderr)
            break

        lot = extraire_lot(charge)
        if not lot:
            cles = list(charge)[:12] if isinstance(charge, dict) else type(charge).__name__
            print(f"\nPage {page} : réponse reçue mais aucune liste d'avis reconnue.",
                  file=sys.stderr)
            print(f"Clés de premier niveau : {cles}", file=sys.stderr)
            print("Adapte extraire_lot() si la liste porte un nom inattendu.", file=sys.stderr)
            break

        neufs = 0
        for avis in lot:
            empreinte = json.dumps(avis, sort_keys=True)[:400]
            if empreinte not in vus:
                vus.add(empreinte)
                tout.append(avis)
                neufs += 1
        print(f"page {page:>3} : {len(lot):>4} avis reçus, {neufs:>4} nouveaux "
              f"(total {len(tout)})")
        if neufs == 0 or len(lot) < a.taille:
            print("fin de pagination atteinte.")
            break

    if not tout:
        print("Aucun avis collecté — rien n'est écrit.", file=sys.stderr)
        return 2

    with open(a.sortie, "w", encoding="utf-8") as f:
        json.dump(tout, f, ensure_ascii=False, indent=1)

    cles = sorted({k for avis in tout for k in avis})
    print(f"\n{len(tout)} avis écrits dans {a.sortie}")
    print(f"{len(cles)} clés distinctes observées au premier niveau :")
    print("  " + ", ".join(cles[:25]) + (" …" if len(cles) > 25 else ""))
    print(f"\nÉtape suivante :\n"
          f"  python -m radar.cli recenser --source ted --echantillon {a.sortie}\n"
          f"  python -m radar.cli sonder   --source ted --entree     {a.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
