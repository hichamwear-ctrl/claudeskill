"""La boucle commerciale.

    SOURCE → OPPORTUNITÉ → ENTREPRISE → SURVEILLANCE → NOUVEAU BESOIN
           → NOUVELLE OPPORTUNITÉ → CONTACT → APPRENTISSAGE

Une entreprise découverte produit ses propres recherches, qui produisent
d'autres besoins, qui font apparaître d'autres entreprises. La profondeur est
BORNÉE : sans cela l'exploration ne s'arrête jamais et le quota part en fumée.

Chaque opportunité conserve par quoi elle a été trouvée — requête, entreprise,
profondeur — pour que la traçabilité tienne jusqu'au bout.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .entreprises import Motif, Registre as RegistreEntreprises, domaine_de, nom_probable


@dataclass
class Etape:
    profondeur: int
    requete: str
    entreprise: str | None = None
    resultats: int = 0
    opportunites: int = 0
    entreprises_nouvelles: int = 0


@dataclass
class Trace:
    etapes: list[Etape] = field(default_factory=list)
    budget_utilise: int = 0
    budget_total: int = 0
    arret: str = ""

    def resume(self) -> str:
        L = ["BOUCLE DE DÉCOUVERTE", "=" * 72, ""]
        if not self.etapes:
            L.append("  aucune étape exécutée.")
        for e in self.etapes:
            marge = "  " * e.profondeur
            cible = f" [{e.entreprise}]" if e.entreprise else ""
            L.append(f"  {marge}n{e.profondeur}{cible} « {e.requete[:52]} » → "
                     f"{e.resultats} résultats, {e.opportunites} opportunités, "
                     f"{e.entreprises_nouvelles} entreprise(s)")
        L.append("")
        L.append(f"  budget : {self.budget_utilise}/{self.budget_total} requêtes")
        if self.arret:
            L.append(f"  arrêt : {self.arret}")
        return "\n".join(L)


class Boucle:
    """Enchaîne recherche générale et recherche ciblée par entreprise.

    `chercher(requete)` est fourni par l'appelant : c'est le connecteur Google,
    ou n'importe quel autre moteur. La boucle ne sait pas d'où viennent les
    résultats — elle sait seulement quoi en faire.
    """

    def __init__(self, generateur, entreprises: RegistreEntreprises,
                 profondeur_max: int = 2, budget: int = 100):
        self.generateur = generateur
        self.entreprises = entreprises
        self.profondeur_max = profondeur_max
        self.budget = budget

    def _entreprises_dans(self, resultats, origine, profondeur) -> int:
        """Repère les entreprises citées. Un nom non identifiable n'est PAS
        inventé : on retient alors seulement le domaine."""
        nouvelles = 0
        for r in resultats:
            domaine = domaine_de(getattr(r, "url", None))
            nom = nom_probable(f"{getattr(r, 'titre', '')} {getattr(r, 'extrait', '')}")
            if not nom and not domaine:
                continue
            avant = len(self.entreprises.entreprises)
            self.entreprises.decouvrir(nom or domaine, domaine=domaine,
                                       motif=Motif.CHERCHE_PARTENAIRE,
                                       origine=origine, profondeur=profondeur)
            if len(self.entreprises.entreprises) > avant:
                nouvelles += 1
        return nouvelles

    def parcourir(self, chercher, *, requetes_generales=None,
                  analyser=None) -> Trace:
        """chercher(requete) -> [Resultat] · analyser(resultats) -> nb opportunités."""
        trace = Trace(budget_total=self.budget)
        file = [(0, q, None) for q in (requetes_generales or self.generateur.generer(20))]

        while file and trace.budget_utilise < self.budget:
            profondeur, requete, entreprise = file.pop(0)
            resultats = chercher(requete)
            trace.budget_utilise += 1

            opportunites = analyser(resultats) if analyser else 0
            # Le moteur qui a produit les résultats se nomme lui-même : la
            # boucle ne présume pas que c'est Google. Brave, ou n'importe quel
            # autre moteur branché plus tard, s'inscrit de la même façon.
            fournisseur = next((getattr(r, "fournisseur", None) for r in resultats
                                if getattr(r, "fournisseur", None)), "recherche")
            origine = f"{fournisseur}/n{profondeur}"
            nouvelles = self._entreprises_dans(resultats, origine, profondeur)
            trace.etapes.append(Etape(profondeur, getattr(requete, "texte", str(requete)),
                                      entreprise, len(resultats), opportunites, nouvelles))

            # Descente : chaque entreprise retenue engendre ses propres requêtes.
            if profondeur < self.profondeur_max:
                for e in self.entreprises.a_surveiller(limite=5):
                    if e.profondeur > profondeur:
                        continue
                    for q in self.generateur.pour_entreprise(e.nom, e.domaine):
                        file.append((profondeur + 1, q, e.nom))

        trace.arret = ("budget épuisé" if trace.budget_utilise >= self.budget
                       else "plus rien à explorer")
        return trace


# ═══════════════════════════════════ LE SECOND CIRCUIT : LA SURVEILLANCE
#
# `Boucle` ci-dessus est le circuit DÉCOUVERTE : il a besoin d'un moteur de
# recherche, parce qu'il cherche ce qu'on ne connaît pas encore.
#
# `Veille` est le circuit SOURCE CONNUE. Il n'importe aucun moteur, n'en
# interroge aucun, et fonctionne à l'identique si Google, Brave, Exa et Tavily
# sont tous indisponibles. C'est exactement la règle :
#
#     une source que le radar connaît déjà doit pouvoir être analysée,
#     surveillée et transformée en opportunité SANS moteur de recherche.
#
# Les deux circuits ne se mélangent pas, et leurs compteurs non plus.

@dataclass
class PassageVeille:
    """Le résultat d'UNE page visitée. Chaque page est indépendante."""
    url: str
    acces: str
    changement: str = ""
    opportunites: int = 0
    motif: str = ""
    hors_metier: bool = False      # la porte l'a écartée avant la chaîne


@dataclass
class TraceVeille:
    """Les chiffres de la SURVEILLANCE. Ils ne se mélangent jamais à ceux de
    la découverte : une opportunité vue en revisitant une page connue n'est
    pas une opportunité découverte."""
    passages: list = field(default_factory=list)
    entreprises_surveillees: int = 0

    @property
    def pages_surveillees(self) -> int:
        return len(self.passages)

    @property
    def pages_consultees(self) -> int:
        return sum(1 for p in self.passages if p.acces == "CONSULTÉE")

    @property
    def pages_modifiees(self) -> int:
        return sum(1 for p in self.passages if p.changement == "MODIFIÉE")

    @property
    def pages_non_commerciales(self) -> int:
        """Le texte a bougé, mais rien n'y rattache notre métier. Enregistré,
        jamais analysé, JAMAIS supprimé."""
        return sum(1 for p in self.passages if p.hors_metier)

    @property
    def pages_changees_techniquement(self) -> int:
        """Le fichier a bougé, pas ce qu'on y lit. Enregistré, jamais analysé."""
        return sum(1 for p in self.passages
                   if p.changement == "MODIFIÉE — TECHNIQUE")

    @property
    def pages_en_erreur(self) -> int:
        return sum(1 for p in self.passages if p.acces == "ERREUR")

    @property
    def pages_non_disponibles(self) -> int:
        return sum(1 for p in self.passages if p.acces == "NON DISPONIBLE")

    @property
    def opportunites(self) -> int:
        return sum(p.opportunites for p in self.passages)

    def resume(self) -> str:
        L = ["SURVEILLANCE — sources connues, aucun moteur de recherche requis",
             "=" * 72, ""]
        if not self.passages:
            L.append("  aucune page surveillée : aucune n'a été déclarée.")
            L.append("  Une page n'est jamais supposée à partir d'un domaine.")
            return "\n".join(L)
        for p in self.passages:
            L.append(f"  {p.acces:<17} {p.changement or '—':<16} "
                     f"{p.opportunites:>3} opp.  {p.url[:44]}"
                     + (f"  · {p.motif[:36]}" if p.motif else ""))
        L.append("")
        L.append(f"  entreprises surveillées   {self.entreprises_surveillees}")
        L.append(f"  pages surveillées         {self.pages_surveillees}")
        L.append(f"  pages consultées          {self.pages_consultees}")
        L.append(f"  pages modifiées           {self.pages_modifiees}")
        L.append(f"    dont purement techniques  "
                 f"{self.pages_changees_techniquement}  (enregistrées, non analysées)")
        L.append(f"    dont hors métier          "
                 f"{self.pages_non_commerciales}  (enregistrées, non analysées)")
        L.append(f"  opportunités générées     {self.opportunites}")
        L.append(f"  pages en erreur           {self.pages_en_erreur}")
        L.append(f"  pages non disponibles     {self.pages_non_disponibles}")
        if self.pages_en_erreur or self.pages_non_disponibles:
            L.append("")
            L.append("  Une page non lue n'est PAS une page sans opportunité :")
            L.append("  son contenu reste INCONNU, et ce qu'on en savait est conservé.")
        return "\n".join(L)


class Veille:
    """Revisite les pages connues. Ne connaît aucun moteur de recherche.

    `recuperer(url)` rend une Collecte (radar/collecte_directe.py).
    `analyser(collecte, page)` rend un nombre d'opportunités — facultatif.
    """

    def __init__(self, cx, recuperer, analyser=None, profil=None,
                 ontologie=None, detecteur=None):
        self.cx, self.recuperer, self.analyser = cx, recuperer, analyser
        # Le profil de lecture déclaré, pour extraire le TEXTE LISIBLE. Sans
        # lui, on ne compare que les octets et toute régénération de page
        # passe pour un mouvement du marché.
        self.profil = profil
        # LA PORTE AVANT LA CHAÎNE. Elle n'a pas de vocabulaire propre : elle
        # interroge l'ontologie et le détecteur de rôle existants. Absents,
        # elle laisse TOUT passer — on préfère analyser pour rien qu'écarter
        # en silence une modification qu'on n'a pas su juger.
        self.ontologie, self.detecteur = ontologie, detecteur

    def _porte(self, texte) -> tuple[bool, str]:
        """Cette modification peut-elle porter un besoin ? En cas de doute, OUI.

        Rend (passer_dans_la_chaine, verdict_affiné).

        On n'écarte QUE le cas certain : un texte lisible dans lequel les
        mécanismes métier ne reconnaissent absolument rien. Tout le reste —
        texte illisible, mécanismes absents, rattachement même partiel —
        entre dans la chaîne. C'est un choix de recall assumé : une affaire
        manquée coûte plus cher qu'une analyse inutile.
        """
        from . import changement as mod_changement
        if not texte or self.ontologie is None or self.detecteur is None:
            return True, mod_changement.MODIFIEE          # INCONNU → chaîne
        from .pertinence import Confiance, evaluer
        verdict = evaluer(texte, self.ontologie, self.detecteur)
        if verdict.confiance is Confiance.AUCUNE:
            return False, mod_changement.NON_COMMERCIALE
        return True, mod_changement.MODIFIEE

    def _texte_de(self, collecte):
        """Ce que la page DIT, lu par le profil déclaré. None si illisible :
        on retombe alors sur la comparaison d'octets, jamais sur une
        conclusion inventée."""
        if not collecte.lue or not self.profil:
            return None
        try:
            from .page import lire as lire_page
            return lire_page(collecte.octets.decode("utf-8", errors="replace"),
                             self.profil).texte
        except Exception:                                        # noqa: BLE001
            return None

    def passer(self, pages=None, *, entreprise=None, limite=None) -> TraceVeille:
        from . import changement, pages as mod_pages

        liste = pages if pages is not None else mod_pages.a_surveiller(
            self.cx, entreprise=entreprise, limite=limite)
        trace = TraceVeille(
            entreprises_surveillees=len({p.entreprise for p in liste if p.entreprise}))

        for page in liste:
            # Chaque page est INDÉPENDANTE : une page qui échoue n'empêche
            # aucune autre d'être consultée.
            try:
                collecte = self.recuperer(page.url)
            except Exception as e:                               # noqa: BLE001
                mod_pages.marquer(self.cx, page.url, mod_pages.Acces.ERREUR,
                                  motif=f"collecte impossible : {e}")
                trace.passages.append(PassageVeille(page.url, "ERREUR",
                                                    motif=str(e)[:60]))
                continue

            empreinte = collecte.empreinte
            mod_pages.marquer(self.cx, page.url, collecte.acces,
                              motif=collecte.motif, empreinte=empreinte)

            # DEUX NIVEAUX, et ils ne disent pas la même chose :
            #   le FICHIER a-t-il bougé ?  le TEXTE LISIBLE a-t-il bougé ?
            # Un horodatage dans un commentaire HTML, un jeton de session ou
            # un ordre d'attributs change le premier sans toucher au second.
            # `observer` ne mémorise que si quelque chose a été lu : une
            # erreur n'écrase pas l'empreinte de la dernière lecture réussie.
            texte = self._texte_de(collecte)
            verdict = changement.observer(self.cx, page.url,
                                          collecte.octets, texte)

            n = 0
            # LA PAGE PASSE DANS LA CHAÎNE QUAND SON CONTENU A UN SENS
            # NOUVEAU. Un changement purement technique est ENREGISTRÉ et
            # s'arrête là : sinon chaque régénération de page fabriquerait une
            # opportunité. Et la détection de changement ne DÉCIDE de rien —
            # elle dit que la page ne dit plus la même chose ; c'est la chaîne
            # qui juge s'il y a un besoin commercial.
            hors_metier = False
            if verdict in (changement.MODIFIEE, changement.PREMIERE):
                passer, _ = self._porte(texte)
                hors_metier = not passer
                # Le verdict de CONTENU reste ce qu'il est : une première
                # visite reste une première visite. Seule une modification
                # écartée par la porte prend le libellé qui le dit.
                if not passer and verdict == changement.MODIFIEE:
                    verdict = changement.NON_COMMERCIALE
                if passer and collecte.lue and self.analyser is not None:
                    n = self.analyser(collecte, page) or 0
            trace.passages.append(PassageVeille(
                page.url, collecte.acces.value,
                changement=verdict if verdict != changement.NON_COMPARABLE else "",
                opportunites=n, motif=collecte.motif, hors_metier=hors_metier))
        self.cx.commit()
        return trace
