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
    #
    # Les noms viennent de la BASE, jamais d'une liste écrite ici : un moteur
    # dont le nom aurait été oublié dans une liste en dur perdrait son
    # vocabulaire de procédure en silence, et ses états deviendraient INCONNU
    # sans que personne ne sache pourquoi. Cela vaut aussi pour les exports
    # importés, dont le nom ne peut pas être connu à l'avance.
    if cx is not None:
        for l in cx.execute("SELECT DISTINCT source FROM trouvailles"):
            sortie.setdefault(l["source"], sortie.get("recherche"))
        for l in cx.execute("SELECT DISTINCT source FROM avis"):
            sortie.setdefault(l["source"], sortie.get("recherche"))
    return sortie


def _moteurs_declares():
    """Les moteurs de DÉCOUVERTE tels qu'ils sont déclarés, disponibles ou non.

    L'ordre est un ordre d'ESSAI, pas un classement de qualité : il sert au
    diagnostic et à l'observabilité, jamais au score commercial. Aucun moteur
    n'a de droit acquis, et aucun ne vaut « mieux » qu'un autre ici.
    """
    from .moteurs_recherche import depuis_environnement
    return depuis_environnement()


def _moteur(cx=None) -> Moteur:
    # Le registre d'entreprises vient de la BASE, pas d'un dictionnaire vide :
    # ce que le radar a découvert hier doit être là aujourd'hui.
    from .entreprises import charger as charger_entreprises
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"),
                  entreprises=charger_entreprises(cx) if cx is not None else None,
                  vocabulaires=_vocabulaires(cx))


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
    from . import suivi as sui
    for l in lignes:
        # Le suivi se lit MAINTENANT, il ne se fige pas dans la fiche : celle-ci
        # est un instantané écrit au calcul, le statut commercial bouge après.
        etat_com = sui.lire(cx, l["avis_id"])
        if a.complet:
            print(l["fiche"])
            print("\n" + "\n".join(etat_com.en_lignes()))
            fil = sui.fil(cx, l["avis_id"])
            if fil:
                print("PARCOURS      " + "\n              ".join(fil))
            print("\n" + "─" * 66 + "\n")
        else:
            emoji = {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
                     "PROSPECT": "🔵"}.get(l["type"], "·")
            statut = etat_com.statut.value if etat_com.statut else "NOUVELLE"
            print(f"{emoji} [{l['score']:3}] {statut:<16} "
                  f"{(etat_com.prochaine_action_le or '—'):<11} "
                  f"{(l['action'] or ''):<24} {(l['intitule'] or '')[:38]}")
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
    from .entreprises import charger as charger_ent, enregistrer as enregistrer_ent
    cx = ouvrir(_base(a))
    # On PART du registre existant : une entreprise déjà connue est complétée,
    # pas remplacée. INSERT OR REPLACE aurait effacé ses compteurs et son
    # historique de visites.
    reg = charger_ent(cx)
    deja = reg._retrouver(a.nom, a.domaine)[1] is not None
    e = reg.surveiller(a.nom, domaine=a.domaine, motif=Motif.MANUEL)
    enregistrer_ent(cx, reg)
    cx.commit()
    if deja:
        print("(entreprise déjà connue — complétée, pas dupliquée)")
    print(f"« {e.nom} » est désormais SURVEILLÉE.")

    # CE QUI EST POSSIBLE MAINTENANT, sans le moindre moteur de recherche.
    from . import pages as mod_pages
    connues = mod_pages.a_surveiller(cx, entreprise=e.cle)
    print(f"\n{len(connues)} page(s) déjà connue(s) pour cette entreprise — "
          "surveillables directement, sans moteur de recherche :")
    for pg in connues:
        print(f"  · {pg.acces.value:<17} {pg.url}")
    if not connues:
        print("  (aucune — déclare une page avec `radar page --entreprise "
              f"{e.cle} --url ...`)")
        print("  Aucune URL n'est devinée : posséder un domaine ne prouve pas")
        print("  qu'une page partenaires existe.")

    # LA DÉCOUVERTE DE PAGES NOUVELLES est un COMPLÉMENT. Son absence ne
    # suspend pas la surveillance de ce qui est déjà connu.
    reqs = Generateur(_cfg("config/decouverte.yaml")).pour_entreprise(e.nom, e.domaine)
    moteurs = _moteurs_declares()
    if moteurs.disponible() is None:
        print(f"\nDÉCOUVERTE COMPLÉMENTAIRE NON DISPONIBLE — "
              f"{len(reqs)} recherche(s) ciblée(s) restent en attente d'un moteur.")
        print("La surveillance des pages ci-dessus n'en dépend pas.")
    else:
        print(f"\n{len(reqs)} recherche(s) ciblée(s) de découverte complémentaire :")
        for q in reqs:
            print(f"  · {q.texte}")
    return 0


def cmd_recoupement(a) -> int:
    """Ce que chaque moteur apporte — volume ET apport propre, côte à côte."""
    from . import recoupement as mod
    cx = ouvrir(_base(a), lecture_seule=True)
    # Les moteurs DÉCLARÉS mais indisponibles : leurs résultats sont NON
    # MESURÉS, jamais zéro. On ne les a pas interrogés.
    declares = {m.nom: m.motif_indisponibilite
                for m in _moteurs_declares().moteurs if not m.disponible}
    print(mod.rapport(cx, declares=declares))
    if a.groupes:
        print()
        print("GROUPES MULTI-SOURCES — l'historique complet de chaque page")
        for g in mod.grouper(__import__("radar.trouvailles", fromlist=["toutes"])
                             .toutes(cx)):
            if not g.multi_source:
                continue
            print(f"\n  {g.cle}")
            for ligne in g.historique():
                print(f"    {ligne}")
    return 0


def cmd_trouvailles(a) -> int:
    """Ce qu'un moteur a MONTRÉ — et ce qui n'a jamais été lu."""
    from . import trouvailles as mod
    cx = ouvrir(_base(a), lecture_seule=True)
    print(mod.rapport(cx))
    if a.detail:
        print()
        for t in mod.toutes(cx, limite=a.limite):
            print("  " + t.ligne())
    return 0


def cmd_import_recherche(a) -> int:
    """Un export produit HORS RADAR entre dans la chaîne — et va jusqu'au bout.

        fichier.json/.csv → trouvailles → entreprises → pages candidates
                          → analyse commerciale → opportunités → 🟢🟡🟣🔵🔴

    Le radar n'a interrogé aucun moteur. Il ne le prétendra jamais : la source
    reste marquée « import: », et le journal des exécutions porte
    « EXÉCUTÉ HORS RADAR » en toutes lettres.
    """
    from . import execution as mod_execution, import_externe as imp, parcours
    from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE

    # Un import porte des résultats RÉELS : un vrai moteur les a rendus, sur le
    # vrai web. Il n'y a donc pas de choix de mode à faire, et en laisser un
    # ouvrirait la porte à des lignes réelles écrites dans la base de
    # démonstration — exactement la confusion que le projet interdit.
    mode = Mode.REEL
    base = a.base or mode.base_par_defaut
    # Le bandeau générique du mode RÉEL dit « données réellement collectées ».
    # C'est vrai d'une collecte, pas d'un import : le radar n'a rien collecté
    # et n'a interrogé personne. On l'écrit donc autrement, plutôt que de
    # laisser un bandeau juste-à-côté faire une affirmation fausse.
    largeur = 68
    print("╔" + "═" * largeur + "╗")
    for ligne in (f"MODE : RÉEL — {imp.PROVENANCE}",
                  "Un moteur externe a rendu ces résultats. Le radar n'a",
                  "interrogé personne et n'a lu aucune page."):
        print("║  " + ligne.ljust(largeur - 2) + "║")
    print("╚" + "═" * largeur + "╝")
    print(f"base : {base}")
    cx = ouvrir(base)
    try:
        bilan = imp.importer(cx, a.fichier)
    except imp.ImportInvalide as e:
        print(f"IMPORT REFUSÉ — {e}", file=sys.stderr)
        return 2
    print(bilan.resume())

    if a.sans_analyse:
        print()
        print(mod_execution.rapport(cx))
        cx.commit()
        return 0

    adaptateur, cfg = _source("recherche")
    defauts = {"signal": cfg.get("signal"),
               "secteur": cfg.get("secteur_par_defaut"),
               "circuit": CIRCUIT_DECOUVERTE}
    p = parcours.executer(cx, _moteur(cx), adaptateur, mode=mode, defauts=defauts)
    cx.commit()
    print()
    print(parcours.rapport(cx, p, limite_top=a.top))
    return 0


def cmd_collecter(a) -> int:
    """Les pages à lire, indice d'adresse d'abord — ou l'import d'une collecte.

    Le radar NE PEUT PAS lire ces pages : l'accès réseau est fermé, mesuré et
    re-mesuré. Il dit donc lesquelles lire, et reçoit ce qu'un poste extérieur
    a lu. Même discipline que pour la recherche.
    """
    from . import collecte_importee as col
    cx = ouvrir(a.base or Mode.REEL.base_par_defaut)
    moteur = _moteur(cx)
    if not a.fichier:
        print(col.rapport_a_collecter(cx, moteur, limite=a.limite))
        return 0
    try:
        bilan = col.importer(cx, a.fichier, moteur)
    except col.CollecteInvalide as e:
        print(f"COLLECTE REFUSÉE — {e}", file=sys.stderr)
        return 2
    cx.commit()
    print(bilan.resume())
    return 0


def cmd_requetes_prioritaires(a) -> int:
    """Les requêtes à exécuter DEHORS, par famille. Le radar n'en lance aucune.

    Ce n'est pas un ordre de valeur : c'est un ordre d'exploration, utile quand
    le budget de requêtes est limité. Aucune famille ne vaut mieux qu'une autre.
    """
    cfg = _cfg("config/requetes-prioritaires.yaml")
    familles = cfg.get("familles") or {}
    if a.brut:
        for f in familles.values():
            for r in f.get("requetes") or []:
                print(r)
        return 0
    total = 0
    print("REQUÊTES PRIORITAIRES — à exécuter HORS RADAR")
    print("=" * 72)
    for cle, f in familles.items():
        if a.famille and not cle.upper().startswith(a.famille.upper()):
            continue
        print()
        print(f"{cle}  —  {f.get('libelle', '')}")
        if f.get("avertissement"):
            print("  ⚠ " + " ".join(str(f["avertissement"]).split()))
        for r in f.get("requetes") or []:
            total += 1
            print(f"    {r}")
    geo = (cfg.get("geographie") or {})
    print()
    print("COUCHES GÉOGRAPHIQUES — ordre d'EXPLORATION, jamais de valeur")
    for couche in geo.get("ordre_exploration") or []:
        suffixes = couche.get("suffixes") or []
        etat = ", ".join(suffixes) if suffixes else "À COMPLÉTER par l'exploitant"
        print(f"    {couche.get('couche', '?'):<22} {etat}")
    print()
    print("  La distance ne supprime JAMAIS une opportunité : elle entre dans")
    print("  l'effort opérationnel et le classement, et nulle part ailleurs.")
    print()
    print(f"{total} requête(s). Le radar n'en a exécuté AUCUNE.")
    print("Voir validation/PROTOCOLE-EXPORT-EXTERNE.md pour la marche à suivre.")
    return 0


def cmd_identifier(a) -> int:
    """Dire au radar DE QUI il s'agit — ou lister ce qu'il ignore.

    Le radar ne devine jamais une identité ni une URL. Cette commande est la
    seule voie ouverte aujourd'hui : l'exploitant apporte la preuve, elle est
    datée et conservée.
    """
    from . import identite as mod_id
    from .entreprises import charger as charger_ent
    cx = ouvrir(_base(a))

    if not a.entreprise:
        print(mod_id.rapport(cx))
        return 0

    reg = charger_ent(cx)
    cle, e = reg._retrouver(a.entreprise, a.domaine)
    if e is None:
        print(f"« {a.entreprise} » n'est pas au registre des entreprises.",
              file=sys.stderr)
        print("Le radar n'invente pas d'entreprise : ajoute-la d'abord avec "
              "`radar surveiller`.", file=sys.stderr)
        return 2

    if a.candidat:
        # PLUSIEURS ENTITÉS PORTENT CE NOM. On les conserve, on ne choisit pas.
        candidats = [mod_id.Candidat(nom=c, source=mod_id.EXPLOITANT)
                     for c in a.candidat]
        ident = mod_id.proposer(cx, cle, candidats)
    elif a.trancher:
        if not a.preuve:
            print("Trancher une ambiguïté EXIGE une preuve : --preuve",
                  file=sys.stderr)
            return 2
        ident = mod_id.trancher(cx, cle, a.trancher,
                                source=mod_id.EXPLOITANT, preuve=a.preuve)
    elif a.sans_site:
        ident = mod_id.sans_site(cx, cle, source=mod_id.EXPLOITANT,
                                 preuve=a.preuve or "constaté par l'exploitant")
    elif a.domaine or a.bce:
        if not a.preuve:
            print("Confirmer une identité EXIGE une preuve relisible : --preuve",
                  file=sys.stderr)
            print("Un domaine seul ne dit pas à QUELLE entité il appartient.",
                  file=sys.stderr)
            return 2
        ident = mod_id.confirmer(cx, cle, source=mod_id.EXPLOITANT,
                                 preuve=a.preuve, bce=a.bce, domaine=a.domaine)
    else:
        ident = mod_id.lire(cx, cle)

    cx.commit()
    print(f"{e.nom}")
    print(f"  identité     {ident.ligne()}")
    if ident.preuve:
        print(f"  preuve       {ident.preuve}")
    if ident.bce:
        print(f"  BCE/KBO      {ident.bce}")
    print(f"  site         {ident.domaine or 'NON IDENTIFIÉ'}")
    for c in ident.candidats:
        print(f"  candidat     {c.ligne()}")
    if ident.etat is mod_id.Etat.AMBIGUE:
        print("\nAucun candidat n'a été choisi. Pour trancher, il faut une")
        print("information qui DISTINGUE réellement :")
        print(f"  radar identifier \"{e.nom}\" --trancher \"…\" --preuve \"…\"")
    elif not ident.domaine and ident.etat.identifiee:
        print("\nIDENTITÉ CONNUE, SITE NON IDENTIFIÉ — c'est un état valide.")
        print("Aucune URL n'est déduite d'un nom d'entreprise.")
    return 0


def cmd_circuits(a) -> int:
    """DÉCOUVERTE et SURVEILLANCE, comptées SÉPARÉMENT.

    Mélanger les deux chiffres rendrait impossible la seule question qui
    compte : cette opportunité, l'avons-nous DÉCOUVERTE ou SURVEILLÉE ?
    """
    from . import circuit as mod_circuit, pages as mod_pages
    from .pages import Acces
    cx = ouvrir(_base(a), lecture_seule=True)

    def compte(sql, args=()):
        return cx.execute(sql, args).fetchone()[0]

    # Une base antérieure à la notion de circuit n'a pas la colonne. Elle
    # affiche alors NON MESURÉ — surtout pas 0, qui ferait croire à une mesure.
    a_circuit = "circuit" in {l[1] for l in cx.execute("PRAGMA table_info(provenances)")}

    def par_circuit(valeur):
        if not a_circuit:
            return "NON MESURÉ"
        return compte("SELECT count(DISTINCT avis_id) FROM provenances WHERE circuit=?",
                      (valeur,))

    print("DÉCOUVERTE — ce que nous ne connaissions pas")
    print("=" * 72)
    moteurs = _moteurs_declares()
    for m in moteurs.moteurs:
        etat = "DISPONIBLE" if m.disponible else f"NON DISPONIBLE — {m.motif_indisponibilite}"
        print(f"  moteur {m.nom:<10} {etat}")
    decouvertes = par_circuit(mod_circuit.DECOUVERTE)
    print(f"  recherches exécutées      {compte('SELECT count(*) FROM requetes')}")
    print(f"  opportunités découvertes  {decouvertes}")
    print(f"  entreprises au registre   {compte('SELECT count(*) FROM entreprises')}"
          "   (toutes origines confondues)")
    if moteurs.disponible() is None:
        print("\n  Aucun moteur accessible : la DÉCOUVERTE WEB est indisponible.")
        print("  Cela ne dit RIEN des autres circuits, qui continuent.")

    print()
    print("SURVEILLANCE — ce que nous connaissons déjà")
    print("=" * 72)
    pages = mod_pages.a_surveiller(cx)
    surveillees = compte("SELECT count(*) FROM entreprises WHERE etat='SURVEILLÉE'")
    connues = par_circuit(mod_circuit.CONNUE)
    print(f"  entreprises surveillées   {surveillees}")
    print(f"  pages surveillées         {len(pages)}")
    for etat in Acces:
        n = sum(1 for p in pages if p.acces is etat)
        print(f"    {etat.value:<18}      {n}")
    print(f"  pages modifiées           "
          f"{compte(chr(39).join(['SELECT count(*) FROM filigrane WHERE source LIKE ', 'page:%', '']))}"
          "   (empreintes mémorisées)")
    print(f"  opportunités générées     {connues}")

    print()
    print("Ces deux tableaux ne se mélangent jamais. Le circuit d'une")
    print("opportunité n'entre dans AUCUN score : même besoin, même score.")
    return 0


def cmd_page(a) -> int:
    """Déclarer une page à surveiller — ou lister celles qu'on connaît.

    Aucune URL n'est devinée : une page entre au registre parce qu'elle a été
    rencontrée, pas parce qu'un domaine existe.
    """
    from . import circuit as mod_circuit, pages as mod_pages
    cx = ouvrir(_base(a))
    if not a.url:
        print(mod_pages.rapport(cx))
        return 0
    if a.ecarter:
        pg = mod_pages.ecarter(cx, a.url, a.ecarter)
        cx.commit()
        print(f"page ÉCARTÉE : {pg.url}\n  motif : {pg.raison}")
        return 0

    # Une URL donnée EXPLICITEMENT par l'exploitant est une décision : elle
    # entre directement en SURVEILLÉE. Une page seulement RENCONTRÉE reste
    # CANDIDATE tant que personne n'a décidé de la suivre.
    pg = mod_pages.rencontrer(cx, a.url, entreprise=a.entreprise,
                              provenance=a.provenance, source="exploitant",
                              circuit=mod_circuit.CONNUE, libelle=a.libelle)
    if not a.candidate:
        pg = mod_pages.promouvoir(cx, a.url,
                                  a.raison or "désignée par l'exploitant")
    cx.commit()
    print(f"page : {pg.url}")
    print(f"  statut       {pg.statut.value}"
          + (f"  — {pg.raison}" if pg.raison else ""))
    print(f"  accès        {pg.acces.value}")
    print(f"  entreprise   {pg.entreprise or '—'}")
    print(f"  provenances  "
          + " · ".join(f"{x['source']}/{x['circuit'] or '—'}" for x in pg.provenances))
    if pg.surveillee:
        print("\nElle sera consultée par `radar veille`, sans aucun moteur de recherche.")
    else:
        print("\nCANDIDATE : rencontrée, pas encore retenue. "
              "`radar page --url ... --raison ...` la fait passer surveillée.")
    return 0


def cmd_veille(a) -> int:
    """LE CIRCUIT SOURCE CONNUE — revisiter les pages déjà connues.

    Ne consulte AUCUN moteur de recherche. L'indisponibilité de Google, de
    Brave ou de n'importe quel autre moteur ne change rien à cette commande.
    """
    from .boucle import Veille
    from . import circuit as mod_circuit, collecte_directe, pages as mod_pages
    cx = ouvrir(_base(a))
    liste = mod_pages.a_surveiller(cx, entreprise=a.entreprise, limite=a.limite)
    if not liste:
        print("Aucune page surveillée — aucune n'a été déclarée.")
        print("Une page n'est jamais supposée à partir d'un domaine :")
        print("  radar page --url https://exemple.be/partenaires --entreprise exemple.be")
        return 0
    if not a.pour_de_vrai:
        print(f"{len(liste)} page(s) seraient consultées (essai à blanc, "
              "aucune requête réseau) :")
        for pg in liste:
            print(f"  · {pg.acces.value:<17} {pg.url}")
        return 0
    from . import liens as mod_liens, normalisation
    from .chaine import traiter
    from .page import lire as lire_page
    profil = _cfg("sources/page_web.yaml")
    mot = _moteur(cx)
    mode = _mode(a)
    print(mode.bandeau())
    domaines = {e.domaine for e in mot.entreprises.entreprises.values() if e.domaine}
    recolte = {"candidates": 0, "promues": 0, "deja_connues": 0}

    def analyser(collecte, page):
        """La page réellement lue entre dans la chaîne, telle quelle.

        La chaîne décide seule s'il y a un besoin : ce raccord n'ajoute
        aucune règle et n'en retire aucune.
        """
        opp, _ = normalisation.depuis_collecte(
            collecte, profil, source="entreprise",
            circuit=mod_circuit.CONNUE)
        if opp is None:
            return 0
        b = traiter(cx, mot, [opp], mode=mode)

        # LES LIENS DE LA PAGE — filtrés, jamais tous retenus. Un lien
        # découvert devient CANDIDAT ; seul un indice fort le fait surveiller.
        if not a.sans_liens:
            lec = lire_page(collecte.octets.decode("utf-8", "replace"), profil)
            candidats = mod_liens.selectionner(
                lec.liens, collecte.url, mot.ontologie, mot.roles,
                domaines_connus=domaines)
            bilan = mod_pages.depuis_liens(cx, candidats, entreprise=page.entreprise,
                                           circuit=mod_circuit.CONNUE)
            for c, v in bilan.items():
                recolte[c] += v
        return b.capter + b.developper

    trace = Veille(cx, collecte_directe.recuperer, analyser=analyser,
                   profil=profil, ontologie=mot.ontologie,
                   detecteur=mot.roles).passer(liste)
    print(trace.resume())
    if not a.sans_liens:
        print()
        print("LIENS RÉCOLTÉS SUR LES PAGES LUES")
        print(f"  pages candidates nouvelles   {recolte['candidates']}")
        print(f"  déjà connues                 {recolte['deja_connues']}")
        print(f"  promues sur indice fort      {recolte['promues']}")
        print("  Un lien découvert n'est PAS une page surveillée, et une page")
        print("  n'est pas une entreprise.")
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
    # Ce lot vient d'un MOTEUR : c'est le circuit DÉCOUVERTE. L'étiquette suit
    # l'opportunité pour la traçabilité et les métriques — jamais pour le score.
    from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE
    defauts = {"signal": cfg_src.get("signal"), "secteur": cfg_src.get("secteur_par_defaut"),
               "circuit": CIRCUIT_DECOUVERTE}

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
    # TOUS les moteurs déclarés entrent au registre, dans l'ordre où ils y
    # sont déclarés. Cet ordre est un ordre d'ESSAI : il ne dit rien de la
    # qualité des résultats et n'entre dans aucun score.
    for m in _moteurs_declares().moteurs:
        source = reg.declarer(m.nom, "decouverte", "moteur_recherche")
        if not m.disponible:
            source.indisponible(m.motif_indisponibilite)
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
    moteurs = _moteurs_declares()
    if moteurs.disponible() is None:
        print("\nMOTEURS DE DÉCOUVERTE : aucun moteur accessible.")
        for m in moteurs.moteurs:
            print(f"  {m.nom:<10} {m.motif_indisponibilite or 'indisponible'}")
        print("\nAucune requête n'a été exécutée. Les SOURCES DIRECTES ne sont")
        print("pas concernées : elles ne passent par aucun moteur.")
    else:
        print(f"\nMoteur disponible : {moteurs.disponible().nom}. "
              "Aucune requête n'a été exécutée par cette commande.")
    return 0


def cmd_apprendre(a) -> int:
    """Ce que le radar a appris — calculé sur la base, jamais estimé."""
    cx = ouvrir(_base(a), lecture_seule=True)
    print(appr.apprendre(cx).rapport())
    return 0


def cmd_notifier(a) -> int:
    cx = ouvrir(_base(a))
    repris = envoi.reprendre_interrompus(cx)
    if repris:
        print(f"{repris} envoi(s) interrompu(s) rangé(s) en AMBIGU — jamais réémis")
    if not a.pour_de_vrai:
        en_attente = envoi.a_envoyer(cx)
        print(f"{len(en_attente)} message(s) en attente (essai à blanc, rien n'est envoyé)")
        for l in en_attente:
            print(f"  · {l['source']}/{l['ref_source']}")
        return 0

    # LE TRANSPORT RÉEL. Un fichier, parce qu'il ne demande ni réseau ni
    # compte : le radar sort quelque chose le jour où on le branche. Il se
    # remplace par un courriel ou un webhook sans toucher à la file.
    from .alerte import TransportFichier
    transport = TransportFichier(a.dossier)
    compte = envoi.vider(cx, transport)
    print(f"ALERTES — dossier {Path(a.dossier).resolve()}")
    print(f"  délivrées {compte['delivre']} · échecs {compte['echec']} · "
          f"ambiguës {compte['ambigu']}")
    print(f"  fichiers écrits      {len(transport.ecrits)}")
    print(f"  déjà sorties (sceau) {len(transport.deja_sortis)}")
    for chemin in transport.ecrits[:10]:
        print(f"    → {chemin}")
    return 0 if not compte["echec"] else 1


def cmd_suivre(a) -> int:
    """Poser le statut commercial d'une opportunité, et rien d'autre.

    Le statut de la RELATION. Il ne touche ni l'état de procédure, ni le
    score, ni le CA, ni la nature, ni la classification : ces valeurs sont
    calculées à partir de la source, et aucune décision commerciale ne doit
    les déplacer.
    """
    from . import suivi
    cx = ouvrir(_base(a))
    try:
        avis_id = suivi.resoudre(cx, a.reference)
    except suivi.OpportuniteIntrouvable as e:
        print(f"{e}", file=sys.stderr)
        return 2

    avant = suivi.lire(cx, avis_id)
    if not a.statut:                       # sans statut : on lit, on ne change rien
        ligne = cx.execute("SELECT intitule, acheteur, action, etat_procedure"
                           " FROM opportunites WHERE avis_id=?", (avis_id,)).fetchone()
        print(f"{ligne['intitule']}  —  {ligne['acheteur'] or 'A_VERIFIER'}")
        print(f"  ÉTAT PROCÉDURE   {ligne['etat_procedure'] or 'HORS PROCÉDURE'}")
        print(f"  ACTION MÉTIER    {ligne['action']}")
        for l in avant.en_lignes():
            print(f"  {l}")
        fil = suivi.fil(cx, avis_id)
        print("\n  PARCOURS COMMERCIAL")
        for etape in fil or ["    aucun mouvement enregistré"]:
            print(f"    {etape}")
        return 0

    try:
        apres = suivi.marquer(cx, avis_id, a.statut, motif=a.motif,
                              prochaine_action_le=a.prochaine,
                              dernier_contact_le=a.contact, par=a.par)
    except (suivi.StatutInconnu, suivi.DateInvalide) as e:
        print(f"{e}", file=sys.stderr)
        return 2
    cx.commit()

    depuis = avant.statut.value if avant.statut else "jamais regardée"
    print(f"{depuis} → {apres.statut.value}")
    for l in apres.en_lignes():
        print(f"  {l}")
    return 0


def cmd_validation(a) -> int:
    """Ce qui est prouvé, et par quoi. Deux compteurs, jamais mélangés."""
    from . import validation
    e = validation.etat()
    print(e.bulletin())
    print()
    print(e.rendu())
    return 0


DESCRIPTION = (
    "Radar commercial logistique — détecte des opportunités de chiffre "
    "d'affaires provenant de DIFFÉRENTES FAMILLES DE SOURCES PRÉVUES PAR "
    "L'ARCHITECTURE, les qualifie économiquement, distingue les faits des "
    "signaux et des hypothèses, puis indique comment les attaquer, les "
    "développer, les surveiller ou les convertir. "
    "« Familles prévues » n'est pas « familles validées » : voir `radar validation`.")


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description=DESCRIPTION)
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

    rc = s.add_parser("recoupement", help="apport propre de chaque moteur")
    rc.add_argument("--groupes", action="store_true",
                    help="l'historique des pages vues par plusieurs moteurs")
    rc.set_defaults(fn=cmd_recoupement)

    tr = s.add_parser("trouvailles", help="ce qu'un moteur a montré, jamais lu")
    tr.add_argument("--detail", action="store_true")
    tr.add_argument("--limite", type=int, default=40)
    tr.set_defaults(fn=cmd_trouvailles)

    ir = s.add_parser("import-recherche",
                      help="importer un export de moteur produit HORS RADAR, "
                           "puis le faire passer par toute la chaîne")
    ir.add_argument("fichier", help="le fichier JSON ou CSV remis au radar")
    ir.add_argument("--sans-analyse", action="store_true",
                    help="s'arrêter aux trouvailles, sans analyse commerciale")
    ir.add_argument("--top", type=int, default=20,
                    help="combien d'opportunités détailler (défaut : 20)")
    ir.set_defaults(fn=cmd_import_recherche)

    co = s.add_parser("collecter",
                      help="lister les pages à lire, ou importer une collecte "
                           "faite HORS RADAR")
    co.add_argument("fichier", nargs="?",
                    help="le fichier JSON de collecte ; absent, on liste")
    co.add_argument("--limite", type=int, help="combien de pages lister")
    co.set_defaults(fn=cmd_collecter)

    rp = s.add_parser("requetes-prioritaires",
                      help="les requêtes à exécuter DEHORS — le radar n'en lance aucune")
    rp.add_argument("--famille", help="n'afficher qu'une famille (A, B, C…)")
    rp.add_argument("--brut", action="store_true",
                    help="une requête par ligne, sans mise en forme")
    rp.set_defaults(fn=cmd_requetes_prioritaires)

    idf = s.add_parser("identifier", help="l'identité d'une entreprise — jamais devinée")
    idf.add_argument("entreprise", nargs="?", help="nom ou clé au registre")
    idf.add_argument("--domaine", help="le site RÉELLEMENT connu, jamais déduit")
    idf.add_argument("--bce", help="numéro d'entreprise BCE/KBO réellement connu")
    idf.add_argument("--preuve", help="d'où vient cette information — obligatoire")
    idf.add_argument("--candidat", action="append",
                     help="une entité possible ; en répéter deux donne AMBIGUË")
    idf.add_argument("--trancher", help="retenir CE candidat, avec --preuve")
    idf.add_argument("--sans-site", action="store_true", dest="sans_site",
                     help="identifiée, et sans site connu — c'est une mesure")
    idf.set_defaults(fn=cmd_identifier)

    ci = s.add_parser("circuits", help="métriques DÉCOUVERTE et SURVEILLANCE, séparées")
    ci.set_defaults(fn=cmd_circuits)

    pg = s.add_parser("page", help="déclarer/lister les pages surveillées")
    pg.add_argument("--url", help="l'URL exacte, jamais devinée")
    pg.add_argument("--entreprise", help="clé de l'entreprise au registre")
    pg.add_argument("--provenance", default="DÉCOUVERTE",
                    help="DÉCOUVERTE | CONFIGURÉE | OBSERVÉE DANS UNE SOURCE | "
                         "IDENTIFIÉE PAR RÈGLE")
    pg.add_argument("--libelle")
    pg.add_argument("--raison", help="pourquoi cette page est retenue")
    pg.add_argument("--candidate", action="store_true",
                    help="l'inscrire sans la retenir pour la surveillance")
    pg.add_argument("--ecarter", metavar="MOTIF",
                    help="ne plus la surveiller, avec son motif")
    pg.set_defaults(fn=cmd_page)

    ve = s.add_parser("veille", help="revisiter les pages connues (sans moteur)")
    ve.add_argument("--entreprise")
    ve.add_argument("--limite", type=int, default=None)
    ve.add_argument("--pour-de-vrai", action="store_true",
                    dest="pour_de_vrai", help="consulter réellement les pages")
    ve.add_argument("--sans-liens", action="store_true", dest="sans_liens",
                    help="ne pas récolter les liens des pages lues")
    ve.set_defaults(fn=cmd_veille)

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

    sv = s.add_parser("suivre", help="statut commercial d'une opportunité")
    sv.add_argument("reference", help="référence de source, ou un fragment")
    sv.add_argument("--statut", help="NOUVELLE · CONTACT À FAIRE · CONTACTÉE · "
                                     "EN ATTENTE · RELANCE · GAGNÉE · PERDUE · ABANDONNÉE")
    sv.add_argument("--motif", help="pourquoi — surtout pour PERDUE")
    sv.add_argument("--prochaine", help="prochaine action, AAAA-MM-JJ")
    sv.add_argument("--contact", help="dernier contact, AAAA-MM-JJ")
    sv.add_argument("--par", default="exploitant")
    sv.set_defaults(fn=cmd_suivre)

    v = s.add_parser("validation",
                     help="état de validation : architecture, fixtures, réel")
    v.set_defaults(fn=cmd_validation)

    n = s.add_parser("notifier", help="vider la file d'envoi")
    n.add_argument("--pour-de-vrai", action="store_true",
                   help="écrire réellement les alertes (sinon : essai à blanc)")
    n.add_argument("--dossier", default="alertes",
                   help="où déposer les fiches (défaut : ./alertes)")
    n.set_defaults(fn=cmd_notifier)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(principal())
