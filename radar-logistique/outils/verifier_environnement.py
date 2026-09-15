# -*- coding: utf-8 -*-
"""CE QU'IL FAUT POUR QUE LE RADAR DÉMARRE — vérifié, pas promis.

La documentation a affirmé pendant tout un cycle que PyYAML était « la seule
dépendance ». C'était faux, et c'est un utilisateur sous Windows qui l'a
découvert, bloqué, avec un `ModuleNotFoundError: No module named 'tzdata'`
avant même la première commande. Un fichier de dépendances qui n'est jamais
exécuté finit toujours par mentir ; celui-ci est exécuté.

Il se lance avec N'IMPORTE QUEL Python, même trop ancien — pas de f-string,
pas d'annotation, pas de syntaxe récente : un interpréteur de 2015 doit
pouvoir lire ce fichier pour dire qu'il est trop vieux.

    python outils/verifier_environnement.py

Sortie 0 : tout est là. Sortie 1 : ce qui manque, et la ligne à taper.
"""

import sys

MINIMUM = (3, 11)


def _manques():
    """La liste de ce qui manque. Chaque entrée : (quoi, pourquoi, remede)."""
    manques = []

    if sys.version_info < MINIMUM:
        manques.append((
            "Python %d.%d" % MINIMUM,
            "Python %d.%d.%d est trop ancien ; le radar écrit « int | None »"
            " et lit « zoneinfo »." % sys.version_info[:3],
            "installez Python 3.11 ou plus récent depuis python.org"))
        return manques          # inutile de tester le reste sur un vieux Python

    try:
        import yaml                                          # noqa: F401
    except ImportError:
        manques.append((
            "PyYAML",
            "le profil, les rôles, la géographie et les pondérations sont"
            " des fichiers .yaml : sans PyYAML, aucune configuration ne se"
            " lit.",
            "pip install pyyaml"))

    # La vérification de fuseau passe par le VRAI module du radar, pas par une
    # importation de tzdata : ce qui compte n'est pas qu'un paquet soit
    # installé, c'est que « Europe/Brussels » se résolve. Sous Linux la base
    # du système suffit ; sous Windows il n'y en a aucune, et le paquet tzdata
    # devient obligatoire. Tester le besoin, jamais le contournement.
    sys.path.insert(0, _racine())
    try:
        import radar.statut                                  # noqa: F401
    except Exception as e:                                   # noqa: BLE001
        if "No time zone found" in str(e) or "tzdata" in str(e):
            manques.append((
                "tzdata",
                "les échéances sont lues en heure belge : une date sans"
                " fuseau vaut Europe/Brussels. Windows ne livre aucune base"
                " de fuseaux horaires, il faut donc le paquet tzdata."
                " Remplacer le fuseau par un décalage fixe décalerait toutes"
                " les échéances d'une heure la moitié de l'année.",
                "pip install tzdata"))
        else:
            manques.append(("radar", str(e), "vérifiez l'installation"))
    return manques


def _racine():
    import os
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def principal():
    manques = _manques()
    if not manques:
        sys.stdout.write(
            "ENVIRONNEMENT COMPLET\n"
            "  Python   %d.%d.%d\n"
            "  PyYAML   presente\n"
            "  Fuseau   Europe/Brussels resolu\n" % sys.version_info[:3])
        return 0

    lignes = ["", "IL MANQUE DE QUOI DEMARRER LE RADAR", ""]
    for quoi, pourquoi, remede in manques:
        lignes.append("  %s" % quoi)
        lignes.append("    %s" % pourquoi)
        lignes.append("    -> %s" % remede)
        lignes.append("")
    lignes.append("  Sous Windows, tout d'un coup :")
    lignes.append("      py -m pip install pyyaml tzdata")
    lignes.append("")
    sys.stderr.write("\n".join(lignes))
    return 1


if __name__ == "__main__":
    sys.exit(principal())
