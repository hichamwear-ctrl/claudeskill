"""SEARCH_PROVIDER → RÉSULTATS WEB → NORMALISATION → ANALYSE

Le métier ne connaît aucun moteur en particulier. Il demande « cherche ceci »
et reçoit des résultats normalisés. Google, Brave ou un moteur futur se
branchent ici sans qu'une ligne du moteur commercial change.

Sans clé, un fournisseur est NON DISPONIBLE et ne simule jamais de recherche.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone


class RechercheIndisponible(Exception):
    """Aucune recherche ne PEUT avoir lieu. Jamais silencieuse, jamais
    remplacée par des résultats fabriqués."""


@dataclass
class Resultat:
    """Un résultat web, normalisé — quel que soit le moteur qui l'a produit."""
    titre: str
    url: str
    extrait: str
    requete: str
    fournisseur: str
    consulte_le: str | None = None

    def en_charge(self) -> dict:
        """Le résultat, sous la forme que lit `sources/google.yaml`.

        C'est le pont qui manquait : un résultat de recherche n'était jusqu'ici
        qu'un moyen de DÉCOUVRIR des entreprises, il ne devenait jamais une
        opportunité. Un besoin exprimé sur une page web est pourtant une
        occasion de chiffre d'affaires au même titre qu'un marché publié — et
        souvent plus tôt.

        Rien n'est fabriqué ici : ni acheteur, ni montant, ni échéance. Ce que
        la page ne dit pas reste absent, et le moteur le qualifiera en
        HYPOTHÈSE plutôt qu'en fait.
        """
        return {"url": self.url, "titre": self.titre, "extrait": self.extrait,
                "requete": self.requete, "consulte_le": self.consulte_le,
                "fournisseur": self.fournisseur}


class MoteurRecherche:
    """Contrat commun. Un nouveau moteur n'a que ces trois choses à fournir."""

    nom: str = "?"

    @property
    def disponible(self) -> bool:
        raise NotImplementedError

    @property
    def motif_indisponibilite(self) -> str | None:
        raise NotImplementedError

    def rechercher(self, requete) -> list[Resultat]:
        raise NotImplementedError

    # ------------------------------------------------------------ commun --
    def _texte(self, requete) -> str:
        return getattr(requete, "texte", str(requete))

    def _maintenant(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def etat(self) -> str:
        if self.disponible:
            return f"{self.nom:<10} DISPONIBLE"
        return f"{self.nom:<10} NON DISPONIBLE — {self.motif_indisponibilite}"


def _appel_json(url: str, entetes: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=entetes or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise RechercheIndisponible(f"HTTP {e.code} — {detail}") from e
    except urllib.error.URLError as e:
        raise RechercheIndisponible(f"réseau injoignable : {e.reason}") from e


# ─────────────────────────────────────────────────────────────────── Google
@dataclass
class Google(MoteurRecherche):
    """Google Programmable Search Engine — API officielle uniquement.

    Le scraping des pages de résultats est exclu : c'est contraire aux
    conditions d'utilisation, et il n'y a pas de contournement.
    """
    cle_api: str | None = None
    moteur_id: str | None = None
    resultats_par_requete: int = 10
    nom: str = "google"
    point_acces: str = "https://www.googleapis.com/customsearch/v1"

    @property
    def disponible(self) -> bool:
        return bool(self.cle_api and self.moteur_id)

    @property
    def motif_indisponibilite(self) -> str | None:
        if self.disponible:
            return None
        manque = [n for n, v in (("clé API", self.cle_api),
                                 ("identifiant de moteur", self.moteur_id)) if not v]
        return "CLÉ ABSENTE — " + " et ".join(manque) + " non fournis"

    def rechercher(self, requete) -> list[Resultat]:
        if not self.disponible:
            raise RechercheIndisponible(self.motif_indisponibilite)
        texte = self._texte(requete)
        params = urllib.parse.urlencode({
            "key": self.cle_api, "cx": self.moteur_id, "q": texte,
            "num": min(self.resultats_par_requete, 10)})
        charge = _appel_json(f"{self.point_acces}?{params}")
        quand = self._maintenant()
        return [Resultat(titre=i.get("title", ""), url=i.get("link", ""),
                         extrait=i.get("snippet", ""), requete=texte,
                         fournisseur=self.nom, consulte_le=quand)
                for i in charge.get("items", [])]


# ──────────────────────────────────────────────────────────────────── Brave
@dataclass
class Brave(MoteurRecherche):
    """Brave Search API — alternative officielle, même contrat."""
    cle_api: str | None = None
    resultats_par_requete: int = 10
    nom: str = "brave"
    point_acces: str = "https://api.search.brave.com/res/v1/web/search"

    @property
    def disponible(self) -> bool:
        return bool(self.cle_api)

    @property
    def motif_indisponibilite(self) -> str | None:
        return None if self.disponible else "CLÉ ABSENTE — clé API non fournie"

    def rechercher(self, requete) -> list[Resultat]:
        if not self.disponible:
            raise RechercheIndisponible(self.motif_indisponibilite)
        texte = self._texte(requete)
        params = urllib.parse.urlencode({"q": texte, "count": self.resultats_par_requete})
        charge = _appel_json(f"{self.point_acces}?{params}",
                             {"Accept": "application/json",
                              "X-Subscription-Token": self.cle_api})
        quand = self._maintenant()
        return [Resultat(titre=i.get("title", ""), url=i.get("url", ""),
                         extrait=i.get("description", ""), requete=texte,
                         fournisseur=self.nom, consulte_le=quand)
                for i in (charge.get("web", {}) or {}).get("results", [])]


# ─────────────────────────────────────────────────────────────────── choix
@dataclass
class Registre:
    """Les moteurs déclarés, dans l'ordre de préférence."""
    moteurs: list = field(default_factory=list)

    def disponible(self) -> MoteurRecherche | None:
        for m in self.moteurs:
            if m.disponible:
                return m
        return None

    def rapport(self) -> str:
        L = ["MOTEURS DE RECHERCHE", "-" * 60]
        for m in self.moteurs:
            L.append("  " + m.etat())
        if self.disponible() is None:
            L.append("")
            L.append("  Aucun moteur disponible : la découverte web ne peut pas")
            L.append("  démarrer. Le radar fonctionne quand même sur ses autres sources.")
        return "\n".join(L)


def depuis_environnement(env: dict | None = None) -> Registre:
    """Lit les clés dans l'environnement. Absentes : les moteurs existent quand
    même et disent pourquoi ils ne peuvent rien faire."""
    import os
    env = env if env is not None else os.environ
    return Registre([
        Google(cle_api=env.get("GOOGLE_API_KEY") or None,
               moteur_id=env.get("GOOGLE_CSE_ID") or None),
        Brave(cle_api=env.get("BRAVE_API_KEY") or None),
    ])
