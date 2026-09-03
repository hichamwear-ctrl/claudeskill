"""Ligne de commande.

Un outil qui échoue le dit et s'arrête avec un code non nul, plutôt que
d'afficher « 0 » partout en signalant un succès.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import apprentissage as appr, envoi, sondage as sondage_mod
from .mode import Mode
from .adaptateur import Adaptateur, vers_opportunite
from .base import ouvrir
from .chaine import Moteur, traiter

RACINE = Path(__file__).resolve().parent.parent


def _mode(a) -> Mode:
    return Mode.REEL if getattr(a, "reel", False) else Mode.DEMO


def _base(a) -> str:
    """Deux fichiers distincts : une fixture ne peut pas atterrir dans la base réelle."""
    if a.base:
        return a.base
    return _mode(a).base_par_defaut


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _vocabulaires(cx=None) -> dict:
    """Le vocabulaire de procédure de CHAQUE source déclarée.

    Deux couches : ce que l'adaptateur déclare (écrit à la main, prioritaire)
    et ce que la mémoire a appris des collectes précédentes.
    """
    from .procedure import Vocabulaire, fusionner_vocabulaires, vocabulaire_appris
    sortie = {}
    for chemin in sorted((RACINE / "sources").glob("*.yaml")):
        cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
        nom = cfg.get("source", chemin.stem)
        declare = Vocabulaire(cfg)
        appris = vocabulaire_appris(cx, nom) if cx is not None else None
        sortie[nom] = fusionner_vocabulaires(appris, declare)
    # Les moteurs partagent l'adaptateur « recherche » mais gardent chacun leur
    # provenance : ils héritent donc de son vocabulaire, sans le confondre.
    for moteur in ("google", "brave"):
        sortie.setdefault(moteur, sortie.get("recherche"))
    return sortie


def _moteur(cx=None) -> Moteur:
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=_vocabulaires(cx))


def _source(nom):
    chemin = RACINE / "sources" / f"{nom}.yaml"
    if not chemin.exists():
        print(f"source inconnue : {nom} (aucun fichier {chemin.name})", file=sys.stderr)
        raise SystemExit(2)
    cfg = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    return Adaptateur.depuis_config(cfg), cfg


def _charger(adaptateur, cfg, chemin, source):
    charges = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if not isinstance(charges, list) or not charges:
        print("entrée vide ou mal formée — rien à traiter", file=sys.stderr)
        raise SystemExit(2)
    defauts = {"signal": cfg.get("signal"), "secteur": cfg.get("secteur_par_defaut")}
    return [vers_opportunite(adaptateur, c, source, defauts) for c in charges], charges


def cmd_recenser(a) -> int:
    adaptateur, _ = _source(a.source)
    charges = json.loads(Path(a.echantillon).read_text(encoding="utf-8"))
    if not isinstance(charges, list) or not charges:
        print("échantillon vide — rien à mesurer", file=sys.stderr)
        return 2
    taux = adaptateur.mesurer(charges)
    print(f"Recensement des clés « {a.source} » sur {len(charges)} réponses réelles\n")
    for nom, t in sorted(taux.items(), key=lambda x: -x[1]):
        marque = "  " if t > 0.5 else ("~ " if t > 0 else "✗ ")
        print(f"  {marque}{t:6.1%}  {nom}")
    absents = [n for n, t in taux.items() if t == 0]
    if absents:
        print(f"\n{len(absents)} champ(s) à 0 % : la clé déclarée n'existe pas.")
        print(f"Corrige-les dans sources/{a.source}.yaml, PAS dans le code.")
        return 1
    print("\nTous les champs répondent. Passe `verifie: true` dans le fichier de source.")
    return 0


def cmd_sonder(a) -> int:
    """Mesure le marché AVANT de construire quoi que ce soit de plus."""
    adaptateur, cfg = _source(a.source)
    opportunites, _ = _charger(adaptateur, cfg, a.entree, a.source)
    s = sondage_mod.sonder(_moteur(), opportunites, a.source)
    print(s.rapport())
    if not cfg.get("verifie"):
        print("\n/!\\ adaptateur non vérifié : lance d'abord `recenser`.")
        print("    Les chiffres ci-dessus portent sur ce que l'adaptateur a SU lire.")
    return 0


def cmd_traiter(a) -> int:
    print(_mode(a).bandeau())
    adaptateur, cfg = _source(a.source)
    if not cfg.get("verifie"):
        print(f"AVERTISSEMENT : adaptateur « {a.source} » non vérifié — lance `recenser`.\n",
              file=sys.stderr)
    opportunites, _ = _charger(adaptateur, cfg, a.entree, a.source)
    cx = ouvrir(_base(a))
    repris = envoi.reprendre_interrompus(cx)
    if repris:
        print(f"{repris} envoi(s) interrompu(s) marqué(s) ambigus — non réémis.")
    b = traiter(cx, _moteur(cx), opportunites, mode=_mode(a))
    print(f"lus {b.lus} · lots éclatés {b.lots_eclates} · doublons {b.doublons}")
    print(f"🟢 {b.direct} direct · 🟡 {b.renforcement} renforcement · "
          f"🟣 {b.a_construire} à construire · 🔵 {b.prospect} prospect · "
          f"🔴 {b.rejet} rejet")
    print(f"CAPTER {b.capter} · DÉVELOPPER {b.developper} · notifiés {b.notifies}")
    if b.attributions:
        print(f"{b.attributions} attribution(s) mémorisée(s) pour le calendrier")
    if b.motifs_rejet:
        print("rejets : " + " · ".join(f"{k} ×{v}" for k, v in
                                       sorted(b.motifs_rejet.items(), key=lambda x: -x[1])[:5]))
    print()
    print(b.livre.rapport())
    return 0


def cmd_opportunites(a) -> int:
    cx = ouvrir(_base(a), lecture_seule=True)          # incapable d'écrire
    where = "type <> 'REJET'"
    if a.type:
        where = f"type = '{a.type.upper()}'"
    if a.moteur:
        where += f" AND moteur = '{a.moteur.upper()}'"
    lignes = cx.execute(
        f"SELECT o.*, a.ref_source FROM opportunites o JOIN avis a ON a.id=o.avis_id "
        f"WHERE {where} ORDER BY o.score DESC, o.echeance ASC").fetchall()
    if not lignes:
        print("Aucune opportunité. (Base lue correctement — ce n'est pas une panne.)")
        return 0
    for l in lignes:
        if a.complet:
            print(l["fiche"]); print("\n" + "─" * 66 + "\n")
        else:
            emoji = {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
                     "PROSPECT": "🔵"}.get(l["type"], "·")
            print(f"{emoji} [{l['score']:3}] {(l['echeance'] or 'NON PUBLIÉ')[:10]:<11} "
                  f"{(l['action'] or ''):<24} {(l['intitule'] or '')[:44]}")
    print(f"\n{len(lignes)} opportunité(s).")
    return 0


def cmd_calendrier(a) -> int:
    """Ce qui va revenir sur le marché — calculé depuis les attributions."""
    cx = ouvrir(_base(a), lecture_seule=True)
    lignes = cx.execute(
        "SELECT * FROM attributions ORDER BY renouvellement IS NULL, renouvellement").fetchall()
    if not lignes:
        print("Aucune attribution mémorisée pour l'instant.")
        return 0
    print("CALENDRIER DES REMISES EN CONCURRENCE\n")
    for l in lignes:
        quand = (l["renouvellement"] or "")[:7] or "A_VERIFIER"
        print(f"  {quand:<12} {(l['prestation'] or '')[:44]}")
        print(f"  {'':<12} titulaire : {l['titulaire'] or 'A_VERIFIER'} · {l['commentaire']}")
    return 0


def cmd_entreprises(a) -> int:
    """Le registre des entreprises découvertes et surveillées."""
    from .entreprises import Registre as RegistreEnt
    cx = ouvrir(_base(a), lecture_seule=True)
    reg = RegistreEnt()
    for l in cx.execute("SELECT * FROM entreprises"):
        e = reg.decouvrir(l["nom"], domaine=l["domaine"], origine=l["origine"])
        e.besoins_detectes = l["besoins_detectes"]
        e.marches_gagnes = l["marches_gagnes"]
        e.motifs = (l["motifs"] or "").split("; ") if l["motifs"] else []
        e.derniere_visite = l["derniere_visite"]
        from .entreprises import Etat as EtatEnt
        e.etat = EtatEnt(l["etat"]) if l["etat"] in {x.value for x in EtatEnt} else e.etat
        e.motif_ecart = l["motif_ecart"]
    print(reg.rapport())
    return 0


def cmd_surveiller(a) -> int:
    """« surveille cette entreprise » — ajout manuel au registre."""
    from .entreprises import Motif, Registre as RegistreEnt
    from .decouverte import Generateur
    cx = ouvrir(_base(a))
    reg = RegistreEnt()
    e = reg.surveiller(a.nom, domaine=a.domaine, motif=Motif.MANUEL)
    cx.execute(
        "INSERT OR REPLACE INTO entreprises(cle, nom, domaine, etat, motifs, origine,"
        " decouverte_le) VALUES(?,?,?,?,?,?,?)",
        (e.cle, e.nom, e.domaine, e.etat.value, "; ".join(e.motifs), "manuel",
         e.decouverte_le))
    cx.commit()
    print(f"« {e.nom} » est désormais SURVEILLÉE.")
    reqs = Generateur(_cfg("config/decouverte.yaml")).pour_entreprise(e.nom, e.domaine)
    print(f"\n{len(reqs)} recherche(s) ciblée(s) seront lancées dès qu'une clé "
          "Google sera disponible :")
    for q in reqs:
        print(f"  · {q.texte}")
    return 0


def cmd_boucle(a) -> int:
    """La boucle de découverte — sans moteur de recherche, elle ne part pas."""
    from .boucle import Boucle
    from .decouverte import ConnecteurIndisponible, Generateur, charger_connecteur
    from .entreprises import Registre as RegistreEnt

    connecteur = charger_connecteur()
    g = Generateur(_cfg("config/decouverte.yaml"))
    if not connecteur.disponible:
        print(f"BOUCLE NON LANCÉE — {connecteur.motif_indisponibilite}")
        print("\nAucune recherche n'a eu lieu et aucun résultat n'est simulé.")
        print(f"{len(g.generer())} requêtes sont prêtes ; "
              "elles partiront dès qu'une clé sera fournie.")
        return 3
    reg = RegistreEnt()
    cx = ouvrir(_base(a))
    mot = _moteur(cx)
    mot.entreprises = reg

    # Un résultat de recherche N'EST PAS qu'un moyen de découvrir une
    # entreprise : c'est un besoin possible, et il entre dans le même moteur
    # que n'importe quel autre. C'est ce qui permet au radar de voir une
    # affaire AVANT qu'elle ne devienne un appel d'offres — si elle le devient.
    # L'adaptateur « recherche » lit la FORME d'un résultat web, quel que soit
    # le moteur qui l'a produit. La PROVENANCE, elle, est celle du moteur réel :
    # étiqueter un résultat Brave comme « google » ferait mentir le rendement
    # par source et rendrait Google indispensable dans les chiffres.
    adaptateur, cfg_src = _source("recherche")
    defauts = {"signal": cfg_src.get("signal"), "secteur": cfg_src.get("secteur_par_defaut")}

    def analyser(resultats) -> int:
        opportunites = []
        for res in resultats:
            if not hasattr(res, "en_charge"):
                continue
            charge = res.en_charge()
            provenance = charge.get("fournisseur") or "recherche"
            opportunites.append(vers_opportunite(adaptateur, charge, provenance, defauts))
        if not opportunites:
            return 0
        b = traiter(cx, mot, opportunites, mode=_mode(a))
        return b.capter + b.developper

    trace = Boucle(g, reg, profondeur_max=a.profondeur, budget=a.budget).parcourir(
        connecteur.rechercher, analyser=analyser)
    print(trace.resume())
    print()
    print(reg.rapport())
    return 0


def cmd_rapport(a) -> int:
    """Le rapport de mesure, écrit dans rapports/."""
    from pathlib import Path as _P
    from . import rapport as rapport_mod

    mode = _mode(a)
    profil = _cfg("profil.yaml")
    etats = {nom: {"etat": src.etat.value, "motif": src.motif_indisponible}
             for nom, src in _registre().sources.items()}
    proche = _cfg("config/ponderations.yaml").get("effort", {}).get(
        "distance_depot_confortable_km", 50)
    cx = ouvrir(_base(a), lecture_seule=True)
    r = rapport_mod.construire(cx, mode, limite_top=a.top, etats_sources=etats,
                               cible=profil.get("cible_economique", {}), proche_km=proche)
    texte = r.en_texte(avec_fiches=not a.resume)

    dossier = _P(a.sortie)
    dossier.mkdir(parents=True, exist_ok=True)
    horo = r.genere_le.replace(":", "").replace("-", "")[:15]
    chemin = dossier / f"rapport-{mode.value.lower().replace('é', 'e')}-{horo}.txt"
    chemin.write_text(texte, encoding="utf-8")

    print(texte)
    print(f"\nRapport écrit dans {chemin}")
    return 0


def cmd_vocabulaire(a) -> int:
    """Les formulations rencontrées que l'adaptateur ne savait pas lire.

    Chacune bloque une opportunité en ÉTAT INCONNU. Les trancher, c'est
    débloquer toutes les prochaines — et c'est un travail humain, pas une
    devinette de la machine.
    """
    from .procedure import INTERPRETATIONS, reviser

    if a.trancher:
        from .procedure import concerne
        cx = ouvrir(_base(a))
        source, champ, expression, sens = a.trancher

        # AVANT de trancher : qui est concerné, et dans quel état sont-ils.
        avant = {l["avis_id"]: (l["intitule"], l["etat_procedure"])
                 for l in concerne(cx, source, champ, expression)}
        version = reviser(cx, source, champ, expression, sens, motif=a.motif or "",
                          par=a.par or "manuel")
        cx.commit()
        print(f"« {expression} » ({source}/{champ}) → {sens}  [version {version}]")
        print("L'ancienne lecture est archivée, pas effacée.")

        if not avant:
            print("\nAucune opportunité en base ne dépend de cette expression.")
            return 0
        print(f"\n{len(avant)} opportunité(s) dépendent de cette lecture :")
        for _, (titre, etat) in list(avant.items())[:20]:
            print(f"  {etat or 'INCONNU':<12} {(titre or '')[:56]}")
        if not a.recalculer:
            print("\nRIEN N'A ÉTÉ RECALCULÉ. Relance avec --recalculer pour les "
                  "réévaluer\net voir lesquelles changent d'état.")
            return 0
        return _recalculer(cx, source, avant)

    cx = ouvrir(_base(a), lecture_seule=True)
    lignes = cx.execute(
        "SELECT source, champ, expression, contexte, occurrences, interpretation,"
        " revise_le FROM vocabulaire ORDER BY interpretation IS NOT NULL,"
        " occurrences DESC").fetchall()
    if not lignes:
        print("Aucune formulation inconnue rencontrée.")
        return 0
    a_trancher = [l for l in lignes if l["interpretation"] is None]
    print(f"{len(lignes)} formulation(s) mémorisée(s), "
          f"{len(a_trancher)} restent à trancher\n")
    for l in lignes:
        sens = l["interpretation"] or "À TRANCHER"
        print(f"  {l['source']:<12} {l['champ']:<18} ×{l['occurrences']:<4} "
              f"{sens:<12} « {l['expression'][:40]} »")
        if l["contexte"]:
            print(f"  {'':<12} vu dans : {l['contexte'][:64]}")
    if a_trancher:
        print(f"\nPour trancher "
              f"(interprétations : {', '.join(sorted(INTERPRETATIONS))}) :")
        l = a_trancher[0]
        print(f"  python -m radar.cli vocabulaire --trancher "
              f"{l['source']} {l['champ']} \"{l['expression']}\" postulable")
    return 1 if a_trancher else 0


def _recalculer(cx, source: str, avant: dict) -> int:
    """Rejoue les opportunités concernées depuis le BRUT conservé.

    Rien n'est modifié en silence : la liste des fiches qui changent d'état est
    affichée avant/après. Et la transition est marquée « révision de
    vocabulaire », pas « collecte » — sinon on croirait que le marché a bougé
    alors que c'est notre lecture qui a changé.
    """
    from . import transitions as tr
    from .adaptateur import Adaptateur, vers_opportunite
    from .base import reponses_fusionnees
    from .chaine import _ecrire_opportunite
    from .procedure import version_vocabulaire

    adaptateur, cfg = _source(source)
    defauts = {"signal": cfg.get("signal"), "secteur": cfg.get("secteur_par_defaut")}
    mot = _moteur(cx)
    version = version_vocabulaire(cx, source)

    changements = []
    for avis_id, (titre, ancien) in avant.items():
        brut = reponses_fusionnees(cx, avis_id)
        if not brut:
            continue
        opp = vers_opportunite(adaptateur, brut, source, defauts)
        r = mot.analyser(opp)
        transition = tr.constater(cx, avis_id, r.lecture, source,
                                  origine=tr.REVISION, version_vocabulaire=version)
        _ecrire_opportunite(cx, avis_id, opp, r)
        if transition is not None:
            changements.append((titre, ancien, r.lecture.etat.value,
                                r.classement.action.value))
    cx.commit()

    if not changements:
        print("\nAucune fiche ne change d'état.")
        return 0
    print(f"\n{len(changements)} fiche(s) changent d'état :")
    for titre, ancien, nouveau, action in changements:
        print(f"  {(ancien or 'INCONNU'):<12} → {nouveau:<12} {action:<26} "
              f"{(titre or '')[:38]}")
    print("\nCes transitions sont marquées « révision de vocabulaire » :")
    print("le marché n'a pas bougé, c'est notre lecture qui a changé.")
    print("Aucune alerte commerciale n'a été émise.")
    return 0


def cmd_incidents(a) -> int:
    """Les avis qui n'ont pas pu être traités — conservés, jamais perdus."""
    cx = ouvrir(_base(a), lecture_seule=True)
    lignes = cx.execute(
        "SELECT ligne, source, reference, etape, motif, mode, cree_le FROM incidents"
        " ORDER BY id DESC LIMIT ?", (a.limite,)).fetchall()
    if not lignes:
        print("Aucun incident enregistré.")
        return 0
    print(f"{len(lignes)} incident(s) — le contenu brut de chacun est conservé en base\n")
    for l in lignes:
        print(f"  ligne {l['ligne'] or '?':<5} {l['source']:<10} {l['etape']:<14} "
              f"{(l['reference'] or '—')[:26]:<28} {l['motif'][:44]}")
    return 0


def _registre():
    """Le registre déclaré, AVANT toute consultation. Une source y entre à
    l'état JAMAIS CONSULTÉE et rien d'autre qu'une consultation réelle ne le
    change."""
    from .decouverte import charger_connecteur
    from .registre import Registre

    reg = Registre()
    cat = _cfg("config/sources.yaml")["categories"]
    for famille, spec in cat.items():
        for nom in spec.get("sources", []):
            reg.declarer(nom, famille, "fichier")
    google = reg.declarer("google", "decouverte", "moteur_recherche")
    c = charger_connecteur()
    if not c.disponible:
        google.indisponible(c.motif_indisponibilite)
    for nom in ("bourses_de_fret",):
        reg.declarer(nom, "transport", "api").indisponible("aucun abonnement fourni")
    return reg


def cmd_sources(a) -> int:
    """Le registre : qui a été consulté, quand, et avec quel rendement."""
    reg = _registre()
    print(reg.rapport())
    print()
    print(reg.rendement())
    return 0


def cmd_requetes(a) -> int:
    """Les requêtes de découverte réellement générées."""
    from .decouverte import Generateur
    g = Generateur(_cfg("config/decouverte.yaml"))
    reqs = g.generer()
    print(f"{len(reqs)} requêtes générées · {a.limite} affichées, par priorité\n")
    for q in reqs[:a.limite]:
        print(f"  [{q.priorite():5.1f}] {q.famille:20} {q.zone:18} {q.texte[:60]}")
    print("\nAucune n'a été exécutée : le connecteur Google est indisponible.")
    return 0


def cmd_apprendre(a) -> int:
    """Ce que le radar a appris — calculé sur la base, jamais estimé."""
    cx = ouvrir(_base(a), lecture_seule=True)
    print(appr.apprendre(cx).rapport())
    return 0


def cmd_notifier(a) -> int:
    cx = ouvrir(_base(a))
    envoi.reprendre_interrompus(cx)
    if a.pour_de_vrai:
        print("aucun transport configuré dans cet environnement", file=sys.stderr)
        return 3
    en_attente = envoi.a_envoyer(cx)
    print(f"{len(en_attente)} message(s) en attente (essai à blanc, rien n'est envoyé)")
    for l in en_attente:
        print(f"  · {l['source']}/{l['ref_source']}")
    return 0


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="Radar commercial logistique")
    p.add_argument("--base", default=None,
                   help="par défaut : radar-demo.sqlite3 ou radar-reel.sqlite3 selon le mode")
    p.add_argument("--reel", action="store_true",
                   help="MODE RÉEL : refuse toute donnée sans preuve de collecte")
    s = p.add_subparsers(dest="cmd", required=True)

    r = s.add_parser("recenser", help="mesurer les clés réelles d'une source")
    r.add_argument("--source", required=True); r.add_argument("--echantillon", required=True)
    r.set_defaults(fn=cmd_recenser)

    so = s.add_parser("sonder", help="mesurer le marché avant de construire")
    so.add_argument("--source", required=True); so.add_argument("--entree", required=True)
    so.set_defaults(fn=cmd_sonder)

    t = s.add_parser("traiter", help="traiter un lot")
    t.add_argument("--source", required=True); t.add_argument("--entree", required=True)
    t.set_defaults(fn=cmd_traiter)

    o = s.add_parser("opportunites", help="ce sur quoi on peut candidater")
    o.add_argument("--complet", action="store_true")
    o.add_argument("--type", choices=["direct", "renforcement", "a_construire", "prospect"],
                   help="filtrer sur une catégorie")
    o.add_argument("--moteur", choices=["capter", "developper"],
                   help="CAPTER = agir maintenant · DEVELOPPER = action commerciale")
    o.set_defaults(fn=cmd_opportunites)

    en = s.add_parser("entreprises", help="entreprises découvertes et surveillées")
    en.set_defaults(fn=cmd_entreprises)

    su = s.add_parser("surveiller", help="ajouter manuellement une entreprise")
    su.add_argument("nom"); su.add_argument("--domaine")
    su.set_defaults(fn=cmd_surveiller)

    bo = s.add_parser("boucle", help="lancer la boucle de découverte")
    bo.add_argument("--profondeur", type=int, default=2)
    bo.add_argument("--budget", type=int, default=100)
    bo.set_defaults(fn=cmd_boucle)

    ra = s.add_parser("rapport", help="rapport de mesure sur les données en base")
    ra.add_argument("--top", type=int, default=20)
    ra.add_argument("--resume", action="store_true", help="sans les fiches détaillées")
    ra.add_argument("--sortie", default="rapports")
    ra.set_defaults(fn=cmd_rapport)

    vo = s.add_parser("vocabulaire", help="formulations de statut rencontrées et non comprises")
    vo.add_argument("--trancher", nargs=4,
                    metavar=("SOURCE", "CHAMP", "EXPRESSION", "INTERPRÉTATION"))
    vo.add_argument("--motif", help="pourquoi cette interprétation")
    vo.add_argument("--par", help="qui a tranché")
    vo.add_argument("--recalculer", action="store_true",
                    help="réévaluer les opportunités concernées et montrer ce qui change")
    vo.add_argument("--reel", action="store_true")
    vo.add_argument("--base")
    vo.set_defaults(fn=cmd_vocabulaire)

    inc = s.add_parser("incidents", help="avis non traités, conservés avec leur motif")
    inc.add_argument("--limite", type=int, default=30)
    inc.set_defaults(fn=cmd_incidents)

    so2 = s.add_parser("sources", help="registre des sources et leur état réel")
    so2.set_defaults(fn=cmd_sources)

    rq = s.add_parser("requetes", help="requêtes de découverte générées")
    rq.add_argument("--limite", type=int, default=20)
    rq.set_defaults(fn=cmd_requetes)

    ap = s.add_parser("apprendre", help="ce que le radar a appris du marché")
    ap.set_defaults(fn=cmd_apprendre)

    c = s.add_parser("calendrier", help="remises en concurrence calculées")
    c.set_defaults(fn=cmd_calendrier)

    n = s.add_parser("notifier", help="vider la file d'envoi")
    n.add_argument("--pour-de-vrai", action="store_true")
    n.set_defaults(fn=cmd_notifier)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(principal())
