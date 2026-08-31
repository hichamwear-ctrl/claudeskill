"""Connecteur 2ememain — collecte segmentée.

L'API plafonne le nombre de pages par requête. Une seule recherche ne peut
donc jamais couvrir les 100 000 annonces. On découpe par marque, puis par
tranche de prix, en subdivisant récursivement tant qu'un segment dépasse
le plafond.

Cadence fixe, un seul thread, User-Agent identifiable, back-off sur 429,
arrêt propre en cas de blocage. Aucun contournement.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch_recent(self, pages: int) -> list[dict]: ...

    @abstractmethod
    def fetch_all(self, max_pages: int) -> list[dict]: ...

    @abstractmethod
    def parse(self, raw: dict) -> dict: ...


class BlockedError(RuntimeError):
    """Le site refuse les requetes. On s'arrete, on ne contourne pas."""


@dataclass
class TweedehandsSource(SourceAdapter):
    name: str = "2ememain"
    base: str = "https://www.2dehands.be/lrp/api/search"
    category_id: int = 91
    limit: int = 100
    delay: float = 2.5
    user_agent: str = "CarSniper/1.0 (usage personnel)"
    backoff: int = 900
    max_consecutive_errors: int = 12

    # bornes de prix en centimes (1 000 EUR a 30 000 EUR)
    price_from: int = 100_000
    price_to: int = 3_000_000

    _errors: int = 0
    _max_page: int = 0
    _budget_pages: int = 0
    _pages_lues: int = 0

    # ---- HTTP ----------------------------------------------

    def _log(self, msg: str) -> None:
        print(msg, flush=True)

    def _get(self, params: dict, retries: int = 2) -> dict:
        url = f"{self.base}?{urllib.parse.urlencode(params, doseq=True)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "fr-BE,fr;q=0.9,nl-BE;q=0.8",
        })
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = json.loads(r.read().decode("utf-8"))
                self._errors = 0
                if data.get("maxAllowedPageNumber"):
                    self._max_page = data["maxAllowedPageNumber"]
                return data
            except urllib.error.HTTPError as e:
                if e.code in (429, 403):
                    raise BlockedError(f"HTTP {e.code}") from e
                if attempt == retries:
                    self._errors += 1
                    if self._errors >= self.max_consecutive_errors:
                        raise BlockedError(f"{self._errors} erreurs consecutives") from e
                    return {}
            except Exception:
                if attempt == retries:
                    self._errors += 1
                    if self._errors >= self.max_consecutive_errors:
                        raise BlockedError(f"{self._errors} erreurs consecutives")
                    return {}
            time.sleep(self.delay * (attempt + 2))
        return {}

    def _get_strict(self, params: dict) -> dict:
        """Comme _get, mais LAISSE REMONTER l'erreur.

        _get avale toute exception non-HTTP et renvoie {} : pratique pour la
        collecte, catastrophique pour un diagnostic, qui affichait alors
        "[OK] connexion etablie" sur une connexion morte.
        """
        url = f"{self.base}?{urllib.parse.urlencode(params, doseq=True)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "fr-BE,fr;q=0.9,nl-BE;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))

    ADVERTISER_PRIVATE = 10898          # facette "Particulier"
    OFFERED_TODAY = "offeredSince:Vandaag"   # filtre natif "publiee aujourd'hui"

    @staticmethod
    def parse_date(v, ref=None) -> str | None:
        """L'API ne donne qu'une date relative : Vandaag, Gisteren, 10 aug 25.

        `ref` = date de COLLECTE. Indispensable : sans elle, un retraitement
        lance trois jours plus tard redaterait toutes les annonces "Vandaag"
        au jour du retraitement et decalerait tout l'historique.
        """
        from datetime import date, datetime as _dt, timedelta
        if not v:
            return None
        if ref is None:
            ref = date.today()
        elif isinstance(ref, str):
            try:
                ref = _dt.fromisoformat(ref.replace(" ", "T").replace("Z", "")).date()
            except ValueError:
                ref = date.today()
        t = str(v).strip().lower()
        if t in ("vandaag", "aujourd'hui", "today"):
            return ref.isoformat()
        if t in ("gisteren", "hier", "yesterday"):
            return (ref - timedelta(days=1)).isoformat()
        if t in ("eergisteren", "avant-hier"):
            return (ref - timedelta(days=2)).isoformat()
        mois = {"jan": 1, "feb": 2, "mrt": 3, "maa": 3, "apr": 4, "mei": 5,
                "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "oct": 10,
                "nov": 11, "dec": 12, "fév": 2, "mar": 3, "avr": 4, "mai": 5,
                "juin": 6, "juil": 7, "aoû": 8, "déc": 12}
        parts = t.replace(".", " ").split()
        if len(parts) >= 2 and parts[0].isdigit():
            m = mois.get(parts[1][:3])
            if m:
                jour = int(parts[0])
                an = 2000 + int(parts[2]) if len(parts) > 2 and parts[2].isdigit() \
                     else ref.year
                try:
                    return date(an, m, jour).isoformat()
                except ValueError:
                    return None
        return None

    def _params(self, offset: int, l2: int | None = None,
                pmin: int | None = None, pmax: int | None = None,
                limit: int | None = None, private_only: bool = False,
                today_only: bool = False, since: str | None = None) -> dict:
        p = {
            "l1CategoryId": self.category_id,
            "limit": limit or self.limit,
            "offset": offset,
            "sortBy": "SORT_INDEX",
            "sortOrder": "DECREASING",
            "viewOptions": "list-view",
        }
        if l2:
            p["l2CategoryId"] = l2
        if pmin is not None and pmax is not None:
            p["attributeRanges[]"] = f"PriceCents:{pmin}:{pmax}"
        if private_only:
            p["attributesById[]"] = self.ADVERTISER_PRIVATE
        if since:
            p["attributesByKey[]"] = f"offeredSince:{since}"
        elif today_only:
            # Filtre natif : c'est 2ememain qui decide ce qui date d'aujourd'hui,
            # pas notre interpretation du champ texte. Bascule a minuit cote site.
            p["attributesByKey[]"] = self.OFFERED_TODAY
        return p

    def _count(self, **kw) -> int:
        d = self._get(self._params(0, limit=1, **kw))
        time.sleep(self.delay)
        return d.get("totalResultCount", 0)

    # ---- Marques -------------------------------------------

    def brands(self) -> list[dict]:
        """Liste des sous-categories (marques), lue dynamiquement."""
        d = self._get(self._params(0, limit=1))
        opts = d.get("searchCategoryOptions", []) or []
        return [{"id": o["id"], "name": o["name"]}
                for o in opts if o.get("parentId") == self.category_id]

    # ---- Pagination d'un segment ---------------------------

    def _paginate(self, **kw) -> list[dict]:
        out: list[dict] = []
        offset = 0
        empty_streak = 0
        cap = (self._max_page or 40) * self.limit
        while offset < cap:
            if self._budget_pages and self._pages_lues >= self._budget_pages:
                self._log(f"  budget de {self._budget_pages} pages atteint")
                break
            self._pages_lues += 1
            d = self._get(self._params(offset, **kw))
            batch = d.get("listings", []) or []
            if not batch:
                # une reponse vide peut etre un hoquet reseau : on retente
                # avant de conclure que le segment est epuise
                empty_streak += 1
                if empty_streak >= 2:
                    break
                time.sleep(self.delay * 2)
                offset += self.limit
                continue
            empty_streak = 0
            out.extend(batch)
            offset += self.limit
            time.sleep(self.delay)
        return out

    def _sweep_prices(self, l2: int | None, pmin: int, pmax: int,
                      depth: int = 0) -> list[dict]:
        """Subdivise recursivement tant qu'un segment depasse le plafond."""
        n = self._count(l2=l2, pmin=pmin, pmax=pmax)
        if n == 0:
            return []
        cap = (self._max_page or 40) * self.limit
        if n <= cap or depth >= 6 or (pmax - pmin) < 20_000:
            return self._paginate(l2=l2, pmin=pmin, pmax=pmax)
        mid = (pmin + pmax) // 2
        return (self._sweep_prices(l2, pmin, mid, depth + 1)
                + self._sweep_prices(l2, mid + 1, pmax, depth + 1))

    # ---- API publique --------------------------------------

    def fetch_recent(self, pages: int = 3) -> list[dict]:
        out: list[dict] = []
        for p in range(pages):
            d = self._get(self._params(p * self.limit))
            batch = d.get("listings", []) or []
            if not batch:
                break
            out.extend(batch)
            time.sleep(self.delay)
        return out

    def fetch_all(self, max_pages: int = 0) -> list[dict]:
        """Sweep segmente : marque par marque, prix par prix.

        `max_pages` plafonne le nombre TOTAL de pages lues sur la passe.
        L'argument etait recu (bootstrap_max_pages: 900) et purement ignore.
        """
        self._budget_pages = max_pages or 0
        self._pages_lues = 0
        self._count()
        marques = self.brands()
        self._log(f"{len(marques)} marques detectees, plafond "
                  f"{self._max_page or 40} pages par requete")

        seen: set[str] = set()
        out: list[dict] = []
        for i, b in enumerate(marques, 1):
            try:
                got = self._sweep_prices(b["id"], self.price_from, self.price_to)
            except BlockedError:
                raise
            except Exception as e:
                self._log(f"  ! {b['name']} : {e}")
                continue
            neuf = 0
            for r in got:
                k = str(r.get("itemId") or "")
                if k and k not in seen:
                    seen.add(k)
                    out.append(r)
                    neuf += 1
            self._log(f"  [{i:>2}/{len(marques)}] {b['name']:<20} "
                      f"{neuf:>5} annonces   (total {len(out)})")
        return out

    # ---- Parsing -------------------------------------------

    @staticmethod
    def _attr(raw: dict, *keys) -> str | None:
        for grp in ("attributes", "extendedAttributes"):
            for a in raw.get(grp, []) or []:
                if a.get("key") in keys:
                    return a.get("value")
        return None

    @staticmethod
    def _int(v) -> int | None:
        if v is None:
            return None
        try:
            return int(str(v).replace(".", "").replace(" ", "")
                       .replace("km", "").strip())
        except ValueError:
            return None

    LEASE_WORDS = ("leasing", "renting", "lease", "huur", "location longue",
                   "par mois", "/maand", "per maand", "p/m", "mensualite")

    def parse(self, raw: dict, seller_known: str | None = None,
              fetched_at=None) -> dict:
        info = raw.get("priceInfo", {}) or {}
        price = info.get("priceCents")
        loc = raw.get("location", {}) or {}
        dist = loc.get("distanceMeters")
        return {
            "external_id": str(raw.get("itemId") or raw.get("id") or ""),
            "url": ("https://www.2dehands.be" + raw["vipUrl"]) if raw.get("vipUrl") else None,
            "title": raw.get("title"),
            "description": raw.get("categorySpecificDescription")
                           or raw.get("description") or "",
            "price_eur": int(price / 100) if isinstance(price, int) and price > 0 else None,
            "mileage_km": self._int(self._attr(raw, "mileage", "kilometerstand")),
            "year": self._int(self._attr(raw, "constructionYear", "bouwjaar")),
            "fuel": self._attr(raw, "fuel", "brandstof"),
            "transmission": self._attr(raw, "transmission", "transmissie"),
            "power_kw": self._int(self._attr(raw, "power", "vermogen")),
            "location": loc.get("cityName"),
            "postal_code": None,
            "distance_km": dist / 1000 if isinstance(dist, (int, float)) and dist > 0 else None,
            "seller_type": seller_known or self._seller_type(raw),
            "seller_id": str(raw.get("sellerInformation", {}).get("sellerId") or ""),
            "photo_count": len(raw.get("imageUrls") or []),
            "published_at": self.parse_date(raw.get("date"), fetched_at),
            "is_lease": int(self._is_lease(raw)),
            # FIXED | MIN_BID | NOTK | RESERVED | FAST_BID ...
            "price_type": info.get("priceType"),
        }

    @classmethod
    def _is_lease(cls, raw: dict) -> bool:
        """Une mensualite de leasing n'est pas un prix de vente : 520 EUR/mois
        pour un Kangoo faussait completement les comparables."""
        if (raw.get("priceInfo") or {}).get("priceType") in ("LEASE", "RENT"):
            return True
        t = ((raw.get("title") or "") + " " +
             (raw.get("categorySpecificDescription") or "")[:200]).lower()
        return any(w in t for w in cls.LEASE_WORDS)

    @staticmethod
    def _seller_type(raw: dict) -> str:
        """Le drapeau isVerified n'est PAS l'indicateur pro/particulier."""
        for grp in ("attributes", "extendedAttributes"):
            for a in raw.get(grp, []) or []:
                if a.get("key") in ("advertiser", "adverteerder"):
                    v = str(a.get("value", "")).lower()
                    if v.startswith("bedrijf") or v.startswith("profession"):
                        return "pro"
                    if v.startswith("particulier"):
                        return "particulier"
        si = raw.get("sellerInformation", {}) or {}
        if si.get("showWebsiteUrl") or si.get("isVerified"):
            return "pro"
        return "particulier"


class ManualSource(SourceAdapter):
    name = "manual"

    def fetch_recent(self, pages: int = 0) -> list[dict]:
        return []

    def fetch_all(self, max_pages: int = 0) -> list[dict]:
        return []

    def parse(self, raw: dict) -> dict:
        return raw
