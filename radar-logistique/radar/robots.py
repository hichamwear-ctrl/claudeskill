"""robots.txt — la condition d'entrée de toute source en navigation web.

Aucune page n'est lue avant que ce fichier ait été consulté et respecté. Une
règle qui interdit un chemin l'interdit : il n'y a pas de contournement, et
l'absence de robots.txt ne vaut pas autorisation tacite d'aller vite.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

DELAI_PAR_DEFAUT = 2.5      # secondes entre deux requêtes, même si rien n'est imposé


@dataclass
class Regles:
    autorise: list[str] = field(default_factory=list)
    interdit: list[str] = field(default_factory=list)
    delai: float = DELAI_PAR_DEFAUT
    lu: bool = False
    erreur: str | None = None

    def chemin_autorise(self, url: str) -> tuple[bool, str]:
        """La règle la plus SPÉCIFIQUE gagne, comme le veut la convention."""
        chemin = urllib.parse.urlparse(url).path or "/"
        meilleure_i = max((len(r) for r in self.interdit if chemin.startswith(r)), default=-1)
        meilleure_a = max((len(r) for r in self.autorise if chemin.startswith(r)), default=-1)
        if meilleure_i < 0:
            return True, "aucune interdiction ne couvre ce chemin"
        if meilleure_a >= meilleure_i:
            return True, f"autorisé explicitement (règle de {meilleure_a} caractères)"
        return False, f"interdit par robots.txt (règle « {chemin[:meilleure_i]} »)"


def analyser(texte: str, agent: str = "*") -> Regles:
    """Retient le groupe de l'agent demandé, sinon le groupe générique."""
    groupes: dict[str, Regles] = {}
    courants: list[str] = []
    attend_regles = True     # True = la prochaine ligne User-agent ouvre un groupe
    for brut in texte.splitlines():
        ligne = brut.split("#", 1)[0].strip()
        if not ligne or ":" not in ligne:
            continue
        cle, valeur = (p.strip() for p in ligne.split(":", 1))
        cle = cle.lower()
        if cle == "user-agent":
            # Des User-agent consécutifs partagent le même groupe de règles.
            if attend_regles:
                courants = [valeur.lower()]
                attend_regles = False
            else:
                courants.append(valeur.lower())
            groupes.setdefault(valeur.lower(), Regles(lu=True))
        elif courants:
            attend_regles = True
            for c in courants:
                g = groupes[c]
                if cle == "disallow" and valeur:
                    g.interdit.append(valeur)
                elif cle == "allow" and valeur:
                    g.autorise.append(valeur)
                elif cle == "crawl-delay":
                    try:
                        g.delai = max(float(valeur), DELAI_PAR_DEFAUT)
                    except ValueError:
                        pass
    agent = agent.lower()
    return groupes.get(agent) or groupes.get("*") or Regles(lu=True)


def recuperer(base_url: str, agent: str = "*", ouvrir=None) -> Regles:
    """Va lire le robots.txt. En cas d'échec, on ne suppose PAS l'autorisation :
    on renvoie des règles marquées non lues, et l'appelant doit s'abstenir."""
    parties = urllib.parse.urlparse(base_url)
    url = f"{parties.scheme}://{parties.netloc}/robots.txt"
    ouvrir = ouvrir or urllib.request.urlopen
    try:
        with ouvrir(url, timeout=20) as r:
            return analyser(r.read().decode("utf-8", "replace"), agent)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Pas de robots.txt : rien n'est interdit, mais on reste lent.
            return Regles(lu=True, delai=DELAI_PAR_DEFAUT)
        return Regles(lu=False, erreur=f"HTTP {e.code}")
    except Exception as e:                                   # noqa: BLE001
        return Regles(lu=False, erreur=str(e))
