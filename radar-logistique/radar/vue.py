"""LA VUE HUMAINE — le moteur, lisible depuis une invite de commande.

    MOTEUR  →  radar/service.py  →  CE MODULE  →  l'écran

CE MODULE NE DÉCIDE RIEN, ET NE NOMME RIEN
==========================================

Il met en forme. Il ne classe pas, ne compte pas de seuil, n'invente aucun
libellé de catégorie et ne traduit aucun verdict. Les noms des catégories,
leurs emojis et leur ordre viennent de `service.categories_possibles()`, qui
les lit dans `classification.Type` — jamais d'une liste écrite ici.

C'est la contrainte principale : une CLI qui renommerait 🟢 DIRECT en
« POSTULABLE » créerait un second vocabulaire métier, qui divergerait du
premier au premier ajout. Et ce serait faux : une opportunité 🟢 peut très
bien avoir pour action « CONTACTER L'ENTREPRISE », pas « POSTULER ».

CE QU'ON IGNORE S'ÉCRIT
=======================

Aucune valeur n'est complétée ni arrondie. Les quatre formes d'absence ont
chacune un sens différent, et la vue les distingue :

    À CONFIRMER      la source n'a rien publié — ça peut exister
    NON PUBLIÉ       la source publie ce champ d'habitude, pas ici
    NON MESURÉ       la mesure n'a pas eu lieu — ce n'est pas zéro
    NON CALCULABLE   il manque une donnée d'entrée pour calculer
"""

from __future__ import annotations

import json

from . import service

LARGEUR = 70
TRAIT = "─" * LARGEUR
DOUBLE = "═" * LARGEUR

NON_PUBLIE = "NON PUBLIÉ PAR LA SOURCE"
NON_CALCULABLE = "NON CALCULABLE"


def _titre(texte: str) -> list[str]:
    return [DOUBLE, f" {texte}", DOUBLE, ""]


def _champ(nom: str, valeur, largeur: int = 18) -> str:
    return f"{nom:<{largeur}}: {valeur}"


def _texte(valeur, defaut=service.A_CONFIRMER) -> str:
    if valeur is None or valeur == "" or valeur == []:
        return defaut
    return str(valeur)


def _emoji_de(code: str) -> str:
    """L'emoji VIENT DU MOTEUR. Aucune table de correspondance ici."""
    for c in service.categories_possibles():
        if c["code"] == code:
            return c["emoji"]
    return "·"


# ═══════════════════════════════════════════════ ANALYSE DU JOUR
def analyse_du_jour(cycle: dict, *, mode: str, avant: dict | None = None,
                    cartes: list | None = None, date: str | None = None) -> str:
    """La synthèse d'un cycle — ce que `radar analyse-du-jour` affiche.

    `avant` : les comptes relevés AVANT le cycle, pour dire ce qui est neuf
    et ce qui était déjà connu. Sans lui, la ligne d'idempotence se tait
    plutôt que d'annoncer un chiffre qu'on n'a pas mesuré.
    """
    e = cycle["entonnoir"]
    L = _titre("RADAR COMMERCIAL — ANALYSE DU JOUR")

    L.append(_champ("Mode", mode))
    L.append(_champ("Date", _texte(date or cycle.get("debut"), "NON MESURÉE")))
    L.append(_champ("Cycle", cycle["id"]))
    L.append(_champ("Statut", cycle["statut"]))
    L.append("")
    # CES NOMBRES SONT L'ÉTAT DE LA BASE, pas ce que ce cycle a fait.
    # `orchestrateur._mesurer` le dit en toutes lettres : « lit l'état de la
    # base APRÈS coup ». Les étiqueter « lus par ce cycle » ferait croire
    # qu'un deuxième passage a relu 35 résultats alors qu'il n'en a relu
    # aucun de neuf. Ce qui est NEUF est plus bas, et mesuré avant/après.
    L.append("ÉTAT DE LA BASE APRÈS CE CYCLE")
    L.append(f"  {'Résultats en base':<32}{e['resultats_bruts']:>5}")
    L.append(f"  {'URLs uniques':<32}{e['urls_uniques']:>5}")
    L.append(f"  {'Doublons regroupés':<32}{e['doublons']:>5}")
    L.append(f"  {'Entreprises':<32}{e['entreprises']:>5}")
    L.append(f"  {'Opportunités':<32}{e['opportunites']:>5}")
    L.append("")

    L.append("OPPORTUNITÉS PAR CATÉGORIE")
    comptes = _compter(cartes or [], "categorie")
    for c in service.categories_possibles():
        L.append(f"  {c['emoji']} {c['code']:<28} {comptes.get(c['code'], 0):>5}")
    L.append("")

    L.append("ACTIONS RECOMMANDÉES")
    actions = _compter(cartes or [], "action")
    if actions:
        for nom, n in sorted(actions.items(), key=lambda x: (-x[1], x[0])):
            L.append(f"  {nom[:44]:<46} {n:>5}")
    else:
        L.append("  aucune — aucune opportunité écrite par ce cycle")
    L.append("")

    L.append("SOURCES")
    L += _bloc_sources(cycle["detail_sources"])
    L.append("")

    L.append(_champ("Notifications préparées", e["notifications"], 28))
    L.append(_champ("Pages réellement collectées", e["pages_analysees"], 28))
    if e["pages_analysees"] == 0:
        L.append("  AUCUNE PAGE N'A ÉTÉ LUE. Tout ce que ces pages contiennent")
        L.append("  et que l'extrait ne dit pas reste INCONNU.")
    L.append("")

    if avant is not None:
        L.append("CE QUI EST NEUF")
        for nom, cle in (("opportunités", "opportunites"),
                         ("entreprises", "entreprises")):
            avant_n = avant.get(cle, 0)
            neuf = max(0, avant.get(f"apres_{cle}", 0) - avant_n)
            L.append(f"  {('Nouvelles ' + nom):<32}{neuf:>5}")
            L.append(f"  {'Déjà connues avant ce cycle':<32}{avant_n:>5}")
        L.append(f"  {'Doublons évités':<32}{e['doublons']:>5}")
        L.append("")

    if cycle.get("erreurs"):
        L.append("ERREURS")
        for x in cycle["erreurs"]:
            L.append(f"  ❌ {x}")
        L.append("")

    if cycle.get("avertissement"):
        L.append(f"  ⚠️  {cycle['avertissement']}")
        L.append("")

    L.append("Analyse terminée.")
    L.append("")
    L.append("  Le radar n'a contacté personne et n'a rien envoyé.")
    L.append("  Voir ensuite :  radar opportunites   ·   radar sources")
    return "\n".join(L)


def _compter(cartes, quoi: str) -> dict:
    """Compter n'est pas décider : on lit ce que le moteur a déjà posé."""
    sortie: dict = {}
    for c in cartes:
        cle = (c["categorie"]["code"] if quoi == "categorie"
               else c["action_recommandee"])
        sortie[cle] = sortie.get(cle, 0) + 1
    return sortie


def _bloc_sources(detail: list) -> list[str]:
    L = []
    for s in sorted(detail, key=lambda x: x["nom"]):
        ligne = f"  {s['nom'][:22]:<24} {s['etat']:<16}"
        if s["motif"]:
            ligne += f" — {s['motif'][:38]}"
        L.append(ligne)
    if not L:
        L.append("  aucune source déclarée à ce cycle")
    return L


# ═══════════════════════════════════════════════ LISTE D'OPPORTUNITÉS
def opportunites(cartes: list, *, titre="OPPORTUNITÉS") -> str:
    L = _titre(titre)
    if not cartes:
        L.append("  Aucune. Ce n'est pas une panne : rien dans cet état de la")
        L.append("  base ne porte, à cette date, un fait commercial lisible.")
        return "\n".join(L)
    for c in cartes:
        L += _bloc_opportunite(c)
        L.append("")
    L.append(TRAIT)
    L.append(f"  {len(cartes)} opportunité(s) affichée(s).")
    L.append("  Fiche complète :  radar opportunite <ID>")
    return "\n".join(L)


def _bloc_opportunite(c: dict) -> list[str]:
    emoji = c["categorie"]["emoji"]
    code = c["categorie"]["code"]
    L = [TRAIT,
         f"{emoji} {code} — Opportunité #{c['avis_id']}",
         TRAIT, ""]
    L.append(_champ("Entreprise", c["entreprise"]["libelle"]))
    L.append(_champ("Besoin", _texte(c["opportunite"])))
    L.append(_champ("Zone", _texte(c["zone"])))
    L.append(_champ("Source(s)", " · ".join(
        s["source"] for s in c["sources"]) or service.NON_MESURE))
    L.append(_champ("État", f"{c['etat_procedure']['etat']}"
                            f"   (confiance {c['etat_procedure']['confiance']})"))
    L.append(_champ("Nature", _texte(c["nature"])))
    L.append(_champ("Score", _score(c)))
    L.append(_champ("Niveau de preuve", _texte(c["niveau_de_preuve"],
                                               service.NON_MESURE)))
    L.append("")
    L.append("Pourquoi elle est retenue :")
    L.append(f"  - {_texte(c['raison_principale'])}")
    for x in c.get("leviers", [])[:3]:
        L.append(f"  - {x}")
    L.append("")
    L.append(f"ACTION :\n  → {_texte(c['action_recommandee'])}")

    if c["nature"] in ("SIGNAL", "HYPOTHÈSE"):
        L.append("")
        L.append("  ⚠️  AUCUN besoin n'a été exprimé ici. Ce n'est pas une")
        L.append("     demande adressée à votre entreprise, et ce n'est pas")
        L.append("     la preuve d'un contrat.")

    manques = c.get("manques") or []
    if manques:
        L.append("")
        L.append("Informations manquantes :")
        for m in manques[:6]:
            L.append(f"  - {m}")

    if c.get("lectures_divergentes"):
        L.append("")
        L += _bloc_divergence(c)
    return L


def _score(c: dict) -> str:
    """Un score affiché sans son caractère mesurable se lit comme une note."""
    if not c.get("score_mesurable"):
        return f"{_texte(c['score'], service.NON_MESURE)}/100   " \
               f"(NON MESURABLE — aucun fait économique observé)"
    return f"{c['score']}/100"


def _bloc_divergence(c: dict) -> list[str]:
    d = c.get("divergence") or {}
    L = [f"{d.get('libelle', '⚠️ LECTURES DIVERGENTES')}",
         "  Les deux lectures sont réelles et datées. Ce désaccord dit ce",
         "  qui a été lu, et ce qui ne l'avait pas été.", ""]
    p = d.get("principale", {})
    L.append(f"  Lecture principale : {p.get('categorie', {}).get('emoji', '')} "
             f"{p.get('categorie', {}).get('code', '')} · {p.get('nature', '')}"
             f" · preuve {p.get('niveau_de_preuve', '')}")
    L.append(f"    → {p.get('action', '')}")
    for a in d.get("autres", []):
        L.append(f"  Autre lecture      : {a.get('categorie', {}).get('emoji', '')} "
                 f"{a.get('categorie', {}).get('code', '')} · {a.get('nature', '')}"
                 f" · preuve {a.get('niveau_de_preuve', '')}")
        for s in a.get("sources", []):
            L.append(f"    source {s['source']}  ·  vue le {s['vue_le'][:10]}")
    return L


# ═══════════════════════════════════════════════ FICHE D'UNE OPPORTUNITÉ
# Les exigences telles que le moteur les nomme, et le libellé qu'on affiche.
# Cette table ne DÉCIDE rien : elle traduit des clés déjà posées par
# `radar/capacite.py`. Une clé inconnue s'affiche telle quelle plutôt que
# d'être tue.
_LIBELLE_EXIGENCE = {
    "vehicules_min": "Véhicules",
    "chauffeurs_min": "Chauffeurs",
    "vehicule_type": "Type de véhicule",
    "tonnage_min_t": "Tonnage",
    "surface_min_m2": "Surface de dépôt",
    "anciennete_min_annees": "Ancienneté",
    "chiffre_affaires_min": "Chiffre d'affaires exigé",
    "references_min": "Références exigées",
}


def fiche_opportunite(c: dict) -> str:
    emoji, code = c["categorie"]["emoji"], c["categorie"]["code"]
    L = _titre(f"{emoji} {code} — OPPORTUNITÉ #{c['avis_id']}")

    L.append("IDENTITÉ")
    L.append(_champ("  ID", c["avis_id"], 22))
    L.append(_champ("  Titre", _texte(c["opportunite"]), 22))
    L.append(_champ("  Entreprise", c["entreprise"]["libelle"], 22))
    L.append(_champ("  Identité", c["entreprise"]["identite"]["etat"], 22))
    L.append(_champ("  Domaine", _texte(c["entreprise"]["domaine"],
                                        service.NON_MESURE), 22))
    L.append("")

    L.append("PROVENANCE")
    for s in c["sources"]:
        L.append(f"  {s['source']}")
        L.append(f"    URL      {s['reference']}")
        L.append(f"    vue le   {s['vue_le']}")
    L.append(_champ("  Découverte le", c["decouverte_le"], 22))
    L.append(_champ("  Collecte", c["surveillance"]["derniere_visite"], 22))
    L.append("")

    L.append("LES QUATRE DIMENSIONS — jamais résumées l'une par l'autre")
    L.append(_champ("  Type d'information", c["type_information"], 22))
    L.append(_champ("  Nature", _texte(c["nature"]), 22))
    L.append(_champ("  État de procédure",
                    f"{c['etat_procedure']['etat']}"
                    f"   (confiance {c['etat_procedure']['confiance']})", 22))
    L.append(_champ("  Action recommandée", _texte(c["action_recommandee"]), 22))
    L.append("")

    L.append("COMMERCIAL")
    L.append(_champ("  Catégorie", f"{emoji} {code}", 22))
    L.append(_champ("  Score", _score(c), 22))
    L.append(_champ("  Niveau de preuve",
                    _texte(c["niveau_de_preuve"], service.NON_MESURE), 22))
    L.append(_champ("  Raison principale", _texte(c["raison_principale"]), 22))
    L.append("")

    L.append("EXÉCUTION")
    L.append(_champ("  Zone", _texte(c["zone"]), 22))
    L.append(_champ("  Distance",
                    c["effort"]["distance"], 22))
    L.append(_champ("  Capacité", _texte(c["effort"]["capacite"],
                                         service.NON_MESURE), 22))
    L.append(_champ("  Montant", _texte(c["montant"], NON_PUBLIE), 22))
    L.append(_champ("  Potentiel annuel",
                    _texte(c["ca_annuel"], c["ca_etat"]), 22))
    L.append(_champ("  Durée", _texte(c["duree_mois"], NON_PUBLIE), 22))
    L.append(_champ("  Échéance", c["echeance"], 22))
    L += _bloc_exigences(c)
    L.append("")

    L.append("VOIES COMMERCIALES")
    L += _bloc_voies(c)
    L.append("")

    if c.get("leviers"):
        L.append("LEVIERS")
        for x in c["leviers"]:
            L.append(f"  - {x}")
        L.append("")

    L.append("INFORMATIONS MANQUANTES")
    if c.get("manques"):
        for m in c["manques"]:
            L.append(f"  - {m}")
    else:
        L.append("  rien d'identifié comme manquant")
    L.append("")

    if c.get("risques"):
        L.append("RISQUES ET RÉSERVES")
        for x in c["risques"]:
            L.append(f"  - {x}")
        L.append("")

    if c.get("lectures_divergentes"):
        L += _bloc_divergence(c)
        L.append("")

    L.append("SURVEILLANCE")
    s = c["surveillance"]
    L.append(_champ("  Statut", s["statut"], 22))
    L.append(_champ("  Accès", s["acces"], 22))
    L.append(_champ("  Qualification", s["qualification"], 22))
    L.append("")

    L.append("SUIVI COMMERCIAL")
    L.append(_champ("  Statut", c["suivi"]["statut"], 22))
    L.append(_champ("  Depuis", _texte(c["suivi"].get("depuis"),
                                       "aucun changement enregistré"), 22))
    L.append("")
    # UNE COMMANDE AFFICHÉE DOIT ÊTRE EXÉCUTABLE TELLE QUELLE.
    #
    # Cette ligne proposait `radar suivre --id 8`. L'option `--id` n'existe
    # pas : `suivre` attend une RÉFÉRENCE DE SOURCE — l'adresse, ou un
    # fragment qui ne désigne qu'elle (voir `suivi.resoudre`). L'exploitant
    # copiait donc une commande qui refusait de s'exécuter.
    #
    # On affiche l'adresse EXACTE plutôt qu'un fragment : `resoudre` la
    # cherche d'abord à l'identique, donc elle ne peut jamais être ambiguë.
    # Un fragment, lui, peut désigner deux affaires du même domaine — et
    # `resoudre` a raison de refuser plutôt que de choisir.
    reference = (c["sources"][0]["reference"] if c.get("sources")
                 else service.A_CONFIRMER)
    L.append(f"  Changer :  radar suivre {reference} --statut \"CONTACT À FAIRE\"")
    return "\n".join(L)


def _bloc_exigences(c: dict) -> list[str]:
    """Ce que la source EXIGE. Absent ≠ zéro : l'absence a son mot."""
    brut = c.get("exigences")
    try:
        exigences = json.loads(brut) if isinstance(brut, str) else (brut or {})
    except (TypeError, ValueError):
        exigences = {}
    if not exigences:
        return [_champ("  Exigences", NON_PUBLIE, 22)]
    L = ["  Exigences         :"]
    for cle, valeur in exigences.items():
        L.append(f"      {_LIBELLE_EXIGENCE.get(cle, cle):<26} {valeur}")
    return L


def _bloc_voies(c: dict) -> list[str]:
    """Sous-traitance, partenariat, groupement — LU dans l'action du moteur.

    Rien n'est déduit ici : si l'action posée est « PROPOSER UN GROUPEMENT »,
    c'est que `classification.classer` l'a décidé, avec sa part couverte.
    Ailleurs, on ne dit pas « impossible » — on dit qu'on ne l'a pas mesuré.
    """
    action = (c.get("action_recommandee") or "").upper()
    L = []
    for libelle, marqueur in (("Sous-traitance", "SOUS-TRAITANCE"),
                              ("Partenariat", "PARTENARIAT"),
                              ("Groupement / consortium", "GROUPEMENT")):
        if marqueur in action:
            L.append(f"  {libelle:<24} PROPOSÉE PAR LE MOTEUR — voir l'action")
        else:
            L.append(f"  {libelle:<24} {service.NON_MESURE} sur cette affaire")
    return L


# ═══════════════════════════════════════════════ ENTREPRISES
def entreprises(liste: list) -> str:
    L = _titre("ENTREPRISES DÉCOUVERTES")
    if not liste:
        L.append("  Aucune entreprise au registre.")
        return "\n".join(L)
    L.append(f"  {'DOMAINE':<28} {'ÉTAT':<13} {'IDENTITÉ':<10} BESOINS")
    L.append("  " + "-" * (LARGEUR - 2))
    for e in liste:
        L.append(f"  {str(e['domaine'] or e['cle'])[:26]:<28} "
                 f"{e['etat']:<13} {e['identite']['etat']:<10} "
                 f"{e['besoins_detectes']:>5}")
    L.append("")
    L.append(f"  {len(liste)} entreprise(s).")
    L.append("  Un DOMAINE n'est pas une raison sociale : « identité INCONNUE »")
    L.append("  veut dire qu'on ne sait pas encore qui est derrière.")
    L.append("  Fiche complète :  radar entreprise <DOMAINE>")
    return "\n".join(L)


def fiche_entreprise(f: dict) -> str:
    L = _titre(f"ENTREPRISE — {f['domaine'] or f['cle']}")
    L.append(_champ("Nom", _texte(f["nom"])))
    L.append(_champ("Identité", f["identite"]["etat"]))
    L.append(_champ("Raison sociale",
                    _texte(f["identite"]["raison_sociale"], service.A_CONFIRMER)))
    L.append(_champ("Domaine", _texte(f["domaine"], service.NON_MESURE)))
    L.append(_champ("BCE", f["bce"]))
    L.append(_champ("État", f["etat"]))
    L.append(_champ("Origine", f["origine"]))
    L.append(_champ("Découverte le", f["decouverte_le"]))
    L.append(_champ("Dernière observ.", f["derniere_visite"]))
    L.append(_champ("Marchés attribués", _texte(f["marches_gagnes"], "0")))
    L.append("")

    L.append("MOTIFS OBSERVÉS")
    for m in f.get("motifs") or ["aucun motif enregistré"]:
        L.append(f"  - {m}")
    L.append("")

    L.append(f"PAGES ({len(f['pages'])})")
    if f["pages"]:
        for p in f["pages"]:
            L.append(f"  {p['statut']:<12} {p['acces']:<18} {p['url'][:40]}")
            L.append(f"    qualification {p['qualification']}")
    else:
        L.append("  aucune page au registre")
    L.append("")

    opps = f["opportunites"]
    L.append(f"OPPORTUNITÉS ASSOCIÉES ({len(opps)})")
    signaux_ = [o for o in opps if o["nature"] in ("SIGNAL", "HYPOTHÈSE")]
    for o in opps:
        L.append(f"  {o['categorie']['emoji']} #{o['avis_id']:<5} "
                 f"{o['nature']:<10} {_texte(o['opportunite'])[:40]}")
    if not opps:
        L.append("  aucune")
    L.append("")
    L.append(f"SIGNAUX COMMERCIAUX ({len(signaux_)})")
    L.append("  Un signal n'est pas la preuve d'un contrat.")
    L.append("")
    L.append("PROCHAINE ACTION")
    suivis = {o["suivi"]["statut"] for o in opps} or {"NOUVELLE"}
    L.append(f"  suivi commercial : {' · '.join(sorted(suivis))}")
    return "\n".join(L)


# ═══════════════════════════════════════════════ SIGNAUX
def signaux(liste: list) -> str:
    L = _titre("SIGNAUX COMMERCIAUX — personne n'a rien demandé")
    if not liste:
        L.append("  Aucun signal.")
        return "\n".join(L)
    for s in liste:
        L.append(TRAIT)
        # L'en-tête dit la NATURE RÉELLE. Écrire « SIGNAL COMMERCIAL » sur
        # une HYPOTHÈSE présenterait notre propre déduction comme un fait
        # observé — exactement ce que les trois natures existent pour
        # empêcher.
        L.append(f"{s['categorie']['emoji']} {s['nature']} — #{s['avis_id']}")
        L.append(TRAIT)
        L.append("")
        L.append(_champ("Entreprise", s["entreprise"]["libelle"]))
        L.append(_champ("Signal", _texte(s["opportunite"])))
        L.append(_champ("Nature", _texte(s["nature"])))
        L.append(_champ("Niveau de preuve",
                        _texte(s["niveau_de_preuve"], service.NON_MESURE)))
        L.append("")
        L.append("Ce que nous savons :")
        for x in s["sources"]:
            L.append(f"  - vu par {x['source']} le {x['vue_le'][:10]}")
        L.append(f"  - {_texte(s['raison_principale'])}")
        L.append("")
        L.append("Ce que nous supposons :")
        L.append("  - qu'un besoin POURRAIT exister. Personne ne l'a écrit.")
        L.append("")
        L.append(f"Action :\n  → {_texte(s['action_recommandee'])}")
        L.append("")
        L.append(f"  ⚠️  {s['avertissement']}")
        L.append("")
    L.append(TRAIT)
    L.append(f"  {len(liste)} signal/signaux. Un signal ne constitue pas la")
    L.append("  preuve d'un contrat, et ne devient jamais une opportunité")
    L.append("  confirmée en montant dans la liste.")
    return "\n".join(L)


# ═══════════════════════════════════════════════ SUIVI COMMERCIAL
def suivi(liste: list) -> str:
    L = _titre("SUIVI COMMERCIAL")
    statuts = service.statuts_possibles()
    par_statut: dict = {s: [] for s in statuts}
    for a in liste:
        par_statut.setdefault(a["statut"], []).append(a)
    for s in statuts:
        lot = par_statut.get(s, [])
        L.append(f"{s}  ({len(lot)})")
        for a in lot[:12]:
            L.append(f"  {_emoji_de(a['categorie'])} #{a['avis_id']:<5} "
                     f"[{a['score']:>3}] {_texte(a['opportunite'])[:44]}")
        if not lot:
            L.append("  —")
        L.append("")
    L.append(TRAIT)
    L.append("  Le statut est posé par un humain, jamais par le moteur.")
    # Le « #8 » affiché à gauche est l'identifiant d'une OPPORTUNITÉ, et il
    # sert à `radar opportunite 8`. `suivre`, lui, prend une RÉFÉRENCE de
    # source. Les deux ne s'échangent pas : le dire ici évite d'essayer l'un
    # à la place de l'autre.
    L.append("  Changer :  radar suivre <adresse> --statut \"CONTACTÉE\"")
    L.append("  L'adresse se lit sur la fiche :  radar opportunite <ID>")
    return "\n".join(L)


# ═══════════════════════════════════════════════ NOTIFICATIONS
def notifications(liste: list) -> str:
    L = _titre(f"NOTIFICATIONS PRÉPARÉES — {len(liste)} à regarder")
    if not liste:
        L.append("  Aucune. Ce n'est pas une panne : rien dans cet état de la")
        L.append("  base ne mérite de réveiller quelqu'un. Les opportunités")
        L.append("  faibles restent en base — elles n'ont pas à vous interrompre.")
        return "\n".join(L)
    for n in liste:
        L.append(n["corps"])
        L.append(TRAIT)
    L.append("")
    L.append("  ⚠️  PRÉPARÉE N'EST PAS ENVOYÉE. Aucun courriel n'est parti,")
    L.append("     aucune entreprise n'a été contactée, aucune candidature")
    L.append("     n'a été déposée.")
    return "\n".join(L)


# ═══════════════════════════════════════════════ SOURCES
def sources(liste: list) -> str:
    L = _titre("ÉTAT RÉEL DES SOURCES")
    L.append(f"  {'SOURCE':<26} {'ÉTAT':<18} {'RÉSULTATS':>10} {'OPP.':>6}")
    L.append("  " + "-" * (LARGEUR - 2))
    if not liste:
        L.append("  Aucune source n'a encore été déclarée dans cette base.")
    for s in liste:
        L.append(f"  {s['nom'][:24]:<26} {str(s['etat'])[:16]:<18} "
                 f"{str(s['resultats']):>10} {str(s['opportunites']):>6}")
        L.append(f"     dernière consultation : {s['derniere_consultation']}")
        L.append(f"     exécution             : {s['execution']}")
        if s.get("motif"):
            L.append(f"     motif                 : {s['motif']}")
    L.append("")
    L.append("  NON DISPONIBLE n'est PAS « 0 résultat ».")
    L.append("  JAMAIS CONSULTÉE n'est PAS « 0 résultat » non plus.")
    L.append("  Une source qui n'a pas pu être lue le dit, et rien n'est inventé.")
    return "\n".join(L)


# ═══════════════════════════════════════════════ STATUT / DIAGNOSTIC
def statut(diag: dict) -> str:
    L = _titre("RADAR — ÉTAT DU SYSTÈME")
    for nom, etat in diag["composants"]:
        L.append(f"  {nom:<22} {etat}")
    L.append("")
    if diag.get("details"):
        L.append("DÉTAILS")
        for d in diag["details"]:
            L.append(f"  - {d}")
        L.append("")
    L.append("PROCHAINE COMMANDE UTILE")
    L.append(f"  {diag['suggestion']}")
    return "\n".join(L)
