"""CAR SNIPER — verification complete en une commande.

  python check.py

Verifie : versions des fichiers, connexion a 2ememain, couverture du jour,
coherence de la base, moteur d'evaluation, Telegram. Rend un verdict.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PB, AV = [], []
def ko(m): PB.append(m); print(f"   [PROBLEME] {m}")
def av(m): AV.append(m); print(f"   [ATTENTION] {m}")
def ok(m): print(f"   [OK] {m}")

AUJ = date.today().isoformat()
print("=" * 68)
print(f" CAR SNIPER — VERIFICATION COMPLETE   {AUJ}")
print("=" * 68)

# ══ 1. VERSIONS DES FICHIERS ══
print("\n1) VERSIONS DES FICHIERS")
# Marqueurs de la v3 : chacun correspond a une correction verifiee par les
# tests. Leur absence signale un fichier reste en v2.
marqueurs = {
    "run.py": ["exclure_id", "_tracer_decision", "poll_feedback",
               "telegram_configure()"],
    "carsniper/engine.py": ["score_confidence", "components_", "canon_fuel",
                            "FAMILY_WORDS", "NON_CHIFFRABLES",
                            "notification_threshold"],
    "carsniper/notify.py": ["poll_feedback", "NON enregistr",
                            "telegram_configure", "suppress_after_reaction"],
    "carsniper/storage/db.py": ["ON CONFLICT(code)", "is_lease", "value_pmin"],
    "carsniper/storage/schema.sql": ["decisions", "value_pmin", "ix_lst_vloose"],
    "carsniper/sources/twoememain.py": ["offeredSince", "_is_lease",
                                        "_get_strict", "_budget_pages"],
    "config/defects.yaml": ["fault_markers", "components_nl", "version: 2"],
    "config/profile.yaml": ["market_reference", "notification_threshold"],
}
for f, mots in marqueurs.items():
    pth = Path(f)
    if not pth.exists():
        ko(f"{f} absent")
        continue
    txt = pth.read_text(encoding="utf-8", errors="replace")
    manque = [m for m in mots if m not in txt]
    if manque:
        ko(f"{f} n'est pas a jour (manque : {manque[0]})")
    else:
        ok(f"{f}")

if PB:
    print("\n   -> remplace les fichiers signales avant de continuer.")

from carsniper import engine
from carsniper.sources.twoememain import TweedehandsSource
from carsniper.storage import db
import run

con = db.init()
src = TweedehandsSource(delay=1.5)
PROFILE, LEX = engine.load_config()
q = lambda s, *a: con.execute(s, a).fetchone()[0]

# ══ 2. CONNEXION 2EMEMAIN ══
print("\n2) CONNEXION A 2EMEMAIN")
# _get() avale les erreurs reseau et renvoie {} : un [OK] etait affiche sur
# une connexion morte, et la verification de couverture (section 3) etait
# ensuite silencieusement sautee parce que `site` valait None.
site = None
try:
    d = src._get_strict(src._params(0, limit=1, private_only=True,
                                    today_only=True))
    if not isinstance(d, dict) or not d:
        ko("reponse vide de 2ememain — endpoint injoignable ou modifie")
    elif "totalResultCount" not in d:
        ko("reponse invalide : champ 'totalResultCount' absent "
           f"(cles recues : {sorted(d)[:6]}) -> structure de l'API changee")
    else:
        site = d["totalResultCount"]
        ok(f"connexion etablie — {site} annonces particuliers aujourd'hui")
except Exception as e:
    ko(f"connexion impossible : {type(e).__name__}: {e}")

# ══ 3. COUVERTURE DU JOUR ══
print("\n3) COUVERTURE DU JOUR")
base = q("SELECT COUNT(*) FROM listings WHERE published_at=?", AUJ)
prix = q("SELECT COUNT(*) FROM listings WHERE published_at=? AND price_eur IS NOT NULL", AUJ)
part = q("SELECT COUNT(*) FROM listings WHERE published_at=? AND seller_type='particulier' AND year>=2005", AUJ)
scor = q("SELECT COUNT(DISTINCT s.listing_id) FROM scores s JOIN listings l "
         "ON l.id=s.listing_id WHERE l.published_at=?", AUJ)
print(f"   site {site} | base {base} | avec prix {prix} | particuliers 2005+ {part} | scorees {scor}")

if site is None:
    ko("couverture du jour NON VERIFIEE : le site est injoignable "
       "(voir section 2)")
elif site:
    manquant = site - base
    if manquant > site * 0.15:
        ko(f"{manquant} annonces du jour non collectees "
           f"({manquant/site:.0%}) -> lancer 'python run.py fast'")
    elif manquant > 0:
        av(f"{manquant} annonces d'ecart (cache du site, tolerable)")
    else:
        ok("couverture complete")

if prix and scor < prix * 0.9:
    ko(f"{prix - scor} annonces avec prix mais sans score")
elif prix:
    ok("toutes les annonces avec prix sont scorees")

# ══ 4. COHERENCE DE LA BASE ══
print("\n4) COHERENCE DE LA BASE")
tot = q("SELECT COUNT(*) FROM listings")
cle = q("SELECT COUNT(*) FROM listings WHERE vkey IS NOT NULL")
dup = q("SELECT COUNT(*) FROM (SELECT external_id FROM listings GROUP BY external_id HAVING COUNT(*)>1)")
print(f"   {tot} annonces, {cle} avec cle de comparaison ({cle/max(tot,1):.0%})")
ko(f"{dup} doublons") if dup else ok("aucun doublon")
if cle < 20000:
    ko(f"seulement {cle} comparables -> lancer 'python run.py bootstrap'")
else:
    ok("base de comparaison suffisante")

# ══ 5. MOTEUR D'EVALUATION ══
print("\n5) MOTEUR D'EVALUATION")
fuite = q("SELECT COUNT(*) FROM scores WHERE confidence_score < 0.5 AND deal_score > 74")
ko(f"{fuite} scores eleves sur estimation faible") if fuite else ok("garde-fou operationnel")

# On teste la reference qui DECIDE du score (pmin), pas p25 qui n'etait
# affiche nulle part dans le calcul.
abs_ = con.execute("""SELECT l.title, l.price_eur,
                             COALESCE(v.value_pmin, v.value_p25) AS ref,
                             v.comparable_count, s.confidence_score
    FROM listings l
    JOIN valuations v ON v.id=(SELECT id FROM valuations WHERE listing_id=l.id
                               ORDER BY computed_at DESC LIMIT 1)
    JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                           ORDER BY computed_at DESC LIMIT 1)
    WHERE COALESCE(v.value_pmin, v.value_p25) > l.price_eur * 3
      AND s.confidence_score >= 0.5
    LIMIT 5""").fetchall()
if abs_:
    ko(f"{len(abs_)} estimations aberrantes AVEC confiance elevee")
    for r in abs_:
        print(f"      {r['price_eur']}EUR vs {r['ref']}EUR "
              f"({r['comparable_count']} comp) {(r['title'] or '')[:32]}")
else:
    ok("aucune estimation aberrante credible")

mc = con.execute("""SELECT AVG(v.comparable_count) c, AVG(s.confidence_score) f
    FROM valuations v JOIN listings l ON l.id=v.listing_id
    JOIN scores s ON s.listing_id=l.id
    WHERE l.published_at=? AND v.comparable_count>=8""", (AUJ,)).fetchone()
if mc and mc["c"]:
    print(f"   moyenne : {mc['c']:.0f} comparables, confiance {mc['f']:.0%}")
    if mc["f"] < 0.45:
        av("confiance moyenne faible -> peu d'alertes possibles")

# ══ 6. LEXIQUE ══
print("\n6) LEXIQUE DES DEFAUTS")
act = q("SELECT COUNT(*) FROM listing_defects WHERE is_negated=0")
nie = q("SELECT COUNT(*) FROM listing_defects WHERE is_negated=1")
print(f"   {act} defauts actifs, {nie} negations")
ok(f"{len(LEX['defects'])} entrees chargees")

# ══ 7. TELEGRAM ══
print("\n7) TELEGRAM")
tok, cid = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
if not tok or not cid:
    av("variables absentes — les alertes resteront dans la console")
else:
    try:
        u = f"https://api.telegram.org/bot{tok}/getMe"
        r = json.loads(urllib.request.urlopen(u, timeout=15).read().decode())
        ok(f"bot @{r['result']['username']} operationnel")
    except Exception as e:
        ko(f"token invalide : {e}")

al = q("SELECT COUNT(*) FROM alerts")
fb = q("SELECT COUNT(*) FROM feedback")
sans_mid = q("SELECT COUNT(*) FROM alerts WHERE telegram_message_id IS NULL")
print(f"   {al} alertes envoyees, {fb} retours enregistres")
if sans_mid:
    av(f"{sans_mid} alertes sans identifiant de message : leurs boutons de "
       f"feedback ne pourront jamais etre rattaches")
row = con.execute("SELECT value FROM meta WHERE key='tg_offset'").fetchone()
offset = int(row["value"]) if row else 0
if tok and cid and al and offset == 0:
    ko("aucun update Telegram n'a jamais ete lu (tg_offset=0) : les clics "
       "sur les boutons ne sont pas traites -> lancer 'python run.py fast'")
elif offset:
    ok(f"boucle de feedback active (dernier update lu : {offset})")

# ── 8. TRACABILITE ──
print("\n8) TRACABILITE DES DECISIONS")
try:
    dec = q("SELECT COUNT(*) FROM decisions")
    tracees = q("SELECT COUNT(*) FROM alerts a WHERE EXISTS("
                "SELECT 1 FROM decisions d WHERE d.listing_id=a.listing_id)")
    print(f"   {dec} decisions tracees")
    if al and tracees < al:
        av(f"{al - tracees} alertes anterieures ne sont pas explicables "
           f"(envoyees avant la mise en place de la tracabilite)")
    else:
        ok("chaque alerte peut etre expliquee apres coup")
except Exception as e:
    ko(f"table decisions absente : {e}")

# ══ VERDICT ══
print("\n" + "=" * 68)
if PB:
    print(f" {len(PB)} PROBLEME(S) A CORRIGER")
    for x in PB:
        print(f"   - {x}")
else:
    print(" TOUT FONCTIONNE")
if AV:
    print(f"\n {len(AV)} point(s) d'attention")
    for x in AV:
        print(f"   - {x}")
print("=" * 68)
