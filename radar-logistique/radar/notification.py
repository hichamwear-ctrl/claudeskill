"""CE QUI MÉRITE UN REGARD HUMAIN — et rien de plus.

    OPPORTUNITÉ EXISTANTE   ≠   NOTIFICATION À AFFICHER

Une opportunité faible RESTE EN BASE. Elle ne réveille personne, et elle ne
disparaît pas non plus. Ce sont deux questions différentes :

    « cette affaire existe-t-elle ? »   → la chaîne d'analyse, déjà écrite
    « dois-je la regarder ce matin ? »  → ici

CE MODULE N'ÉCRIT AUCUNE RÈGLE DE SÉLECTION
===========================================

Il n'invente pas de seuil de score, et surtout il ne s'en sert pas pour
supprimer quoi que ce soit. La question « faut-il réveiller quelqu'un ? »
a déjà sa réponse dans `classification.Type.notifiable`, validée depuis
longtemps : ni un REJET ni une OBSERVATION ne réveillent le commercial.

Ce module LIT cette réponse. Il ne la recalcule pas.

LE BOT N'ENVOIE RIEN
====================

Une notification est un texte déposé en base. Aucun courriel n'est envoyé,
aucune entreprise n'est contactée, aucune candidature n'est déposée. Le bot
PRÉPARE ; l'humain décide et agit.

IDEMPOTENCE PAR LE SCEAU
========================

Le sceau est l'empreinte du corps notifié. Relancer le même cycle sur les
mêmes données ne renotifie rien : le sceau est déjà là. Mais si le contenu
CHANGE — une échéance qui bouge, un titulaire qui apparaît — le sceau change
avec lui, et la notification repart. C'est exactement ce qu'on veut : ne pas
répéter, ne pas taire.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

A_CONFIRMER = "À CONFIRMER"
NON_MESURE = "NON MESURÉ"

# Pourquoi on réveille. Jamais « parce que le score est élevé » : un score
# classe, il ne déclenche pas.
NOUVELLE = "NOUVELLE OPPORTUNITÉ"
MODIFIEE = "OPPORTUNITÉ MODIFIÉE"
RENOUVELLEMENT = "RENOUVELLEMENT APPROCHANT"
DEVELOPPEMENT = "TITULAIRE À DÉVELOPPER"

EMOJI = {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
         "PROSPECT": "🔵", "PAS ENCORE UNE OPPORTUNITÉ": "⚪", "REJET": "🔴"}


def merite_une_alerte(type_valeur) -> bool:
    """La règle existante, LUE et non réécrite.

    `classification.Type.notifiable` dit déjà qu'un REJET et une OBSERVATION
    ne réveillent personne. Recopier ce jugement ici en ferait une seconde
    version, qui finirait par diverger de la première.
    """
    from .classification import Type
    for t in Type:
        if t.value == type_valeur:
            return t.notifiable
    return False


def sceau(corps: str) -> str:
    return hashlib.sha256(corps.encode("utf-8", "replace")).hexdigest()[:32]


@dataclass
class Notification:
    avis_id: int | None
    motif: str
    corps: str
    sceau: str
    cycle_id: str | None = None
    creee_le: str | None = None


def _liste(valeur, vide: str) -> str:
    import json
    try:
        items = json.loads(valeur) if valeur else []
    except (TypeError, ValueError):
        return str(valeur)
    return " · ".join(str(i) for i in items) if items else vide


def carte(cx, ligne, *, motif: str = NOUVELLE) -> str:
    """La carte que l'exploitant lit le matin.

    Elle doit répondre à quatre questions et à aucune autre :
    qu'est-ce que c'est · pourquoi on me le montre · que puis-je faire ·
    qu'est-ce qui reste incertain.

    Ce qui manque s'écrit. Un champ vide laisserait croire que l'information
    a été cherchée et qu'elle vaut zéro.
    """
    from .entreprises import domaine_de
    emoji = EMOJI.get(ligne["type"], "·")
    domaine = domaine_de(ligne["ref_source"])
    etat_identite = "INCONNUE"
    if domaine:
        try:
            from . import identite as mod_identite
            etat_identite = mod_identite.lire(cx, domaine).etat.value
        except Exception:                                        # noqa: BLE001
            pass
    entreprise = ligne["acheteur"] or (
        f"domaine {domaine} (identité {etat_identite} — pas une raison sociale)"
        if domaine else f"entreprise {A_CONFIRMER}")

    adequation = (f"{ligne['score']}/100" if ligne["score_mesurable"]
                  else "NON MESURABLE — aucun fait économique observé")
    ca = (f"{ligne['ca_annuel']:,.0f} €/an".replace(",", " ")
          if ligne["ca_annuel"] else (ligne["ca_etat"] or NON_MESURE))
    effort = []
    effort.append(f"{ligne['distance_km']:.0f} km" if ligne["distance_km"]
                  is not None else f"distance {A_CONFIRMER}")
    effort.append(ligne["capacite"] or f"capacité {A_CONFIRMER}")

    L = [f"🔔 {motif}", ""]
    L.append(f"Entreprise      {entreprise}")
    L.append(f"Besoin          {(ligne['intitule'] or A_CONFIRMER)[:70]}")
    L.append(f"Type d'info     {ligne['type_information'] or 'NON DÉCLARÉ PAR LA SOURCE'}")
    L.append(f"Nature          {ligne['nature'] or A_CONFIRMER}")
    L.append(f"Procédure       {ligne['etat_procedure'] or 'INCONNU'}"
             f"   (confiance {ligne['confiance_etat'] or A_CONFIRMER})")
    L.append(f"Classification  {emoji} {ligne['type']}")
    L.append(f"Adéquation      {adequation}")
    L.append(f"Preuve          {ligne['fiabilite'] or A_CONFIRMER}")
    L.append(f"Potentiel       {ca}")
    L.append(f"Pourquoi        {(ligne['motif'] or A_CONFIRMER)[:70]}")
    L.append(f"Action          {ligne['action'] or A_CONFIRMER}")
    L.append(f"Effort          {' · '.join(effort)}")
    L.append(f"Échéance        {ligne['echeance'] or 'NON PUBLIÉE'}")
    L.append(f"Zone            {ligne['zone'] or A_CONFIRMER}")
    L.append(f"Source          {ligne['source']}")
    L.append(f"Preuves         {ligne['ref_source']}")
    L.append(f"État source     {ligne['etat_source'] if 'etat_source' in ligne.keys() else NON_MESURE}")
    manque = _liste(ligne["manques"], "")
    risques = _liste(ligne["risques"], "")
    L.append("")
    L.append("⚠️ À CONFIRMER")
    L.append(f"   {manque or 'rien d’identifié comme manquant'}")
    if risques:
        L.append(f"   {risques[:150]}")
    L.append("")
    L.append("   Le bot n'a contacté personne et n'a rien envoyé. Il prépare ;")
    L.append("   la décision et l'action restent humaines.")
    return "\n".join(L)


def deposer(cx, avis_id, corps, *, motif: str = NOUVELLE,
            cycle_id=None) -> Notification | None:
    """Dépose une notification, SAUF si son sceau est déjà connu.

    Rend None quand rien n'a été déposé — c'est le signal d'idempotence, et
    il se lit : « rien de neuf sur celle-ci ».
    """
    from .base import maintenant
    s = sceau(corps)
    if cx.execute("SELECT 1 FROM notifications WHERE sceau=?", (s,)).fetchone():
        return None
    quand = maintenant()
    cx.execute(
        "INSERT INTO notifications(avis_id, motif, sceau, corps, cycle_id,"
        " creee_le) VALUES(?,?,?,?,?,?)",
        (avis_id, motif, s, corps, cycle_id, quand))
    return Notification(avis_id=avis_id, motif=motif, corps=corps, sceau=s,
                        cycle_id=cycle_id, creee_le=quand)


def _lignes_notifiables(cx):
    return cx.execute(
        "SELECT o.*, a.ref_source, a.source FROM opportunites o"
        " JOIN avis a ON a.id = o.avis_id"
        " ORDER BY o.score DESC").fetchall()


def preparer(cx, *, cycle_id=None) -> list[Notification]:
    """Prépare les notifications du cycle. N'envoie RIEN.

    Une opportunité non notifiable reste en base, intacte : ne pas réveiller
    quelqu'un n'est pas la supprimer.
    """
    sortie = []
    for ligne in _lignes_notifiables(cx):
        if not merite_une_alerte(ligne["type"]):
            continue
        n = deposer(cx, ligne["avis_id"], carte(cx, ligne), motif=NOUVELLE,
                    cycle_id=cycle_id)
        if n is not None:
            sortie.append(n)

    # RENOUVELLEMENTS — une attribution dont l'échéance approche redevient une
    # piste. Elle ne devient JAMAIS postulable pour autant.
    for l in cx.execute(
            "SELECT t.*, a.ref_source, a.source FROM attributions t"
            " JOIN avis a ON a.id = t.avis_id"
            " WHERE t.renouvellement IS NOT NULL").fetchall():
        corps = "\n".join([
            f"🔔 {RENOUVELLEMENT}", "",
            f"Titulaire       {l['titulaire'] or A_CONFIRMER}",
            f"Acheteur        {l['acheteur'] or A_CONFIRMER}",
            f"Fin             {l['fin'] or A_CONFIRMER}",
            f"Renouvellement  {l['renouvellement']}",
            f"Prestation      {(l['prestation'] or A_CONFIRMER)[:60]}",
            "Action          CONTACTER LE TITULAIRE · SURVEILLER LE RENOUVELLEMENT",
            f"Preuves         {l['ref_source']}",
            "",
            "   Un marché ATTRIBUÉ n'est pas POSTULABLE et ne le devient",
            "   jamais. C'est une piste de développement.",
        ])
        n = deposer(cx, l["avis_id"], corps, motif=RENOUVELLEMENT,
                    cycle_id=cycle_id)
        if n is not None:
            sortie.append(n)
    return sortie


def toutes(cx, *, cycle_id=None, limite=None) -> list[Notification]:
    sql, args = "SELECT * FROM notifications", []
    if cycle_id:
        sql += " WHERE cycle_id=?"
        args.append(cycle_id)
    sql += " ORDER BY id DESC"
    if limite:
        sql += f" LIMIT {int(limite)}"
    return [Notification(avis_id=l["avis_id"], motif=l["motif"], corps=l["corps"],
                         sceau=l["sceau"], cycle_id=l["cycle_id"],
                         creee_le=l["creee_le"])
            for l in cx.execute(sql, args).fetchall()]


def rapport(cx, *, cycle_id=None, limite=10) -> str:
    liste = toutes(cx, cycle_id=cycle_id, limite=limite)
    L = [f"NOTIFICATIONS — {len(liste)} à regarder", "=" * 80, ""]
    if not liste:
        L.append("  Aucune. Ce n'est pas une panne : rien dans cet état de la")
        L.append("  base ne mérite de réveiller quelqu'un. Les opportunités")
        L.append("  faibles restent en base — elles n'ont simplement pas à")
        L.append("  vous interrompre.")
        return "\n".join(L)
    for n in liste:
        L.append(n.corps)
        L.append("-" * 80)
    return "\n".join(L)
