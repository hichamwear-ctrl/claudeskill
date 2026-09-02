"""File d'envoi durable. L'envoi n'a JAMAIS lieu dans une transaction."""

from __future__ import annotations

from .base import maintenant


def mettre_en_file(cx, source: str, ref: str, corps: str) -> bool:
    """Écrit l'intention d'alerter. Renvoie False si elle existait déjà."""
    cur = cx.execute(
        "INSERT OR IGNORE INTO envois(source, ref_source, corps, cree_le, maj_le) "
        "VALUES(?,?,?,?,?)", (source, ref, corps, maintenant(), maintenant()))
    return cur.rowcount == 1


def a_envoyer(cx, limite: int = 50):
    return cx.execute(
        "SELECT * FROM envois WHERE etat='a_envoyer' ORDER BY id LIMIT ?", (limite,)).fetchall()


def _transition(cx, envoi_id: int, etat: str, erreur: str | None = None):
    cx.execute("UPDATE envois SET etat=?, maj_le=?, erreur=? WHERE id=?",
               (etat, maintenant(), erreur, envoi_id))
    cx.commit()                     # chaque transition validée séparément


def vider(cx, transport) -> dict:
    """Draine la file. `transport(corps)` fait l'appel réseau, hors transaction.

    Trois issues seulement : délivré, échec (réessayable), ambigu (jamais
    réémis). L'ambiguïté ne se supprime pas — on décide quoi en faire.
    """
    compte = {"delivre": 0, "echec": 0, "ambigu": 0}
    for ligne in a_envoyer(cx):
        _transition(cx, ligne["id"], "en_cours")
        cx.execute("UPDATE envois SET tentatives=tentatives+1 WHERE id=?", (ligne["id"],))
        cx.commit()
        try:
            transport(ligne["corps"])                  # <- hors transaction
        except TimeoutError as e:
            _transition(cx, ligne["id"], "ambigu", f"issue inconnue : {e}")
            compte["ambigu"] += 1
        except Exception as e:                          # noqa: BLE001
            _transition(cx, ligne["id"], "echec", str(e))
            compte["echec"] += 1
        else:
            _transition(cx, ligne["id"], "delivre")
            compte["delivre"] += 1
    return compte


def reprendre_interrompus(cx) -> int:
    """Un « en_cours » au démarrage veut dire que le programme est mort pendant
    l'appel. On ne peut pas savoir si le message est parti : on ne renvoie pas."""
    cur = cx.execute(
        "UPDATE envois SET etat='ambigu', erreur='programme interrompu pendant l''envoi', "
        "maj_le=? WHERE etat='en_cours'", (maintenant(),))
    cx.commit()
    return cur.rowcount
