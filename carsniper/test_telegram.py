"""Test Telegram — vérifie la chaîne complète et envoie une vraie alerte."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from carsniper import notify
from carsniper.storage import db
import run

print("=" * 58)
print(" TEST TELEGRAM")
print("=" * 58)

# ── 1. Les variables sont-elles définies ? ──────────────────
token = os.environ.get("TELEGRAM_TOKEN")
chat = os.environ.get("TELEGRAM_CHAT_ID")

print("\n1) Variables d'environnement")
if not token:
    print("   ✖ TELEGRAM_TOKEN absent")
else:
    print(f"   ✅ TELEGRAM_TOKEN = {token[:12]}...{token[-4:]}")
if not chat:
    print("   ✖ TELEGRAM_CHAT_ID absent")
else:
    print(f"   ✅ TELEGRAM_CHAT_ID = {chat}")

if not token or not chat:
    print("\n   Définis-les puis relance :")
    print('     set TELEGRAM_TOKEN=ton_token')
    print('     set TELEGRAM_CHAT_ID=ton_id')
    sys.exit(1)

# ── 2. Message simple ───────────────────────────────────────
print("\n2) Envoi d'un message de test...")
mid = notify.send("✅ <b>CAR SNIPER</b>\nConnexion Telegram opérationnelle.")
if mid:
    print(f"   ✅ reçu (message #{mid}) — regarde ton téléphone")
else:
    print("   ✖ échec. Causes possibles :")
    print("      • tu n'as pas envoyé /start à ton bot")
    print("      • le token ou l'ID est incorrect")
    sys.exit(1)

# ── 3. Une vraie alerte, depuis ta base ─────────────────────
print("\n3) Alerte réelle depuis la meilleure annonce en base...")
con = db.init()

row = con.execute("""
    SELECT l.id, s.deal_score, v.comparable_count
    FROM listings l
    JOIN scores s ON s.id = (SELECT id FROM scores WHERE listing_id=l.id
                             ORDER BY computed_at DESC LIMIT 1)
    LEFT JOIN valuations v ON v.id = (SELECT id FROM valuations
                             WHERE listing_id=l.id ORDER BY computed_at DESC LIMIT 1)
    WHERE l.status='active' AND v.comparable_count >= 5
    ORDER BY s.deal_score DESC LIMIT 1
""").fetchone()

if not row:
    print("   ⚠ aucune annonce évaluable en base.")
    print("     Lance 'python run.py bootstrap' puis relance ce test.")
    sys.exit(0)

res = run.analyse(con, row["id"], send_alert=False)
listing = dict(con.execute("SELECT * FROM listings WHERE id=?", (row["id"],)).fetchone())

print(f"   Annonce  : {(listing['title'] or '')[:50]}")
print(f"   Score    : {res['deal_score']} ({res['tier']})")
print(f"   Comparables : {row['comparable_count']}")

msg = notify.format_alert(listing, res, drops=0, age_days=0)
header = ("🧪 <b>TEST — alerte forcée</b>\n"
          "<i>Envoyée quel que soit le score, pour valider le format.</i>\n\n")
mid = notify.send(header + msg, listing.get("url"))

if mid:
    print("   ✅ alerte envoyée avec les boutons de feedback")
    print("\n" + "=" * 58)
    print(" Vérifie sur ton téléphone :")
    print("  • le prix et la valeur de marché s'affichent")
    print("  • les défauts détectés apparaissent")
    print("  • le bouton 'Ouvrir l'annonce' fonctionne")
    print("  • les 5 boutons de feedback sont présents")
    print("=" * 58)
else:
    print("   ✖ échec de l'envoi de l'alerte")
