"""MESURE DU LEXIQUE — FR / NL / EN, sur NOTRE vocabulaire.

Ce que ce script mesure : ce que le radar SAIT RECONNAÎTRE.
Ce qu'il ne mesure PAS : ce qui existe sur le marché belge.

Aucun réseau, aucune clé, aucune donnée réelle. Les phrases sont des
FORMULATIONS TYPES écrites à la main pour éprouver le lexique — elles ne
viennent d'aucune page et ne prouvent l'existence d'aucune entreprise.

Un « faux négatif linguistique » ici veut dire : le même besoin, écrit dans
une autre langue, n'est pas reconnu. C'est un défaut de LEXIQUE, pas un
défaut de marché.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar.cli import _moteur                                   # noqa: E402

# Chaque groupe dit LA MÊME CHOSE dans trois langues. Si les trois ne
# donnent pas la même lecture, c'est le lexique qui manque, pas le besoin.
EQUIVALENCES = [
    ("partenaire de livraison", [
        ("FR", "Nous recherchons un partenaire de livraison"),
        ("NL", "Wij zoeken een leveringspartner"),
        ("EN", "We are looking for a delivery partner")]),
    ("sous-traitant transport", [
        ("FR", "Nous recherchons un sous-traitant transport"),
        ("NL", "Wij zoeken een onderaannemer transport"),
        ("EN", "We are looking for a transport subcontractor")]),
    ("distribution de colis", [
        ("FR", "distribution de colis en Belgique"),
        ("NL", "pakketbezorging in België"),
        ("EN", "parcel delivery in Belgium")]),
    ("recrutement de chauffeurs", [
        ("FR", "recrutement de chauffeurs"),
        ("NL", "chauffeurs gezocht"),
        ("EN", "drivers wanted")]),
    ("devenir partenaire", [
        ("FR", "devenir partenaire transport"),
        ("NL", "word transportpartner"),
        ("EN", "become a transport partner")]),
]


def lire(moteur, phrase):
    c = moteur.ontologie.analyser(phrase, [], None)
    r = moteur.roles.analyser(phrase, [], None)
    familles = list(getattr(c, "familles", []) or [])
    return familles, getattr(r.role, "value", str(r.role))


def principal():
    moteur = _moteur()
    print("MESURE DU LEXIQUE — FR / NL / EN")
    print("=" * 88)
    print("Mesure ce que le radar SAIT LIRE. Ne mesure AUCUN marché.")
    print()
    ecarts = []
    for sujet, phrases in EQUIVALENCES:
        print(f"« {sujet} »")
        lectures = {}
        for langue, phrase in phrases:
            familles, role = lire(moteur, phrase)
            lectures[langue] = (tuple(familles), role)
            fam = ", ".join(familles) if familles else "—"
            print(f"   {langue}  {phrase[:52]:<54} familles: {fam:<20} rôle: {role}")
        distinctes = set(lectures.values())
        if len(distinctes) > 1:
            reference = lectures["FR"]
            for langue, lecture in lectures.items():
                if lecture != reference:
                    ecarts.append((sujet, langue, lecture, reference))
            print("   ⚠ LES TROIS LANGUES NE DONNENT PAS LA MÊME LECTURE")
        print()

    print("-" * 88)
    if not ecarts:
        print("Aucun écart : les trois langues se lisent pareil sur cet échantillon.")
        return 0
    print(f"{len(ecarts)} FAUX NÉGATIF(S) LINGUISTIQUE(S) — le même besoin, non reconnu")
    for sujet, langue, lecture, reference in ecarts:
        print(f"  · « {sujet} » en {langue}")
        print(f"      lu      : familles {list(lecture[0]) or '—'} · rôle {lecture[1]}")
        print(f"      attendu : familles {list(reference[0]) or '—'} · rôle {reference[1]}")
    print()
    print("CE N'EST PAS UNE CORRECTION À APPLIQUER À L'AVEUGLE.")
    print("Un lexique se complète sur des formulations RÉELLEMENT rencontrées,")
    print("pas sur des phrases écrites pour le test : ajouter un mot que")
    print("personne n'emploie ne fait rien gagner, et ajouter un mot trop large")
    print("fait entrer du bruit pour toujours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
