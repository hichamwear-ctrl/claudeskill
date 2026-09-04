"""OBSERVÉ RÉELLEMENT · INTERPRÉTÉ · DÉDUIT · INCONNU.

Quatre niveaux, et un seul principe : **le niveau n'est pas déclaré, il est
mesuré**.

Un champ n'est OBSERVÉ que si sa valeur se retrouve *littéralement* dans les
octets bruts de la page collectée. Le journal vérifie ; si la valeur n'y est
pas, il refuse le niveau demandé et rétrograde en INTERPRÉTÉ, en écrivant
pourquoi. C'est la différence entre « j'affirme que je l'ai lu » et « voici
l'extrait, à cette position, dans le fichier conservé ».

Les quatre niveaux, et ce qu'ils engagent :

    OBSERVÉ RÉELLEMENT  la page contient ces mots. Vérifiable dans le fichier
                        brut conservé, avec la position exacte.
    INTERPRÉTÉ          une règle sémantique a conclu à partir de mots
                        observés. La conclusion est à moi ; les mots ne le
                        sont pas. L'extrait qui a servi est conservé.
    DÉDUIT              calculé à partir d'autres champs, sans support textuel
                        direct. Un score, une distance, une catégorie.
    INCONNU             rien dans la page ne permet de répondre. Ce n'est ni
                        zéro, ni faux, ni absent : c'est non mesuré.

INCONNU n'est pas un échec du radar. C'est le seul résultat honnête quand la
page ne dit rien — et c'est une information commerciale à part entière, parce
qu'elle désigne la prochaine question à poser.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


class Niveau(Enum):
    OBSERVE = "OBSERVÉ RÉELLEMENT"
    OBSERVE_BALISAGE = "OBSERVÉ DANS LE BALISAGE"
    INTERPRETE = "INTERPRÉTÉ"
    DEDUIT = "DÉDUIT"
    INCONNU = "INCONNU"

    @property
    def marque(self) -> str:
        return {"OBSERVÉ RÉELLEMENT": "◉", "OBSERVÉ DANS LE BALISAGE": "◎",
                "INTERPRÉTÉ": "◐", "DÉDUIT": "◔", "INCONNU": "○"}[self.value]


ORDRE = [Niveau.OBSERVE, Niveau.OBSERVE_BALISAGE, Niveau.INTERPRETE,
         Niveau.DEDUIT, Niveau.INCONNU]


def normaliser(texte: str) -> str:
    """Minuscules, accents retirés, espaces réduits — pour COMPARER, jamais
    pour afficher. Ce qui s'affiche reste ce que la page a écrit."""
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texte).strip().lower()


@dataclass
class Constat:
    """Un champ, sa valeur, son niveau — et la preuve du niveau."""
    champ: str
    valeur: object
    niveau: Niveau
    extrait: str = ""          # ce que la page dit, mot pour mot
    position: int | None = None    # où, dans le texte normalisé de la page
    regle: str = ""            # quelle règle a conclu (INTERPRÉTÉ / DÉDUIT)
    question: str = ""         # ce qu'il faudrait demander (INCONNU)
    retrograde: str = ""       # pourquoi le niveau demandé a été refusé

    @property
    def affichage(self) -> str:
        if self.niveau is Niveau.INCONNU:
            return "INCONNU"
        v = self.valeur
        if isinstance(v, (list, tuple)):
            return ", ".join(str(x) for x in v) if v else "INCONNU"
        return str(v)

    def ligne(self, largeur: int = 22) -> str:
        base = f"{self.niveau.marque} {self.champ:<{largeur}} {self.affichage}"
        if self.niveau is Niveau.OBSERVE and self.extrait:
            base += f"\n    └─ page, car. {self.position} : « {self.extrait} »"
        elif self.niveau is Niveau.OBSERVE_BALISAGE:
            base += f"\n    └─ balisage, car. {self.position} : « {self.extrait} »"
            base += "\n    └─ ⚠ invisible pour un lecteur humain de la page"
        elif self.niveau is Niveau.INTERPRETE:
            if self.extrait:
                base += f"\n    └─ lu : « {self.extrait} »"
            if self.regle:
                base += f"\n    └─ règle : {self.regle}"
        elif self.niveau is Niveau.DEDUIT and self.regle:
            base += f"\n    └─ calculé : {self.regle}"
        elif self.niveau is Niveau.INCONNU and self.question:
            base += f"\n    └─ à demander : {self.question}"
        if self.retrograde:
            base += f"\n    └─ ⚠ {self.retrograde}"
        return base


class Journal:
    """Tient le registre des constats pour UNE page, et vérifie les niveaux.

    Le journal détient le texte brut. C'est ce qui lui permet de contredire
    l'appelant : `observer()` n'est pas une déclaration, c'est une demande.
    """

    def __init__(self, texte_brut: str, source_brute: str = ""):
        # Deux corpus, et la distinction compte. Le TEXTE VISIBLE est ce qu'un
        # humain lit sur la page. Le BALISAGE contient en plus les attributs :
        # href, content d'un <meta>, lang. Une adresse tirée d'un href est
        # bien dans la page — elle n'est pas dans ce qu'on y lit. Confondre
        # les deux faisait dire au journal « ne figure pas dans la page » à
        # propos d'une valeur qui y figurait : un reproche faux, découvert en
        # mesurant une vraie page.
        self.brut = texte_brut or ""
        self.plat = normaliser(self.brut)
        self.source = source_brute or ""
        self.plat_source = normaliser(self.source) if source_brute else ""
        self.constats: list[Constat] = []

    # ------------------------------------------------------- vérification --
    def _situer(self, valeur) -> tuple[int | None, str]:
        """Cherche la valeur dans la page. Rend sa position et l'extrait réel.

        La recherche se fait sur le texte normalisé ; l'extrait rendu vient du
        texte NORMALISÉ lui aussi, parce que les positions ne correspondent
        plus dans le brut. Ce qui compte est la présence, pas la typographie.
        """
        aiguille = normaliser(valeur)
        if not aiguille:
            return None, ""
        i = self.plat.find(aiguille)
        if i < 0:
            return None, ""
        debut = max(0, i - 40)
        fin = min(len(self.plat), i + len(aiguille) + 40)
        extrait = self.plat[debut:fin].strip()
        if debut > 0:
            extrait = "…" + extrait
        if fin < len(self.plat):
            extrait += "…"
        return i, extrait

    def contient(self, fragment: str) -> bool:
        f = normaliser(fragment)
        return bool(f) and f in self.plat

    # ---------------------------------------------------------- écriture --
    def observer(self, champ: str, valeur, *, tolerer_absence: bool = False) -> Constat:
        """Demande le niveau OBSERVÉ. Accordé seulement si la page le porte."""
        if valeur in (None, "", [], {}):
            return self.inconnu(champ)
        cible = valeur[0] if isinstance(valeur, (list, tuple)) and valeur else valeur
        position, extrait = self._situer(cible)
        if position is None and self.plat_source:
            # Seconde chance : la valeur est peut-être dans un attribut.
            i = self.plat_source.find(normaliser(cible))
            if i >= 0:
                debut, fin = max(0, i - 30), min(len(self.plat_source),
                                                 i + len(normaliser(cible)) + 30)
                c = Constat(champ, valeur, Niveau.OBSERVE_BALISAGE, position=i,
                            extrait=self.plat_source[debut:fin].strip(),
                            regle="présent dans le balisage (attribut), "
                                  "absent du texte visible")
                self.constats.append(c)
                return c
        if position is None:
            # Le refus est le cœur du dispositif : un champ que l'adaptateur a
            # produit mais que la page ne contient pas n'est pas une lecture,
            # c'est une reconstruction. On le dit.
            c = Constat(champ, valeur, Niveau.INTERPRETE,
                        regle="valeur produite par l'adaptateur",
                        retrograde=("demandé OBSERVÉ, refusé : « "
                                    f"{str(cible)[:60]} » ne figure pas "
                                    "littéralement dans la page conservée"))
            if tolerer_absence:
                c.retrograde += " (reformatage attendu : date, nombre, code)"
            self.constats.append(c)
            return c
        c = Constat(champ, valeur, Niveau.OBSERVE, extrait=extrait, position=position)
        self.constats.append(c)
        return c

    def interpreter(self, champ: str, valeur, *, regle: str, extrait: str = "") -> Constat:
        """Une conclusion sémantique. L'extrait cité est vérifié lui aussi."""
        if valeur in (None, "", [], {}):
            return self.inconnu(champ)
        verifie = extrait if (not extrait or self.contient(extrait)) else ""
        c = Constat(champ, valeur, Niveau.INTERPRETE, extrait=verifie, regle=regle,
                    retrograde=("" if verifie or not extrait else
                                f"extrait cité « {extrait[:50]} » introuvable dans la page"))
        self.constats.append(c)
        return c

    def deduire(self, champ: str, valeur, *, regle: str) -> Constat:
        if valeur in (None, "", [], {}):
            return self.inconnu(champ)
        c = Constat(champ, valeur, Niveau.DEDUIT, regle=regle)
        self.constats.append(c)
        return c

    def inconnu(self, champ: str, *, question: str = "") -> Constat:
        c = Constat(champ, None, Niveau.INCONNU, question=question)
        self.constats.append(c)
        return c

    # ----------------------------------------------------------- lecture --
    def par_niveau(self, niveau: Niveau) -> list[Constat]:
        return [c for c in self.constats if c.niveau is niveau]

    def comptes(self) -> dict:
        return {n: len(self.par_niveau(n)) for n in ORDRE}

    def retrogradations(self) -> list[Constat]:
        return [c for c in self.constats if c.retrograde]

    def questions(self) -> list[str]:
        return [c.question for c in self.par_niveau(Niveau.INCONNU) if c.question]

    def tableau(self) -> str:
        largeur = max([len(c.champ) for c in self.constats] or [12]) + 1
        lignes = []
        for niveau in ORDRE:
            groupe = self.par_niveau(niveau)
            if not groupe:
                continue
            lignes.append(f"\n  {niveau.marque} {niveau.value}  ({len(groupe)})")
            lignes.append("  " + "─" * 66)
            for c in groupe:
                lignes.append("  " + c.ligne(largeur).replace("\n", "\n  "))
        return "\n".join(lignes)

    def resume(self) -> str:
        c = self.comptes()
        total = sum(c.values()) or 1
        return " · ".join(
            f"{n.marque} {n.value} {c[n]} ({100 * c[n] // total} %)"
            for n in ORDRE if c[n])
