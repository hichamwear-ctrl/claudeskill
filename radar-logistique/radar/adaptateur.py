"""Adaptateur de source : correspondance déclarative vers le modèle interne.

Les clés ne sont JAMAIS écrites en dur dans le code : elles vivent dans un
fichier par source, et chacune porte son état de vérification. Sur le projet
précédent, la moitié des bugs d'extraction venaient de clés plausibles qui
n'existaient pas — l'antidote est de pouvoir les corriger sans toucher au code,
et de MESURER lesquelles répondent réellement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def lire_chemin(payload, chemin: str):
    """Lit 'a.b[0].c' dans une réponse imbriquée. Renvoie None si absent."""
    courant = payload
    for morceau in chemin.split("."):
        if not morceau:
            return None
        indice = None
        if "[" in morceau and morceau.endswith("]"):
            morceau, brut = morceau[:morceau.index("[")], morceau[morceau.index("[") + 1:-1]
            try:
                indice = int(brut)
            except ValueError:
                return None
        if isinstance(courant, dict):
            courant = courant.get(morceau)
        else:
            return None
        if courant is None:
            return None
        if indice is not None:
            if not isinstance(courant, (list, tuple)) or len(courant) <= indice:
                return None
            courant = courant[indice]
    return courant


@dataclass
class Adaptateur:
    source: str
    champs: dict[str, list[str]]              # champ interne -> chemins candidats
    verifie: bool = False                     # une vraie réponse a-t-elle confirmé ?
    couverture: dict[str, int] = field(default_factory=dict)
    vocabulaire: object = None                # ce que les statuts de CETTE source veulent dire

    @classmethod
    def depuis_config(cls, cfg: dict) -> "Adaptateur":
        champs = {}
        for nom, spec in (cfg.get("champs") or {}).items():
            champs[nom] = [spec] if isinstance(spec, str) else list(spec)

        # Source en NAVIGATION WEB : l'extraction HTML produit déjà les noms
        # internes (les sélecteurs sont déclarés par champ). La correspondance
        # est donc l'identité — tout l'aval reste identique à une source JSON.
        if cfg.get("methode") == "navigation":
            for bloc in ("navigation", "detail"):
                for nom in ((cfg.get(bloc) or {}).get("champs") or {}):
                    champs.setdefault(nom, [nom])
            champs.setdefault("plateforme", ["plateforme", "lien_avis"])
            champs.setdefault("lien_documents", ["lien_documents", "lien_avis"])

        # Le vocabulaire de procédure de CETTE source : ses valeurs de statut,
        # ses types d'information, et ce qu'ils veulent dire chez elle.
        from .procedure import Vocabulaire
        return cls(source=cfg.get("source", "?"), champs=champs,
                   verifie=bool(cfg.get("verifie", False)),
                   vocabulaire=Vocabulaire(cfg))

    def extraire(self, payload: dict) -> dict:
        """Premier chemin qui répond gagne. Aucun champ n'est fabriqué."""
        sortie = {}
        for nom, chemins in self.champs.items():
            for chemin in chemins:
                v = lire_chemin(payload, chemin)
                if v not in (None, "", []):
                    sortie[nom] = v
                    break
        return sortie

    def mesurer(self, payloads: list[dict]) -> dict[str, float]:
        """Taux de présence réel de chaque champ, sur de vraies réponses.

        C'est le recensement des clés — mesuré, pas deviné. Un champ à 0 %
        signale une clé inexistante, pas une source pauvre.
        """
        total = len(payloads) or 1
        taux = {}
        for nom, chemins in self.champs.items():
            trouves = sum(
                1 for p in payloads
                if any(lire_chemin(p, c) not in (None, "", []) for c in chemins)
            )
            taux[nom] = trouves / total
            self.couverture[nom] = trouves
        return taux


# --------------------------------------------------------------- normalisation --

def _liste(v):
    if v in (None, "", []):
        return []
    return [str(x).strip().upper() for x in (v if isinstance(v, (list, tuple)) else [v]) if x]


def _codes(v):
    if v in (None, "", []):
        return []
    return [str(x).strip() for x in (v if isinstance(v, (list, tuple)) else [v]) if x]


# Espaces fines, insécables et séparateurs de milliers : une source publie
# « 120 000 » aussi souvent que 120000.
_ESPACES = "\u00a0\u202f\u2009 \t"


def _nombre(valeur, champ: str, illisibles: dict):
    """Lit un nombre publié sous n'importe quelle forme raisonnable.

    Trois issues, et une seule est acceptable pour le reste de la chaîne :
      · absent           → None, sans bruit ;
      · lisible          → un float ;
      · publié mais illisible → None ET une trace dans `illisibles`.

    Ce qui n'arrive jamais : un zéro inventé pour boucher le trou, et une
    exception qui ferait perdre tout le cycle. Un montant écrit « douze » ne
    doit pas coûter les mille autres avis du fichier.
    """
    if valeur is None or valeur == "" or valeur == [] or valeur == {}:
        return None
    if isinstance(valeur, bool):
        illisibles[champ] = valeur
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    if isinstance(valeur, (list, tuple)):
        return _nombre(valeur[0], champ, illisibles) if len(valeur) == 1 else None
    if isinstance(valeur, dict):
        illisibles[champ] = valeur
        return None

    texte = str(valeur).strip()
    for c in _ESPACES:
        texte = texte.replace(c, "")
    for jeton in ("€", "EUR", "eur", "mois", "km"):
        texte = texte.replace(jeton, "")
    if "," in texte and "." in texte:
        texte = (texte.replace(".", "").replace(",", ".")
                 if texte.rfind(",") > texte.rfind(".") else texte.replace(",", ""))
    elif "," in texte:
        # « 120,000 » est un séparateur de milliers ; « 12,5 » une décimale.
        entier, _, reste = texte.rpartition(",")
        texte = entier + reste if len(reste) == 3 and reste.isdigit() else texte.replace(",", ".")
    try:
        return float(texte)
    except ValueError:
        illisibles[champ] = valeur
        return None


def _entier(valeur, champ: str, illisibles: dict):
    n = _nombre(valeur, champ, illisibles)
    return int(round(n)) if n is not None else None


def _liste_texte(v) -> list:
    """Une liste de libellés, quelle que soit la forme reçue. Rien n'est inventé."""
    if v in (None, "", []):
        return []
    if isinstance(v, dict):
        v = list(v.values())
    if not isinstance(v, (list, tuple)):
        v = [v]
    sortie = []
    for x in v:
        if isinstance(x, dict):
            x = x.get("nom") or x.get("titre") or x.get("libelle") or x.get("name")
        if x:
            sortie.append(str(x))
    return sortie


def _evenements_de(champs: dict) -> list:
    """Les événements de procédure — chacun avec sa date quand elle est publiée."""
    brut = champs.get("evenements")
    if brut in (None, "", []):
        return []
    if not isinstance(brut, (list, tuple)):
        brut = [brut]
    sortie = []
    for e in brut:
        if isinstance(e, dict):
            nom = e.get("type") or e.get("nom") or e.get("libelle") or e.get("name")
            if nom:
                sortie.append({"type": str(nom), "date": e.get("date")})
        elif e:
            sortie.append({"type": str(e), "date": None})
    return sortie


def _exigences_de(champs: dict) -> dict:
    """Ne retient que ce qui vient d'un champ NORMÉ : une exigence structurée
    peut bloquer, une exigence lue en texte libre ne le peut jamais."""
    sortie = {}
    for cle, valeur in champs.items():
        if cle.startswith("exige_") and valeur:
            sortie[cle[len("exige_"):]] = valeur
        elif cle in ("surface_min_m2", "vehicules_min", "anciennete_min_annees",
                     "chiffre_affaires_min", "references_min") and valeur:
            sortie[cle] = valeur
    return sortie


def _lots_de(charge: dict, adaptateur, illisibles: dict) -> list:
    """Extrait les lots. Un marché sans lot déclaré en aura un : lui-même."""
    from .modele import LotBrut

    chemin = (adaptateur.champs.get("lots") or ["lots"])[0]
    brut = lire_chemin(charge, chemin)
    if not isinstance(brut, list):
        return []
    sortie = []
    for i, lot in enumerate(brut, 1):
        if not isinstance(lot, dict):
            continue
        # Les exigences d'un lot sont publiées avec les MÊMES chemins que celles
        # du marché (« requirements.min-vehicles »). Lire le lot avec ses seules
        # clés de premier niveau les perdait en silence : le lot ressortait
        # « exécutable avec la structure actuelle » alors qu'il exigeait douze
        # véhicules. On applique donc à chaque lot la carte déclarée de la source.
        champs = {**lot, **adaptateur.extraire(lot)}
        numero = str(lot.get("numero") or lot.get("lot-number") or i)
        sortie.append(LotBrut(
            numero=numero,
            intitule=str(lot.get("intitule") or lot.get("title") or ""),
            texte=str(lot.get("description") or lot.get("objet") or ""),
            cpv=_codes(lot.get("cpv") or lot.get("classification-cpv")),
            montant=_nombre(lot.get("montant") or lot.get("estimated-value"),
                            f"montant du lot {numero}", illisibles),
            duree_mois=_entier(lot.get("duree_mois") or lot.get("duration-months"),
                               f"durée du lot {numero}", illisibles),
            exigences=_exigences_de(champs),
            pays_collecte=_liste(lot.get("pays_collecte")),
            pays_livraison=_liste(lot.get("pays_livraison")),
            # Un marché peut être « attribué » alors que son lot 3 est encore
            # ouvert. Le lot garde donc SON statut, quand le portail le publie.
            statut_source=champs.get("statut") or lot.get("statut"),
            type_information=champs.get("type_information")))
    return sortie


def vers_opportunite(adaptateur, charge: dict, source: str, defauts: dict | None = None):
    """Traduit une réponse brute en Opportunite. SEUL endroit qui connaît la
    forme d'une source ; tout l'aval ignore d'où vient l'annonce."""
    from .modele import Opportunite

    c = adaptateur.extraire(charge)
    d = defauts or {}

    # Un identifiant absent ne doit JAMAIS produire une référence vide : deux
    # références vides ont la même empreinte et se fusionneraient en silence,
    # ce qui fait disparaître des opportunités. On dérive alors une référence
    # stable du contenu, et on la marque comme dérivée pour que ce soit visible.
    ref = str(c.get("identifiant") or charge.get("id") or "").strip()
    if not ref:
        import hashlib
        empreinte = hashlib.sha256(
            repr(sorted(charge.items())).encode()).hexdigest()[:12]
        ref = f"SANS-REF-{empreinte}"
    est_signal = bool(d.get("signal")) or bool(c.get("signal_code"))
    illisibles: dict = {}

    texte = " ".join(str(c.get(k, "")) for k in ("objet", "intitule", "lieu", "conditions"))
    return Opportunite(
        source=source,
        ref_source=ref,
        intitule=str(c.get("intitule") or "(sans intitulé)"),
        lots=_lots_de(charge, adaptateur, illisibles),
        texte=texte,
        type_avis=c.get("type_avis") or d.get("type_avis"),
        est_signal=est_signal,
        signal_code=c.get("signal_code") or (c.get("type_avis") if est_signal else None),
        acheteur=c.get("acheteur"),
        contact=c.get("contact_email"),
        secteur_acheteur=c.get("secteur") or d.get("secteur"),
        echeance_brute=c.get("echeance"),
        publie_le=c.get("publie_le"),
        montant=_nombre(c.get("montant"), "montant", illisibles),
        # L'unité vient de la DÉCLARATION de la source, pas du contenu : une
        # bourse de fret publie des prix récurrents, un avis de marché un total.
        montant_unite=(defauts or {}).get("montant_unite") or c.get("montant_unite"),
        devise=c.get("devise") or "EUR",
        duree_mois=_entier(c.get("duree_mois"), "durée", illisibles),
        cadence=c.get("cadence"),
        date_demarrage=c.get("date_demarrage"),
        km_annuels=_nombre(c.get("km_annuels"), "kilométrage annuel", illisibles),
        distance_depot_km=_nombre(c.get("distance_depot_km"),
                                  "distance au dépôt", illisibles),
        travail_nuit=c.get("travail_nuit"),
        travail_weekend=c.get("travail_weekend"),
        vehicules_requis=_entier(c.get("vehicules_requis"),
                                 "véhicules requis", illisibles),
        chauffeurs_requis=_entier(c.get("chauffeurs_requis"),
                                  "chauffeurs requis", illisibles),
        type_information=c.get("type_information"),
        statut_source=c.get("statut"),
        texte_statut=c.get("texte_statut"),
        evenements=_evenements_de(c),
        documents=_liste_texte(c.get("documents")),
        actions_possibles=_liste_texte(c.get("actions")),
        provenances=[{"source": source, "url": c.get("plateforme") or c.get("lien_documents"),
                      "consulte_le": (defauts or {}).get("consulte_le"),
                      "requete": (defauts or {}).get("requete")}],
        pays_collecte=_liste(c.get("pays_collecte")),
        pays_livraison=_liste(c.get("pays_livraison")) or _liste(c.get("pays")),
        lieu_texte=c.get("lieu"),
        cpv=_codes(c.get("cpv")),
        exigences=_exigences_de(c),
        exigences_texte=[t for t in (c.get("exigences_texte") or []) if t],
        lien_dossier=c.get("lien_documents") or c.get("plateforme"),
        lien_depot=c.get("plateforme"),
        plateforme=c.get("plateforme"),
        attribue=bool(c.get("attribue")),
        titulaire=c.get("titulaire"),
        attribue_le=c.get("attribue_le"),
        champs_illisibles=illisibles,
        brut=charge,
    )
