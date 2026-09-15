"""LA COUCHE DE SERVICE — le moteur, appelable proprement.

    INTERFACE WEB  →  CE MODULE  →  MOTEUR RADAR  →  BASE  →  SOURCES

CE MODULE NE DÉCIDE RIEN
========================

Il ne calcule aucun score, ne classe aucune opportunité, ne qualifie aucune
page, n'invente aucun libellé. Il APPELLE les modules qui en ont la charge et
rend leur réponse sous une forme sérialisable. Toute règle métier écrite ici
serait une deuxième implémentation, et c'est exactement ce que l'architecture
existe pour empêcher :

    le moteur reste la source de vérité ; le frontend n'en devient jamais une.

Un écran qui recalculerait une couleur, un seuil ou une action à partir des
champs rendus ici referait le radar une seconde fois, en moins testé. Les
champs sont donc rendus DÉJÀ DÉCIDÉS — `type`, `emoji`, `action`, `score`,
`fiabilite` — et il n'y a rien à en déduire.

CE QU'ON IGNORE S'ÉCRIT
=======================

Aucun champ n'est complété, deviné ni arrondi. Une donnée absente sort
`À CONFIRMER`, une mesure qui n'a pas eu lieu sort `NON MESURÉ`, une source
jamais interrogée sort `JAMAIS CONSULTÉE`. Un `null` silencieux laisserait
croire que l'information a été cherchée et qu'elle vaut zéro.

LES RESPONSABILITÉS, ET LEUR ÉQUIVALENT HTTP
============================================

Les noms restent ceux du projet ; la correspondance est écrite pour qu'un
serveur puisse être posé dessus sans y remettre de logique.

    POST /analyse              analyser()
    GET  /analyses             analyses()
    GET  /opportunites         opportunites()
    GET  /opportunites/{id}    opportunite()
    GET  /entreprises          entreprises()
    GET  /entreprises/{id}     entreprise()
    GET  /signaux              signaux()
    GET  /sources              sources()
    GET  /notifications        notifications()
    GET  /suivi                suivi()
    POST /verdict              poser_verdict()
    POST /action               poser_action()
    POST /surveillance         poser_surveillance()

Chaque fonction reçoit une connexion ouverte et rend des structures Python
sérialisables en JSON. Aucune n'ouvre ni ne ferme la base : la transaction
appartient à l'appelant, qui seul sait ce qui forme une unité de travail.
"""

from __future__ import annotations

import json

A_CONFIRMER = "À CONFIRMER"
NON_MESURE = "NON MESURÉ"
JAMAIS_CONSULTEE = "JAMAIS CONSULTÉE"


# ═══════════════════════════════════════════════════════ petits outils
def _liste(valeur) -> list:
    """Une colonne JSON rendue comme liste. Jamais une chaîne à découper."""
    if not valeur:
        return []
    if isinstance(valeur, (list, tuple)):
        return list(valeur)
    try:
        charge = json.loads(valeur)
    except (TypeError, ValueError):
        return [str(valeur)]
    return list(charge) if isinstance(charge, list) else [str(charge)]


def _ou(valeur, defaut=A_CONFIRMER):
    """La valeur, ou ce qu'on écrit quand on ne l'a pas."""
    if valeur is None or valeur == "":
        return defaut
    return valeur


def _colonnes(ligne) -> dict:
    try:
        return {c: ligne[c] for c in ligne.keys()}
    except AttributeError:
        return dict(ligne)


# ═══════════════════════════════════════════════════ POST /analyse
def analyser(cx, moteur, adaptateur, *, imports=None, collectes=None,
             moteurs_declares=None, profil=None, notifier: bool = True) -> dict:
    """UN CYCLE COMPLET — ce que déclenche « ANALYSE DU JOUR ».

    Délègue entièrement à `orchestrateur.executer`, qui enchaîne découverte,
    déduplication, qualification, identification, classification, score,
    surveillance et notifications. Rien n'est réordonné ici.

    Ce que cette fonction garantit en propre : une source qui n'a pas pu être
    interrogée ressort avec son état réel, et JAMAIS avec un résultat
    fabriqué. Un cycle sans aucune source disponible est un cycle honnête à
    zéro résultat, pas un cycle raté.
    """
    from . import orchestrateur as orch
    cycle = orch.executer(cx, moteur, adaptateur, imports=imports,
                          collectes=collectes,
                          moteurs_declares=moteurs_declares, profil=profil,
                          notifier=notifier)
    return _cycle_en_dict(cycle)


def _cycle_en_dict(cycle) -> dict:
    from . import orchestrateur as orch
    return {
        "id": cycle.cycle_id,
        "debut": cycle.debut,
        "fin": cycle.fin,
        "statut": cycle.statut,
        "entonnoir": {
            "resultats_bruts": cycle.resultats_bruts,
            "urls_uniques": cycle.urls_uniques,
            "doublons": cycle.doublons,
            "pages_analysees": cycle.pages_analysees,
            "candidats": cycle.candidats,
            "entreprises": cycle.entreprises,
            "opportunites": cycle.opportunites,
            "signaux": cycle.signaux,
            "postulables": cycle.postulables,
            "attribues": cycle.attribues,
            "rejetes": cycle.rejetes,
            "notifications": cycle.notifications,
        },
        # LES CINQ ÉTATS DE SOURCE, JAMAIS ADDITIONNÉS. Les fondre en un
        # « 3 sources OK » ferait disparaître la différence entre « a rendu
        # zéro » et « n'a pas été interrogée ».
        "sources": {
            "demandees": cycle.demandees,
            "executees": cycle.executees,
            "en_erreur": cycle.en_erreur,
            "non_disponibles": cycle.non_disponibles,
            "non_mesurees": cycle.non_mesurees,
        },
        "detail_sources": [_source_en_dict(s) for s in cycle.sources.values()],
        "erreurs": list(cycle.erreurs),
        "avertissement": (
            "NON MESURÉE n'est pas zéro : la source n'a pas été interrogée."
            if cycle.non_mesurees or cycle.non_disponibles else None),
    }


def _source_en_dict(s) -> dict:
    from . import orchestrateur as orch
    return {
        "nom": s.nom,
        "etat": s.etat,
        "resultats": s.resultats,
        "opportunites": s.opportunites,
        "motif": s.motif,
        "derniere_consultation": _ou(s.derniere_consultation, JAMAIS_CONSULTEE),
    }


# ═══════════════════════════════════════════════════ GET /analyses
def analyses(cx, *, limite: int = 20) -> list[dict]:
    """Le journal des cycles. Chaque nombre est un compte d'observations."""
    lignes = cx.execute(
        "SELECT * FROM journal_cycles ORDER BY id DESC LIMIT ?",
        (int(limite),)).fetchall()
    return [{
        "id": l["cycle_id"],
        "debut": l["debut"],
        "fin": l["fin"],
        "statut": l["statut"],
        "entonnoir": {
            "resultats_bruts": l["resultats_bruts"],
            "urls_uniques": l["urls_uniques"],
            "doublons": l["doublons"],
            "pages_analysees": l["pages_analysees"],
            "candidats": l["candidats"],
            "entreprises": l["entreprises"],
            "opportunites": l["opportunites"],
            "notifications": l["notifications"],
        },
        "sources": {
            "demandees": _liste(l["sources_demandees"]),
            "executees": _liste(l["sources_executees"]),
            "en_erreur": _liste(l["sources_erreur"]),
            "non_disponibles": _liste(l["sources_non_disponibles"]),
            "non_mesurees": _liste(l["sources_non_mesurees"]),
        },
    } for l in lignes]


# ═══════════════════════════════════ GET /opportunites
def _carte(cx, ligne) -> dict:
    """LA CARTE d'un écran — tous les champs DÉJÀ DÉCIDÉS par le moteur.

    Rien n'est à recalculer côté interface : la couleur, l'action et le score
    sortent d'ici tels que le moteur les a posés.
    """
    from . import classification
    from .classification import Type
    from .entreprises import domaine_de
    l = _colonnes(ligne)
    url = l.get("ref_source") or ""
    domaine = domaine_de(url)

    emoji = "·"
    for t in Type:
        if t.value == l.get("type"):
            emoji = t.emoji
            break

    # L'ENTREPRISE N'EST JAMAIS DEVINÉE. Un domaine n'est pas une raison
    # sociale, et l'écrire comme si c'en était une polluerait le registre.
    identite = _identite_de(cx, domaine)

    return {
        "avis_id": l.get("avis_id"),
        "entreprise": {
            "nom": _ou(l.get("acheteur"), None),
            "domaine": domaine,
            "identite": identite,
            "libelle": (l.get("acheteur") or
                        (f"domaine {domaine}" if domaine else A_CONFIRMER)),
        },
        "opportunite": _ou(l.get("intitule")),
        "categorie": {"code": l.get("type"), "emoji": emoji},
        "nature": _ou(l.get("nature")),
        "etat_procedure": {
            "etat": _ou(l.get("etat_procedure"), "INCONNU"),
            "confiance": _ou(l.get("confiance_etat")),
        },
        "type_information": _ou(l.get("type_information"),
                                "NON DÉCLARÉ PAR LA SOURCE"),
        "sources": [{"source": l.get("source_avis") or l.get("source"),
                     "reference": url,
                     "vue_le": _ou(l.get("derniere_vue"), NON_MESURE)}],
        "zone": _ou(l.get("zone")),
        "distance_km": l.get("distance_km"),
        "montant": l.get("montant"),
        "ca_annuel": l.get("ca_annuel"),
        "ca_etat": _ou(l.get("ca_etat"), NON_MESURE),
        "duree_mois": l.get("duree_mois"),
        "effort": {
            "distance": (f"{l['distance_km']:.0f} km"
                         if l.get("distance_km") is not None
                         else f"distance {A_CONFIRMER}"),
            "capacite": _ou(l.get("capacite")),
        },
        # LE SCORE EST RENDU TEL QUEL, et son caractère mesurable avec lui :
        # un score affiché sans dire qu'il ne repose sur aucun fait
        # économique se lit comme une évaluation.
        "score": l.get("score"),
        "score_mesurable": bool(l.get("score_mesurable")),
        "niveau_de_preuve": _ou(l.get("fiabilite"), NON_MESURE),
        "action_recommandee": _ou(l.get("action")),
        "raison_principale": _ou(l.get("motif")),
        # Les exigences telles que la source les a publiées. Vide ≠ « aucune
        # exigence » : la vue écrit NON PUBLIÉ, pas zéro.
        "exigences": l.get("exigences"),
        "manques": _liste(l.get("manques")),
        "risques": _liste(l.get("risques")),
        "leviers": _liste(l.get("leviers")),
        "decouverte_le": _ou(l.get("premiere_vue"), NON_MESURE),
        "echeance": _ou(l.get("echeance"), "NON PUBLIÉE"),
        "surveillance": _surveillance_de(cx, url),
        "suivi": _suivi_de(cx, l.get("avis_id")),
    }


def _identite_de(cx, domaine) -> dict:
    if not domaine:
        return {"etat": "INCONNUE", "raison_sociale": None}
    try:
        from . import identite as mod
        i = mod.lire(cx, domaine)
        return {"etat": i.etat.value,
                "raison_sociale": getattr(i, "raison_sociale", None)}
    except Exception:                                            # noqa: BLE001
        return {"etat": "INCONNUE", "raison_sociale": None}


def _surveillance_de(cx, url) -> dict:
    try:
        from . import pages
        p = pages.lire(cx, url)
    except Exception:                                            # noqa: BLE001
        p = None
    if p is None:
        return {"statut": "NON SURVEILLÉE", "acces": JAMAIS_CONSULTEE,
                "qualification": NON_MESURE}
    return {
        "statut": p.statut.value,
        "acces": p.acces.value if p.acces else JAMAIS_CONSULTEE,
        "qualification": (p.qualification.value if p.qualification
                          else NON_MESURE),
        "derniere_visite": _ou(p.derniere_visite, JAMAIS_CONSULTEE),
    }


def _suivi_de(cx, avis_id) -> dict:
    """La clé du contrat s'appelle « depuis » ; la colonne en base s'appelle
    « etat_maj » et `Suivi` l'expose sous le nom `statut_maj`.

    Ces deux noms ont divergé et personne ne l'a vu : `getattr(s, "depuis")`
    ne levait rien, il rendait None. La fiche affichait donc « aucun
    changement enregistré » juste après que `radar suivre` ait écrit le
    changement — le radar se contredisait lui-même. On lit l'attribut par
    son vrai nom, pour qu'une faute de nom redevienne une erreur bruyante.

    Le filet était `except Exception`, et c'est LUI qui a rendu le défaut
    invisible : une faute d'attribut y serait morte aussi silencieusement.
    On ne rattrape donc plus que ce qui est légitimement attendu — pas
    d'opportunité pour cet avis, valeur illisible, base d'une version
    antérieure. Un AttributeError remonte désormais jusqu'à la surface.
    """
    import sqlite3
    if avis_id is None:
        return {"statut": "NOUVELLE", "depuis": None, "motif": None}
    try:
        from . import suivi as mod
        s = mod.lire(cx, int(avis_id))
    except (ValueError, TypeError, sqlite3.OperationalError):
        return {"statut": "NOUVELLE", "depuis": None, "motif": None}
    # Une affaire jamais regardée a `statut = None` en base — c'est le défaut
    # `non_vu` du schéma. Le resserrement du filet ci-dessus a montré que
    # « NOUVELLE » ne sortait PAS d'ici mais d'un AttributeError attrapé au
    # vol : `s.statut.value` sur None. La bonne réponse était la bonne pour
    # une mauvaise raison. On la dit maintenant explicitement.
    if s.jamais_regardee:
        return {"statut": "NOUVELLE", "depuis": None, "motif": s.motif}
    return {"statut": s.statut.value, "depuis": s.statut_maj, "motif": s.motif}


def _lignes_opportunites(cx, *, limite, categorie=None, avis_id=None,
                         exclure=None):
    sql = ("SELECT o.*, a.ref_source, a.source AS source_avis,"
           " a.derniere_vue, a.premiere_vue"
           " FROM opportunites o JOIN avis a ON a.id = o.avis_id")
    ou, args = [], []
    if avis_id is not None:
        ou.append("o.avis_id = ?")
        args.append(int(avis_id))
    if categorie:
        ou.append("o.type = ?")
        args.append(str(categorie))
    # EXCLURE N'EST PAS SUPPRIMER : la ligne reste en base, elle n'est
    # simplement pas affichée par cette vue-là. Le filtre est posé en SQL
    # pour que `--limite 10` rende bien dix lignes affichables, et non dix
    # lignes lues dont neuf disparaissent ensuite.
    if exclure:
        ou.append("o.type <> ?")
        args.append(str(exclure))
    if ou:
        sql += " WHERE " + " AND ".join(ou)
    sql += " ORDER BY o.score DESC, o.echeance IS NULL, o.echeance"
    if limite:
        sql += f" LIMIT {int(limite)}"
    return cx.execute(sql, args).fetchall()


def opportunites(cx, *, limite: int = 50, categorie=None, exclure=None,
                 consolider: bool = True) -> list[dict]:
    """Les opportunités, UNE FICHE PAR ADRESSE.

    Le regroupement est celui de `radar/consolidation.py` — le même que le
    rapport texte, pour que l'écran et le terminal ne racontent jamais deux
    histoires différentes. Les lectures écartées de la carte principale ne
    sont pas perdues : elles sortent dans `autres_lectures`, avec leur
    provenance et leur niveau de preuve.
    """
    from . import consolidation
    lignes = _lignes_opportunites(cx, limite=limite, categorie=categorie,
                                  exclure=exclure)
    if not consolider:
        return [_carte(cx, l) for l in lignes]

    sortie = []
    for adresse in consolidation.grouper(lignes):
        carte = _carte(cx, adresse.principale)
        autres = [_carte(cx, l) for l in adresse.autres]
        carte["autres_lectures"] = autres
        # TOUTES les provenances de l'adresse, principale comprise : c'est ce
        # qui permet à l'écran de montrer « vue par deux sources » sans avoir
        # à recomposer la liste lui-même.
        carte["sources"] = [s for c in [carte] + autres for s in c["sources"]]
        carte["lectures_divergentes"] = adresse.divergentes
        if adresse.divergentes:
            carte["divergence"] = {
                "libelle": consolidation.DIVERGENCE,
                "principale": {
                    "categorie": carte["categorie"],
                    "nature": carte["nature"],
                    "action": carte["action_recommandee"],
                    "niveau_de_preuve": carte["niveau_de_preuve"]},
                "autres": [{
                    "categorie": a["categorie"], "nature": a["nature"],
                    "action": a["action_recommandee"],
                    "niveau_de_preuve": a["niveau_de_preuve"],
                    "sources": a["sources"]} for a in autres],
            }
        sortie.append(carte)
    return sortie


def opportunite(cx, avis_id) -> dict | None:
    """Une opportunité et toutes ses lectures. None si elle n'existe pas."""
    lignes = _lignes_opportunites(cx, limite=None, avis_id=avis_id)
    if not lignes:
        return None
    cartes = opportunites(cx, limite=None, consolider=False)
    for c in cartes:
        if c["avis_id"] == int(avis_id):
            return c
    return _carte(cx, lignes[0])


# ═══════════════════════════════════ GET /signaux
def signaux(cx, *, limite: int = 50) -> list[dict]:
    """Ce qui se passe chez quelqu'un — SANS que personne ait rien demandé.

    Un signal n'est pas une opportunité confirmée, et l'écran ne doit pas
    pouvoir les confondre : la nature est rendue, et l'avertissement avec.
    """
    lignes = cx.execute(
        "SELECT o.*, a.ref_source, a.source AS source_avis, a.derniere_vue,"
        " a.premiere_vue FROM opportunites o JOIN avis a ON a.id = o.avis_id"
        " WHERE o.type <> 'REJET' AND o.nature IN ('SIGNAL', 'HYPOTHÈSE')"
        " ORDER BY o.score DESC LIMIT ?", (int(limite),)).fetchall()
    sortie = []
    for l in lignes:
        c = _carte(cx, l)
        c["avertissement"] = ("AUCUN besoin n'a été exprimé ici. "
                              "Ce n'est pas une demande adressée à votre "
                              "entreprise.")
        sortie.append(c)
    return sortie


# ═══════════════════════════════════ GET /entreprises
def entreprises(cx, *, limite: int = 100) -> list[dict]:
    from . import entreprises as mod
    registre = mod.charger(cx)
    fiches = sorted(registre.entreprises.values(),
                    key=lambda e: (-e.besoins_detectes, e.cle))
    return [_entreprise_en_dict(cx, e) for e in fiches[:limite]]


def _entreprise_en_dict(cx, e) -> dict:
    return {
        "cle": e.cle,
        "domaine": e.domaine,
        # UN DOMAINE N'EST PAS UNE RAISON SOCIALE. `identite` dit ce qu'on
        # sait vraiment de qui se cache derrière, et l'état INCONNUE est une
        # réponse — pas un champ vide.
        "identite": _identite_de(cx, e.domaine),
        "nom": _ou(e.nom),
        "etat": e.etat.value,
        "motifs": list(e.motifs),
        "origine": _ou(e.origine, NON_MESURE),
        "decouverte_le": _ou(e.decouverte_le, NON_MESURE),
        "derniere_visite": _ou(e.derniere_visite, JAMAIS_CONSULTEE),
        "besoins_detectes": e.besoins_detectes,
        "marches_gagnes": e.marches_gagnes,
        "bce": _ou(e.bce, A_CONFIRMER),
        "surveillee": e.etat.value == "SURVEILLEE",
    }


def entreprise(cx, domaine) -> dict | None:
    from . import entreprises as mod, pages
    registre = mod.charger(cx)
    trouvee = registre.entreprises.get(domaine)
    if trouvee is None:
        for e in registre.entreprises.values():
            if e.domaine == domaine or e.cle == domaine:
                trouvee = e
                break
    if trouvee is None:
        return None
    domaine = trouvee.domaine or trouvee.cle
    fiche = _entreprise_en_dict(cx, trouvee)
    fiche["pages"] = [{
        "url": p.url,
        "statut": p.statut.value,
        "acces": p.acces.value if p.acces else JAMAIS_CONSULTEE,
        "qualification": (p.qualification.value if p.qualification
                          else NON_MESURE),
        "raison": p.raison,
    } for p in pages.a_surveiller(cx, entreprise=domaine, toutes=True)]
    fiche["opportunites"] = [
        c for c in opportunites(cx, limite=None, consolider=False)
        if c["entreprise"]["domaine"] == domaine]
    return fiche


# ═══════════════════════════════════ GET /sources
def sources(cx, *, declarees=()) -> list[dict]:
    """L'état RÉEL de chaque source — et jamais un résultat fabriqué.

    Une source qu'on n'a pas pu interroger ne rend pas zéro : elle rend
    JAMAIS CONSULTÉE ou NON DISPONIBLE, avec son motif quand il est connu.
    Les deux ne se confondent pas, et l'écran ne doit pas pouvoir les
    afficher pareil.

    `declarees` : les moteurs que l'installation connaît, disponibles ou
    non. Ils sont passés par l'appelant — ce module ne connaît aucun moteur
    et ne doit pas en apprendre. Sans eux, un moteur jamais interrogé serait
    simplement ABSENT de la liste, ce qui se lirait comme « il n'existe
    pas » au lieu de « il n'a pas pu servir ».
    """
    from . import execution as ex
    sortie = {}
    for ligne in cx.execute(
            "SELECT source, moteur_declare, execution_par, requete, resultats,"
            " refuses, date_execution, importe_le FROM executions_recherche"
            " ORDER BY id DESC").fetchall():
        nom = ligne["source"]
        e = sortie.setdefault(nom, {
            "nom": nom,
            "moteur_declare": ligne["moteur_declare"],
            # QUI a exécuté la recherche — le radar, ou quelqu'un d'autre.
            # Confondre les deux ferait passer un import pour une consultation.
            "execution": ligne["execution_par"],
            "etat": "CONSULTÉE",
            # La date DÉCLARÉE par la source. « INCONNUE » quand elle ne l'a
            # pas dite : on ne date pas une recherche qu'on n'a pas datée.
            "derniere_consultation": _ou(ligne["date_execution"],
                                         ex.DATE_INCONNUE),
            "recue_le": ligne["importe_le"],
            "resultats": 0,
            "refuses": 0,
            "opportunites": NON_MESURE,
            "motif": None,
        })
        e["resultats"] += int(ligne["resultats"] or 0)
        e["refuses"] += int(ligne["refuses"] or 0)
        if (ligne["importe_le"] or "") > (e["recue_le"] or ""):
            e["recue_le"] = ligne["importe_le"]
            e["derniere_consultation"] = _ou(ligne["date_execution"],
                                             ex.DATE_INCONNUE)

    for nom, e in sortie.items():
        e["opportunites"] = cx.execute(
            "SELECT count(*) c FROM opportunites o JOIN avis a"
            " ON a.id = o.avis_id WHERE a.source = ?", (nom,)).fetchone()["c"]

    # LES MOTEURS DE L'INSTALLATION, exécutés ou non. Un moteur sans clé
    # doit se voir : c'est la première chose qu'on cherche quand le radar
    # ne rend rien.
    for m in declarees or ():
        nom = getattr(m, "nom", str(m))
        if nom in sortie:
            continue
        dispo = bool(getattr(m, "disponible", False))
        sortie[nom] = {
            "nom": nom, "moteur_declare": nom,
            "execution": NON_MESURE,
            "etat": "DISPONIBLE — NON INTERROGÉ" if dispo else "NON DISPONIBLE",
            "derniere_consultation": JAMAIS_CONSULTEE, "recue_le": None,
            "resultats": NON_MESURE, "refuses": NON_MESURE,
            "opportunites": NON_MESURE,
            "motif": (None if dispo
                      else getattr(m, "motif_indisponibilite", None)),
        }

    # Les sources DÉCLARÉES mais jamais exécutées : elles doivent apparaître,
    # précisément pour qu'on voie qu'elles n'ont rien rendu parce qu'on ne
    # leur a rien demandé.
    for ligne in cx.execute("SELECT DISTINCT source FROM avis").fetchall():
        sortie.setdefault(ligne["source"], {
            "nom": ligne["source"], "moteur_declare": None,
            "execution": NON_MESURE, "etat": JAMAIS_CONSULTEE,
            "derniere_consultation": JAMAIS_CONSULTEE, "recue_le": None,
            "resultats": NON_MESURE, "refuses": NON_MESURE,
            "opportunites": cx.execute(
                "SELECT count(*) c FROM opportunites o JOIN avis a"
                " ON a.id = o.avis_id WHERE a.source = ?",
                (ligne["source"],)).fetchone()["c"],
            "motif": "aucune exécution journalisée pour cette source",
        })
    return sorted(sortie.values(), key=lambda e: e["nom"])


# ═══════════════════════════════════ GET /notifications
def notifications(cx, *, cycle_id=None, limite: int = 20) -> list[dict]:
    """Ce qui mérite un regard humain. Le bot n'a contacté personne."""
    from . import notification as mod
    return [{
        "avis_id": n.avis_id,
        "motif": n.motif,
        "corps": n.corps,
        "sceau": n.sceau,
        "cycle_id": n.cycle_id,
        "creee_le": n.creee_le,
        "envoyee": False,
        "avertissement": ("Le bot n'a contacté personne et n'a rien envoyé. "
                          "Il prépare ; la décision et l'action restent "
                          "humaines."),
    } for n in mod.toutes(cx, cycle_id=cycle_id, limite=limite)]


# ═══════════════════════════════════ GET /suivi
def suivi(cx, *, limite: int = 100) -> list[dict]:
    """L'état commercial de chaque affaire — posé par un humain, jamais déduit."""
    from .suivi import Statut
    lignes = cx.execute(
        "SELECT o.avis_id, o.intitule, o.type, o.score, o.action,"
        " a.ref_source, a.source AS source_avis"
        " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
        " WHERE o.type <> 'REJET' ORDER BY o.score DESC LIMIT ?",
        (int(limite),)).fetchall()
    sortie = []
    for l in lignes:
        s = _suivi_de(cx, l["avis_id"])
        sortie.append({
            "avis_id": l["avis_id"],
            "opportunite": _ou(l["intitule"]),
            "categorie": l["type"],
            "score": l["score"],
            "action_recommandee": _ou(l["action"]),
            "reference": l["ref_source"],
            "source": l["source_avis"],
            "statut": s["statut"],
            "depuis": s.get("depuis"),
        })
    return sortie


def statuts_possibles() -> list[str]:
    """Les colonnes du tableau commercial. Le frontend n'en invente aucune."""
    from .suivi import Statut
    return [s.value for s in Statut]


def categories_possibles() -> list[dict]:
    """Les six catégories, avec leur emoji. Jamais recalculées côté écran."""
    from .classification import Type
    return [{"code": t.value, "emoji": t.emoji, "notifiable": t.notifiable}
            for t in Type]


# ═══════════════════════════════════ POST /verdict
def poser_verdict(cx, url, verdict, *, motif=None, entreprise=None,
                  source=None, juge_par="exploitant") -> dict:
    """Un humain juge un résultat : VP · FP · FN · ?

    Le radar ne se juge jamais lui-même : `juge_par` ne peut pas valoir
    « radar ». La règle vit dans `radar/verdicts.py` et n'est pas recopiée
    ici — l'exception remonte telle quelle à l'appelant.
    """
    from . import verdicts as mod
    j = mod.inscrire(cx, url, verdict, motif=motif, entreprise=entreprise,
                     source=source, juge_par=juge_par)
    return {"url": j.url, "verdict": j.verdict.value, "emoji": j.verdict.emoji,
            "motif": j.motif, "juge_par": j.juge_par, "juge_le": j.juge_le}


def qualite(cx) -> dict:
    """Les comptes de verdicts, et les taux SEULEMENT s'ils veulent dire
    quelque chose. En dessous du seuil, `ÉCHANTILLON INSUFFISANT` — pas un
    pourcentage qui se lirait comme un pourcentage calculé sur mille."""
    from . import verdicts as mod
    return mod.metriques(cx)


# ═══════════════════════════════════ POST /action
def poser_action(cx, avis_id, statut, *, motif=None,
                 prochaine_action_le=None, dernier_contact_le=None,
                 par: str = "exploitant") -> dict:
    """L'état commercial d'une affaire, posé par un humain.

    Le vocabulaire est celui de `radar/suivi.py` : un statut hors liste est
    refusé, jamais deviné.
    """
    from . import suivi as mod
    s = mod.marquer(cx, int(avis_id), statut, motif=motif,
                    prochaine_action_le=prochaine_action_le,
                    dernier_contact_le=dernier_contact_le, par=par)
    return {"avis_id": int(avis_id), "statut": s.statut.value,
            "motif": s.motif,
            "depuis": s.statut_maj,
            "prochaine_action_le": s.prochaine_action_le,
            "dernier_contact_le": s.dernier_contact_le}


def actions_possibles(cx, avis_id) -> list[str]:
    """Ce qu'un humain a le droit de poser. La liste ne dépend pas de l'écran."""
    return statuts_possibles()


# ═══════════════════════════════════ POST /surveillance
def poser_surveillance(cx, url, *, entreprise=None, raison=None,
                       surveiller: bool = True) -> dict:
    """Mettre une page sous surveillance, ou l'en retirer.

    Une page ÉCARTÉE à la main n'est jamais re-promue automatiquement : la
    règle est dans `radar/pages.py`, et c'est elle qui décide.
    """
    from . import pages
    if surveiller:
        motif = raison or "surveillance demandée par l'exploitant"
        pages.declarer(cx, url, entreprise=entreprise, raison=motif)
        p = pages.promouvoir(cx, url, motif)
    else:
        p = pages.ecarter(cx, url, raison or "écartée par l'exploitant")
    return {
        "url": p.url,
        "statut": p.statut.value,
        "raison": p.raison,
        "acces": p.acces.value if p.acces else JAMAIS_CONSULTEE,
        "qualification": (p.qualification.value if p.qualification
                          else NON_MESURE),
    }


def a_collecter(cx, *, limite: int = 50) -> list[dict]:
    """Les pages à lire — le radar ne peut pas toujours les lire lui-même.

    Rendu explicitement plutôt que déduit côté écran : l'ordre et la raison
    viennent du moteur.
    """
    from . import pages
    return [{
        "url": p.url,
        "entreprise": p.entreprise,
        "libelle": _ou(p.libelle, None),
        "raison": p.raison,
        "acces": p.acces.value if p.acces else JAMAIS_CONSULTEE,
        "derniere_visite": _ou(p.derniere_visite, JAMAIS_CONSULTEE),
    } for p in pages.a_surveiller(cx, limite=limite)]


# ═══════════════════════════════════ DIAGNOSTIC — « est-ce que ça marche ? »
def diagnostic(cx, *, configurations=None, declarees=()) -> dict:
    """L'état RÉEL du système, tel qu'il est au moment où on demande.

    Aucun composant n'est déclaré OK par principe : chacun est éprouvé, et
    ce qui échoue dit pourquoi. Un diagnostic qui afficherait « OK » partout
    sans rien avoir essayé serait pire qu'inutile — il rassurerait à tort.

    `configurations` : un appelable qui charge les fichiers de configuration
    du moteur. La CLI le fournit ; ce module ne connaît aucun chemin.
    """
    composants, details = [], []

    # ── le moteur : ses configurations se chargent-elles ? ──
    if configurations is None:
        composants.append(("Moteur", NON_MESURE + " — non éprouvé ici"))
    else:
        try:
            configurations()
            composants.append(("Moteur", "OK"))
        except Exception as e:                                   # noqa: BLE001
            composants.append(("Moteur", "ERREUR"))
            details.append(f"configuration illisible : {e}")

    # ── la base : lisible, et que contient-elle ? ──
    try:
        n_opp = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        n_avis = cx.execute("SELECT count(*) c FROM avis").fetchone()["c"]
        composants.append(("Base", f"OK — {n_avis} avis · {n_opp} opportunités"))
    except Exception as e:                                       # noqa: BLE001
        composants.append(("Base", "ERREUR"))
        details.append(f"base illisible : {e}")
        n_opp = n_avis = 0

    # ── les sources : combien ont réellement rendu quelque chose ? ──
    # Les moteurs DÉCLARÉS comptent, même sans clé : un diagnostic qui
    # dirait « Sources OK — 1/1 » en taisant les deux moteurs injoignables
    # rassurerait exactement là où il ne faut pas.
    liste = sources(cx, declarees=declarees)
    consultees = [s for s in liste if s["etat"] == "CONSULTÉE"]
    if not liste:
        composants.append(("Sources", JAMAIS_CONSULTEE + " — aucune déclarée"))
    elif len(consultees) == len(liste):
        composants.append(("Sources", f"OK — {len(consultees)}/{len(liste)}"))
    else:
        composants.append(("Sources", f"PARTIEL — {len(consultees)}/{len(liste)}"))
    for s in liste:
        if s["etat"] != "CONSULTÉE":
            details.append(f"source {s['nom']} : {s['etat']}"
                           + (f" — {s['motif']}" if s.get("motif") else ""))

    # ── l'import : le module refuse-t-il bien un fichier sans provenance ? ──
    try:
        from . import import_externe as imp
        composants.append(("Import", f"OK — exige « {imp.PROVENANCE} »"))
    except Exception as e:                                       # noqa: BLE001
        composants.append(("Import", "ERREUR"))
        details.append(f"import indisponible : {e}")

    # ── la collecte : des pages ont-elles été RÉELLEMENT lues ? ──
    try:
        from . import pages as mod_pages
        toutes = mod_pages.a_surveiller(cx, toutes=True)
        lues = [p for p in toutes
                if p.acces and p.acces.value not in (JAMAIS_CONSULTEE,)]
        if not toutes:
            composants.append(("Collecte", JAMAIS_CONSULTEE + " — aucune page"))
        elif not lues:
            composants.append(("Collecte", f"{JAMAIS_CONSULTEE} — "
                                           f"{len(toutes)} page(s) en attente"))
            details.append("aucune page n'a été lue : le radar ne peut pas "
                           "collecter lui-même dans cet environnement — "
                           "voir `radar collecter`")
        else:
            composants.append(("Collecte", f"OK — {len(lues)}/{len(toutes)} lue(s)"))
    except Exception as e:                                       # noqa: BLE001
        composants.append(("Collecte", "ERREUR"))
        details.append(f"registre de pages illisible : {e}")

    # ── notifications et surveillance ──
    try:
        n_notif = cx.execute("SELECT count(*) c FROM notifications").fetchone()["c"]
        composants.append(("Notifications", f"OK — {n_notif} préparée(s), "
                                            "0 envoyée(s)"))
    except Exception as e:                                       # noqa: BLE001
        composants.append(("Notifications", "ERREUR"))
        details.append(str(e))
    try:
        from . import pages as mod_pages
        surveillees = mod_pages.a_surveiller(cx)
        composants.append(("Surveillance", f"OK — {len(surveillees)} page(s)"))
    except Exception as e:                                       # noqa: BLE001
        composants.append(("Surveillance", "ERREUR"))
        details.append(str(e))

    suggestion = ("radar analyse-du-jour --import <fichier.tsv>"
                  if n_opp == 0 else "radar opportunites")
    return {"composants": composants, "details": details,
            "suggestion": suggestion,
            "opportunites": n_opp, "avis": n_avis}
