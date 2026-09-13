"""La collecte directe — aller lire une page qu'on connaît déjà.

    URL connue → robots.txt → récupération → octets réels

AUCUN MOTEUR DE RECHERCHE N'INTERVIENT ICI. C'est le point de la règle :

    Google et les autres moteurs servent à DÉCOUVRIR ce que nous ne
    connaissons pas. Une source déjà connue s'analyse DIRECTEMENT.

Si Google, Brave, Exa et Tavily sont tous indisponibles, ce module fonctionne
exactement pareil. Il ne les importe pas, il ne les interroge pas, il ne sait
même pas qu'ils existent.

CE QU'IL NE FAIT JAMAIS :

  · il ne rend jamais de contenu qu'il n'a pas reçu ;
  · il ne transforme jamais une erreur d'accès en « page vide » ni en
    « aucune opportunité » — ERREUR et NON DISPONIBLE disent que nous n'avons
    pas pu lire, pas que la page est sans intérêt ;
  · il ne passe jamais outre un robots.txt, et un robots.txt ILLISIBLE ne vaut
    pas autorisation : dans le doute, on s'abstient.
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from . import robots
from .pages import Acces

AGENT = "RadarLogistique/1.0 (+contact via l'exploitant)"
DELAI_MINIMUM = robots.DELAI_PAR_DEFAUT
TAILLE_MAX = 8 * 1024 * 1024          # au-delà, on ne charge pas en mémoire
TEMPS_MAX = 30                        # secondes


@dataclass
class Collecte:
    """Le résultat d'UNE tentative d'accès. Le contenu et l'état d'accès sont
    deux choses distinctes et ne se déduisent jamais l'un de l'autre."""
    url: str
    acces: Acces
    octets: bytes | None = None
    http: int | None = None
    motif: str = ""
    consulte_le: str = ""
    provenance: str = "collecte directe"

    @property
    def lue(self) -> bool:
        return self.acces is Acces.CONSULTEE and self.octets is not None

    @property
    def empreinte(self) -> str | None:
        """L'empreinte des octets REÇUS. Sans octets, pas d'empreinte — et
        surtout pas l'empreinte de la chaîne vide, qui ferait passer un échec
        pour une page devenue vide."""
        if self.octets is None:
            return None
        return hashlib.sha256(self.octets).hexdigest()

    def ligne(self) -> str:
        taille = f"{len(self.octets)} o" if self.octets is not None else "—"
        code = f"HTTP {self.http}" if self.http else "—"
        return f"{self.acces.value:<17} {code:<10} {taille:>10}  {self.url[:48]}" \
               + (f"  · {self.motif}" if self.motif else "")


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Politesse:
    """Le délai entre deux requêtes vers le MÊME hôte, jamais sous le plancher.

    L'horloge et le sommeil sont injectables : les tests ne dorment pas."""

    def __init__(self, horloge=time.monotonic, dormir=time.sleep):
        self.horloge, self.dormir = horloge, dormir
        self.derniere: dict[str, float] = {}

    def attendre(self, hote: str, delai: float):
        delai = max(float(delai or 0), DELAI_MINIMUM)
        precedente = self.derniere.get(hote)
        maintenant = self.horloge()
        if precedente is not None:
            reste = delai - (maintenant - precedente)
            if reste > 0:
                self.dormir(reste)
        self.derniere[hote] = self.horloge()


def recuperer(url: str, *, agent: str = AGENT, ouvrir=None, politesse=None,
              regles_robots=None) -> Collecte:
    """Va chercher UNE page connue. Rend toujours une Collecte, jamais une
    exception : un échec est une information, pas un arrêt du radar.

    `ouvrir` est injectable — les tests n'atteignent aucun réseau.
    """
    import urllib.parse
    quand = _maintenant()
    hote = urllib.parse.urlparse(url).netloc
    if not hote:
        return Collecte(url=url, acces=Acces.NON_DISPONIBLE, consulte_le=quand,
                        motif="URL sans hôte — rien à consulter")

    # ── 1. robots.txt, AVANT toute lecture. Pas de contournement. ──
    regles = regles_robots
    if regles is None:
        regles = robots.recuperer(url, agent=agent.split("/")[0].lower(), ouvrir=ouvrir)
    if not regles.lu:
        return Collecte(url=url, acces=Acces.NON_DISPONIBLE, consulte_le=quand,
                        motif=f"robots.txt illisible ({regles.erreur}) — "
                              "ne pas savoir n'autorise pas")
    autorise, regle = regles.chemin_autorise(url)
    if not autorise:
        return Collecte(url=url, acces=Acces.NON_DISPONIBLE, consulte_le=quand,
                        motif=f"interdit par robots.txt ({regle}) — aucun contournement")

    # ── 2. le délai imposé, jamais moins que le plancher ──
    (politesse or Politesse()).attendre(hote, regles.delai)

    # ── 3. la récupération réelle ──
    ouvrir = ouvrir or urllib.request.urlopen
    requete = urllib.request.Request(url, headers={"User-Agent": agent,
                                                   "Accept": "text/html,*/*"})
    try:
        with ouvrir(requete, timeout=TEMPS_MAX) as r:
            octets = r.read(TAILLE_MAX + 1)
            code = getattr(r, "status", None) or getattr(r, "code", None) or 200
    except urllib.error.HTTPError as e:
        # Un 404 est une réponse du serveur, pas une preuve d'absence de besoin.
        return Collecte(url=url, acces=Acces.ERREUR, http=e.code, consulte_le=_maintenant(),
                        motif=f"HTTP {e.code} — la page n'a pas été lue")
    except urllib.error.URLError as e:
        return Collecte(url=url, acces=Acces.ERREUR, consulte_le=_maintenant(),
                        motif=f"accès impossible : {e.reason} — "
                              "ce que contient la page reste INCONNU")
    except Exception as e:                                       # noqa: BLE001
        return Collecte(url=url, acces=Acces.ERREUR, consulte_le=_maintenant(),
                        motif=f"accès impossible : {e} — "
                              "ce que contient la page reste INCONNU")

    if len(octets) > TAILLE_MAX:
        return Collecte(url=url, acces=Acces.ERREUR, http=code, consulte_le=_maintenant(),
                        motif=f"réponse au-delà de {TAILLE_MAX} octets — non chargée")
    return Collecte(url=url, acces=Acces.CONSULTEE, octets=octets, http=code,
                    consulte_le=_maintenant(),
                    motif=f"{len(octets)} octets reçus")
