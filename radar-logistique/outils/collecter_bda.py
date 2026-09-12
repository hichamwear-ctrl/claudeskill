#!/usr/bin/env python3
"""Collecteur BDA — à lancer depuis une machine ayant un accès réseau.

    python3 outils/collecter_bda.py --pages 5 --sortie bda-brut.json
    python  -m radar.cli recenser --source bda --echantillon bda-brut.json

Deux règles non négociables, appliquées avant toute lecture :

  1. le robots.txt est consulté ; un chemin interdit N'EST PAS lu ;
  2. le délai entre requêtes est celui du robots.txt, jamais moins que 2,5 s.

Si le robots.txt est illisible, le script s'ARRÊTE : ne pas savoir n'autorise
pas. Et il ne prétend jamais avoir réussi — un échec sort avec un code non nul.

────────────────────────────────────────────────────────────────────────────
LA LISTE N'EST PAS L'AVIS
────────────────────────────────────────────────────────────────────────────

Ce collecteur ne lisait que les LIGNES DE LISTE : un identifiant, un titre, un
lien. `sources/bda.yaml` déclare pourtant depuis toujours une section
`detail:` — objet, montant, durée, guichet de dépôt, documents, contact, lots
— et aucun code ne la lisait. Une collecte de listing reproduit exactement ce
que les mesures des 5 et 12 septembre ont montré : des titres, 24/100, aucun
CA, aucun dépôt possible. Un titre est un capteur de découverte, pas une
opportunité attaquable.

Chaque avis retenu est donc OUVERT, une requête par avis, au même rythme et
sous le même robots.txt. `--sans-detail` permet de s'en passer pour un simple
recensement de clés.

────────────────────────────────────────────────────────────────────────────
CE QUE CE SCRIPT NE PRÉTEND PAS
────────────────────────────────────────────────────────────────────────────

Les sélecteurs de `sources/bda.yaml` portent `verifie: false` : ils n'ont
jamais rencontré la vraie page. Tant que c'est le cas, ce script écrit sa
sortie MAIS sort en code 6 — « collecté, non vérifié ». Une collecte dont les
sélecteurs n'ont jamais été mesurés n'est pas une collecte valide, et un code
de sortie nul le laisserait croire.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                    # noqa: E402

from radar import robots                                       # noqa: E402
from radar.extraction import analyser, extraire                # noqa: E402
from radar.extraction import _valeur as valeur_selon           # noqa: E402
from radar.mode import estampiller                             # noqa: E402

CODE_NON_VERIFIE = 6


def lire(url: str, agent: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": agent, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:800]
    except urllib.error.URLError as e:
        return 0, f"réseau injoignable : {e.reason}"


def cle_de(ligne: dict) -> str:
    """La clé de déduplication : le lien de l'avis, sinon l'identifiant.

    L'ancienne version comparait les dictionnaires entiers, en reconstruisant
    toute la liste à chaque ligne — mille lignes faisaient un million de
    comparaisons, et deux lignes identiques à un espace près passaient pour
    différentes.
    """
    for cle in ("lien_avis", "identifiant", "intitule"):
        v = str(ligne.get(cle) or "").strip()
        if v:
            return v
    return json.dumps(ligne, sort_keys=True)


def archiver(html: str, url: str, dossier: Path) -> dict:
    """La page, telle qu'elle est arrivée. C'est la seule preuve qui tienne.

    Sans elle, un sélecteur faux se corrige de mémoire. Avec elle, il se
    corrige sur pièces — et la mesure est rejouable sans réseau.
    """
    octets = html.encode("utf-8")
    empreinte = hashlib.sha256(octets).hexdigest()
    dossier.mkdir(parents=True, exist_ok=True)
    quand = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fichier = dossier / f"{quand[:10]}-bda-{empreinte[:12]}.html"
    if not fichier.exists():
        fichier.write_bytes(octets)
    return {"url": url, "collecte_le": quand, "octets": len(octets),
            "sha256": empreinte, "fichier": fichier.name}


def lire_detail(html: str, cfg: dict, base_url: str) -> dict:
    """Les champs de la FICHE de l'avis, déclarés dans `detail.champs`.

    Aucun champ n'est fabriqué : un sélecteur qui ne répond pas ne produit
    pas de clé, et le recensement le verra à 0 %.
    """
    champs = ((cfg.get("detail") or {}).get("champs")) or {}
    racine = analyser(html)
    sortie = {}
    for nom, spec in champs.items():
        v = valeur_selon(racine, spec, base_url)
        if v not in (None, "", []):
            sortie[nom] = v
    return sortie


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description="Collecte des avis du BDA")
    p.add_argument("--pages", type=int, default=5)
    p.add_argument("--recherche", default="transport")
    p.add_argument("--sortie", default="bda-brut.json")
    p.add_argument("--html-brut", default="bda-pages",
                   help="dossier où déposer le HTML collecté")
    p.add_argument("--sans-detail", action="store_true",
                   help="ne pas ouvrir la fiche de chaque avis (recensement seul)")
    p.add_argument("--max-detail", type=int, default=50,
                   help="nombre maximum de fiches ouvertes")
    a = p.parse_args(argv)

    cfg = yaml.safe_load((RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8"))
    nav = cfg["navigation"]
    agent = nav["agent"]
    archives = Path(a.html_brut)

    # ── 1. robots.txt, avant toute lecture ──
    regles = robots.recuperer(nav["base_url"], agent=agent.split("/")[0].lower())
    if not regles.lu:
        print(f"robots.txt illisible ({regles.erreur}) — arrêt.", file=sys.stderr)
        print("Ne pas savoir n'autorise pas : aucune page ne sera lue.", file=sys.stderr)
        return 2
    autorise, motif = regles.chemin_autorise(nav["url_recherche"])
    print(f"robots.txt : {motif} · délai imposé {regles.delai:g} s")
    if not autorise:
        print("Chemin interdit par robots.txt — arrêt, sans contournement.", file=sys.stderr)
        return 3
    delai = max(regles.delai, nav.get("delai_minimum_s", 2.5))

    # ── 2. la liste, page par page ──
    tout, vus, pages_brutes, preuves = [], set(), [], []
    for page in range(1, min(a.pages, nav.get("pages_max", 20)) + 1):
        params = urllib.parse.urlencode({nav.get("parametre_recherche", "q"): a.recherche,
                                         nav.get("parametre_page", "page"): page})
        url = f"{nav['url_recherche']}?{params}"
        statut, contenu = lire(url, agent)

        if statut != 200:
            print(f"\nÉCHEC page {page} — code {statut}", file=sys.stderr)
            print(contenu[:400], file=sys.stderr)
            if not tout:
                return 4
            break

        pages_brutes.append((page, contenu))
        preuves.append(archiver(contenu, url, archives))
        lignes = extraire(contenu, cfg, base_url=nav["base_url"])
        if not lignes:
            print(f"page {page} : reçue ({len(contenu)} octets) mais AUCUNE ligne extraite.")
            print("   → les sélecteurs de sources/bda.yaml ne correspondent pas à la page.")
            break

        neufs = []
        for l in lignes:
            cle = cle_de(l)
            if cle in vus:
                continue
            vus.add(cle)
            neufs.append(l)
        tout += neufs
        print(f"page {page:>3} : {len(lignes):>4} lignes, {len(neufs):>4} nouvelles "
              f"(total {len(tout)})")
        if not neufs:
            print("fin de pagination.")
            break
        time.sleep(delai)                       # jamais après la DERNIÈRE lecture

    if not tout:
        for page, contenu in pages_brutes:
            (archives / f"page-{page}.html").write_text(contenu, encoding="utf-8")
        print(f"\nAucune ligne extraite. {len(pages_brutes)} page(s) enregistrée(s) "
              f"dans {archives}/", file=sys.stderr)
        print("Mesure-les :  python3 outils/bac_a_sable_bda.py --html <fichier>",
              file=sys.stderr)
        print("Puis corrige sources/bda.yaml SUR PIÈCES, jamais dans le code.",
              file=sys.stderr)
        return 5

    # ── 3. la FICHE de chaque avis : c'est là que vit l'opportunité ──
    lien_champ = (cfg.get("detail") or {}).get("suivre_le_lien", "lien_avis")
    ouvertes = echecs = 0
    if not a.sans_detail and cfg.get("detail"):
        for ligne in tout[:a.max_detail]:
            lien = ligne.get(lien_champ)
            if not lien:
                continue
            lien = urllib.parse.urljoin(nav["base_url"], str(lien))
            permis, _ = regles.chemin_autorise(lien)
            if not permis:
                echecs += 1
                continue
            time.sleep(delai)
            statut, html = lire(lien, agent)
            if statut != 200:
                echecs += 1
                continue
            preuves.append(archiver(html, lien, archives))
            detail = lire_detail(html, cfg, nav["base_url"])
            if detail:
                ligne.update(detail)
                ouvertes += 1
            else:
                echecs += 1
        print(f"\nfiches ouvertes : {ouvertes} · illisibles ou refusées : {echecs}")
        lisibles = ouvertes / max(1, ouvertes + echecs)
        print(f"taux de fiches réellement lisibles : {lisibles:.0%}")

    # ── 4. sortie ──
    estampilles = [estampiller(l, source="bda",
                               reference=str(l.get(lien_champ) or l.get("identifiant") or ""))
                   for l in tout]
    Path(a.sortie).write_text(json.dumps(estampilles, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    (archives / "preuves.json").write_text(
        json.dumps(preuves, ensure_ascii=False, indent=1), encoding="utf-8")

    cles = sorted({k for l in estampilles for k in l})
    print(f"\n{len(estampilles)} avis écrits dans {a.sortie}")
    print(f"{len(preuves)} page(s) archivée(s) et hachée(s) dans {archives}/")
    print(f"champs réellement extraits : {', '.join(cles)}")
    declares = list(nav["champs"]) + list(((cfg.get("detail") or {}).get("champs")) or {})
    manquants = [c for c in declares if c not in cles]
    if manquants:
        print(f"champs DÉCLARÉS mais jamais trouvés : {', '.join(manquants)}")
        print("→ sélecteurs à corriger dans sources/bda.yaml")

    print(f"\nÉtape suivante :\n"
          f"  python -m radar.cli recenser --source bda --echantillon {a.sortie}")

    # ── 5. une collecte non vérifiée n'est pas une collecte valide ──
    if not cfg.get("verifie"):
        print("\n" + "─" * 70, file=sys.stderr)
        print("COLLECTE NON VÉRIFIÉE — sources/bda.yaml porte `verifie: false`.",
              file=sys.stderr)
        print("Les sélecteurs n'ont jamais rencontré la vraie page. Ce qui est",
              file=sys.stderr)
        print("écrit ci-dessus est ce qu'ils ont SU lire, pas ce que la page",
              file=sys.stderr)
        print("contient. Lance `recenser`, corrige les champs à 0 %, puis passe",
              file=sys.stderr)
        print("`verifie: true` — et relance. Code de sortie 6.", file=sys.stderr)
        print("─" * 70, file=sys.stderr)
        return CODE_NON_VERIFIE
    return 0


if __name__ == "__main__":
    sys.exit(principal())
