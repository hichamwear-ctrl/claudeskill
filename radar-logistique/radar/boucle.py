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
