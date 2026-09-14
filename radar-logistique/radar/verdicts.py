"""CE QU'UN HUMAIN A JUGÉ — et surtout ce que le radar a MANQUÉ.

    VRAI POSITIF   le radar l'a retenu, et il avait raison
    FAUX POSITIF   le radar l'a retenu, et il avait tort
    FAUX NÉGATIF   le radar NE l'a PAS retenu, et il avait tort
    INCONNU        personne n'a tranché — et c'est une réponse

POURQUOI CETTE TABLE EXISTE
===========================

Un faux positif est en base : on peut le montrer du doigt. Un faux négatif,
lui, n'y est souvent PAS — c'est exactement ce qui le définit. Sans un
registre qui accepte une adresse que le radar n'a jamais retenue, un faux
négatif n'aurait nulle part où vivre et disparaîtrait du bilan.

Un bilan qui ne compte que ses réussites ne mesure rien.

C'est la raison pour laquelle `inscrire()` n'exige NI page candidate, NI
trouvaille, NI opportunité. On peut écrire « le radar a manqué ceci » à
propos d'une adresse dont il n'a jamais entendu parler.

LE RADAR NE SE JUGE PAS LUI-MÊME
================================

`juge_par` ne vaut jamais « radar ». Un système qui décide seul de ses
succès finit par se donner raison. Le verdict vient de l'exploitant, ou d'un
relecteur nommé, et la clé d'unicité porte sur (url, juge_par) — deux
personnes ont le droit de ne pas être d'accord, et les deux avis restent.

CE MODULE NE DÉCIDE RIEN
========================

Il n'écarte aucune page, n'ajoute aucun point, ne modifie aucun score, ne
change aucune classification. Il enregistre un jugement et le compte. Ce que
le radar fera de ces comptes est une décision métier, qui n'est pas prise
ici — et pas encore prise du tout.

UN PETIT ÉCHANTILLON SE DIT PETIT
=================================

Trois verdicts ne font pas un taux. Le rapport écrit ÉCHANTILLON
INSUFFISANT plutôt qu'un pourcentage, parce qu'un pourcentage calculé sur
trois observations se lit exactement comme un pourcentage calculé sur mille.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .pages import normaliser

# En dessous, aucun taux n'est affiché. Ce n'est pas un seuil de qualité :
# c'est le seuil en dessous duquel un pourcentage ment par sa seule présence.
MINIMUM_POUR_UN_TAUX = 20

NON_MESURE = "NON MESURÉ"
ECHANTILLON_INSUFFISANT = "ÉCHANTILLON INSUFFISANT"


class Verdict(Enum):
    VRAI_POSITIF = "VRAI POSITIF"
    FAUX_POSITIF = "FAUX POSITIF"
    FAUX_NEGATIF = "FAUX NÉGATIF"
    INCONNU = "INCONNU"

    @property
    def emoji(self) -> str:
        return {"VRAI POSITIF": "🟢", "FAUX POSITIF": "🔴",
                "FAUX NÉGATIF": "🟠", "INCONNU": "⚪"}[self.value]

    @property
    def retenu_par_le_radar(self) -> bool | None:
        """Le radar l'avait-il retenu ? None quand personne n'a tranché."""
        if self is Verdict.INCONNU:
            return None
        return self is not Verdict.FAUX_NEGATIF


class VerdictInconnu(ValueError):
    """Une étiquette qui n'est pas l'une des quatre."""


class JugeInvalide(ValueError):
    """Le radar ne se juge pas lui-même."""


# Ce que le radar ne peut jamais être : son propre juge.
JUGES_INTERDITS = {"radar", "le radar", "systeme", "système", "auto",
                   "automatique"}


def lire_verdict(valeur) -> Verdict:
    if isinstance(valeur, Verdict):
        return valeur
    v = str(valeur or "").strip().upper()
    for x in Verdict:
        if v == x.value or v == x.name:
            return x
    # Les abréviations qu'on écrit en relisant vingt lignes à la main.
    raccourcis = {"VP": Verdict.VRAI_POSITIF, "FP": Verdict.FAUX_POSITIF,
                  "FN": Verdict.FAUX_NEGATIF, "?": Verdict.INCONNU}
    if v in raccourcis:
        return raccourcis[v]
    raise VerdictInconnu(
        f"« {valeur} » n'est pas un verdict. Les quatre sont : "
        + " · ".join(x.value for x in Verdict))


@dataclass
class Jugement:
    url: str
    verdict: Verdict
    motif: str | None = None
    entreprise: str | None = None
    source: str | None = None
    juge_par: str = "exploitant"
    juge_le: str | None = None

    def ligne(self) -> str:
        return (f"{self.verdict.emoji} {self.verdict.value:<14} "
                f"{(self.motif or '')[:44]:<46} {self.url[:56]}")


def inscrire(cx, url, verdict, *, motif=None, entreprise=None, source=None,
             juge_par: str = "exploitant") -> Jugement:
    """Enregistre un jugement humain sur une adresse.

    N'exige NI page, NI trouvaille, NI opportunité : un faux négatif porte
    par définition sur quelque chose que le radar n'a pas retenu, et devoir
    l'avoir en base pour pouvoir dire qu'il manque serait absurde.
    """
    from .base import maintenant
    v = lire_verdict(verdict)
    juge = str(juge_par or "").strip() or "exploitant"
    if juge.lower() in JUGES_INTERDITS:
        raise JugeInvalide(
            "le radar ne juge pas ses propres résultats : un système qui "
            "décide seul de ses succès finit par se donner raison. "
            "Nommez la personne ou le relecteur.")
    u = normaliser(str(url or "").strip())
    if not u:
        raise ValueError("un verdict sans adresse ne se rattache à rien")

    quand = maintenant()
    cx.execute(
        "INSERT INTO verdicts(url, verdict, motif, entreprise, source,"
        " juge_par, juge_le) VALUES(?,?,?,?,?,?,?)"
        " ON CONFLICT(url, juge_par) DO UPDATE SET"
        "   verdict=excluded.verdict, motif=excluded.motif,"
        "   entreprise=excluded.entreprise, source=excluded.source,"
        "   juge_le=excluded.juge_le",
        (u, v.value, motif, entreprise, source, juge, quand))
    return Jugement(url=u, verdict=v, motif=motif, entreprise=entreprise,
                    source=source, juge_par=juge, juge_le=quand)


def _depuis(l) -> Jugement:
    return Jugement(url=l["url"], verdict=lire_verdict(l["verdict"]),
                    motif=l["motif"], entreprise=l["entreprise"],
                    source=l["source"], juge_par=l["juge_par"],
                    juge_le=l["juge_le"])


def tous(cx, *, verdict=None, source=None) -> list[Jugement]:
    sql, args, ou = "SELECT * FROM verdicts", [], []
    if verdict is not None:
        ou.append("verdict=?")
        args.append(lire_verdict(verdict).value)
    if source:
        ou.append("source=?")
        args.append(source)
    if ou:
        sql += " WHERE " + " AND ".join(ou)
    return [_depuis(l) for l in cx.execute(sql + " ORDER BY id", args).fetchall()]


def lire(cx, url, juge_par: str = "exploitant") -> Jugement | None:
    l = cx.execute("SELECT * FROM verdicts WHERE url=? AND juge_par=?",
                   (normaliser(str(url)), juge_par)).fetchone()
    return _depuis(l) if l else None


def comptes(cx, *, source=None) -> dict:
    sortie = {v.value: 0 for v in Verdict}
    for j in tous(cx, source=source):
        sortie[j.verdict.value] += 1
    return sortie


def metriques(cx, *, source=None) -> dict:
    """Les comptes, et les taux SEULEMENT s'ils veulent dire quelque chose."""
    c = comptes(cx, source=source)
    juges = sum(c.values())
    tranches = juges - c[Verdict.INCONNU.value]
    retenus = c[Verdict.VRAI_POSITIF.value] + c[Verdict.FAUX_POSITIF.value]
    manques = c[Verdict.FAUX_NEGATIF.value]

    sortie = {**c, "juges": juges, "tranches": tranches,
              "suffisant": tranches >= MINIMUM_POUR_UN_TAUX}
    if tranches < MINIMUM_POUR_UN_TAUX:
        sortie["precision"] = ECHANTILLON_INSUFFISANT
        sortie["rappel"] = ECHANTILLON_INSUFFISANT
        return sortie
    sortie["precision"] = (c[Verdict.VRAI_POSITIF.value] / retenus
                           if retenus else NON_MESURE)
    trouvables = c[Verdict.VRAI_POSITIF.value] + manques
    sortie["rappel"] = (c[Verdict.VRAI_POSITIF.value] / trouvables
                        if trouvables else NON_MESURE)
    return sortie


def rapport(cx) -> str:
    m = metriques(cx)
    L = ["QUALITÉ — ce qu'un humain a jugé", "=" * 84, ""]
    if not m["juges"]:
        L.append(f"  {NON_MESURE} — aucun résultat n'a encore été jugé.")
        L.append("  Ce n'est pas « zéro erreur » : c'est l'absence de relecture.")
        L.append("  Le radar ne peut pas savoir seul s'il s'est trompé.")
        return "\n".join(L)

    for v in Verdict:
        L.append(f"  {v.emoji} {v.value:<16} {m[v.value]:>5}")
    L.append("")
    if not m["suffisant"]:
        L.append(f"  PRÉCISION  {ECHANTILLON_INSUFFISANT}")
        L.append(f"  RAPPEL     {ECHANTILLON_INSUFFISANT}")
        L.append(f"  {m['tranches']} verdict(s) tranché(s) — moins de "
                 f"{MINIMUM_POUR_UN_TAUX}.")
        L.append("  Un pourcentage calculé sur si peu se lit exactement comme")
        L.append("  un pourcentage calculé sur mille. On ne l'écrit donc pas.")
    else:
        for cle, libelle in (("precision", "PRÉCISION"), ("rappel", "RAPPEL")):
            v = m[cle]
            L.append(f"  {libelle:<10} {v:.0%}" if isinstance(v, float)
                     else f"  {libelle:<10} {v}")

    manques = tous(cx, verdict=Verdict.FAUX_NEGATIF)
    if manques:
        L.append("")
        L.append("CE QUE LE RADAR A MANQUÉ — jamais masqué")
        for j in manques:
            L.append("  " + j.ligne())
        L.append("  Un faux négatif ne disparaît pas du bilan parce qu'il est")
        L.append("  absent de la base : c'est précisément ce qui le définit.")
    return "\n".join(L)
