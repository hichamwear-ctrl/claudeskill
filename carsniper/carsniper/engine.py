"""CAR SNIPER — moteur d'analyse.

Pipeline : normalisation → défauts → marché → réparations → risque
           → revente → urgence → Deal Score
"""
from __future__ import annotations

import json
import math
import re
import statistics
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

def load_config() -> tuple[dict, dict]:
    profile = yaml.safe_load((CONFIG / "profile.yaml").read_text(encoding="utf-8"))
    lexicon = yaml.safe_load((CONFIG / "defects.yaml").read_text(encoding="utf-8"))
    return profile, lexicon


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def norm_text(s: str | None) -> str:
    return re.sub(r"\s+", " ", strip_accents((s or "").lower()))


# ═══════════════════════════════════════════════════════════
# 1. NORMALISATION DU VÉHICULE
# ═══════════════════════════════════════════════════════════

# Marques absentes = annonces inexploitables. Les ajouts ci-dessous
# representent ~3 099 annonces de la base reelle (MG 1 133, Rover 785,
# Chevrolet 386, Iveco 220, Saab 126, SsangYong 103, Lancia 87...).
BRANDS = [
    "abarth", "alfa romeo", "alpine", "aston martin", "audi", "bentley",
    "bmw", "byd", "cadillac", "chevrolet", "chrysler", "citroen", "cupra",
    "dacia", "daewoo", "daihatsu", "dodge", "ds", "ferrari", "fiat", "ford",
    "genesis", "honda", "hyundai", "infiniti", "isuzu", "iveco", "jaguar",
    "jeep", "kia", "lada", "lamborghini", "lancia", "land rover", "lexus",
    "maserati", "mazda", "mercedes", "mg", "mini", "mitsubishi", "nissan",
    "opel", "peugeot", "polestar", "porsche", "renault", "rover", "saab",
    "seat", "skoda", "smart", "ssangyong", "subaru", "suzuki", "tesla",
    "toyota", "volkswagen", "volvo",
]
STOPWORDS = {
    "te", "koop", "a", "vendre", "auto", "voiture", "wagen", "car", "occasion",
    "mooie", "belle", "super", "prachtige", "zeer", "tres", "met", "avec",
    "van", "de", "la", "le", "en", "et", "of", "ou", "n", "in", "goede",
    "bon", "etat", "staat", "nieuwe", "nieuw", "neuf", "annee", "bj", "bwj",
}
BRAND_ALIASES = {
    "vw": "volkswagen", "mercedes-benz": "mercedes", "mercedes benz": "mercedes",
    "alfa": "alfa romeo", "landrover": "land rover", "range rover": "land rover",
    # fautes de frappe relevees dans les titres de la base
    "mercedez": "mercedes", "mercedez benz": "mercedes", "merecedes": "mercedes",
    "peugoet": "peugeot", "peugeut": "peugeot", "peugot": "peugeot",
    "wolkswagen": "volkswagen", "volskwagen": "volkswagen",
    "citroën": "citroen", "citroen ds": "ds", "ssang yong": "ssangyong",
    "vauxhall": "opel",
}

# Valeur canonique -> variantes. Le champ "fuel" du site arrive en
# neerlandais ("Benzine", "Hybride elektrisch/benzine") : sans passage par
# cette table, la valeur BRUTE finissait dans la cle de comparaison et
# coupait le marche essence en deux moities qui ne se voyaient pas
# (10 321 "benzine" contre 9 835 "essence" sur la base reelle).
FUELS = {
    "diesel": ["diesel", "gasoil", "mazout", "tdi", "hdi", "cdi", "dci", "crdi",
               "jtd", "d4d", "bluehdi", "tdci"],
    "essence": ["essence", "benzine", "benzin", "petrol", "tsi", "tfsi", "vti",
                "thp", "mpi", "fsi", "gasoline"],
    "hybride": ["hybride", "hybrid", "phev", "hev", "hybride elektrisch/benzine",
                "hybride elektrisch/diesel", "plug-in hybride", "mhev"],
    "electrique": ["electrique", "elektrisch", "electric", "ev", "bev"],
    "lpg": ["lpg", "gpl", "autogas"],
    "cng": ["cng", "aardgas", "cng (aardgas)"],
}
# index plat variante -> canonique, le plus long d'abord
FUEL_MAP = {v: canon for canon, alts in FUELS.items() for v in alts}
FUEL_CANON = set(FUELS)
# Valeurs du site qui ne designent aucun carburant exploitable : on les
# traite comme INCONNU plutot que de les laisser polluer la cle.
FUEL_UNKNOWN = {"overige brandstoffen", "andere", "autre", "waterstof",
                "overige", "other"}


def canon_fuel(value: str | None) -> str | None:
    """Ramene n'importe quelle ecriture du carburant a sa forme canonique."""
    v = norm_text(value)
    if not v or v in FUEL_UNKNOWN:
        return None
    if v in FUEL_CANON:
        return v
    if v in FUEL_MAP:
        return FUEL_MAP[v]
    for variant in sorted(FUEL_MAP, key=len, reverse=True):
        if re.search(rf"\b{re.escape(variant)}\b", v):
            return FUEL_MAP[variant]
    return None


AUTO_HINTS = ["automatique", "automaat", "automatic", "dsg", "tiptronic", "s-tronic",
              "stronic", "steptronic", "edc", "eat8", "eat6", "cvt", "pdk", "boite auto"]
MANUAL_HINTS = ["manuelle", "manueel", "handgeschakeld", "boite manuelle", "6 vitesses"]


BODY_HINTS = {
    "break": ("break", "avant", "sw", "estate", "variant", "touring", "kombi",
              "sportstourer", "tourer"),
    "cabrio": ("cabrio", "cabriolet", "roadster", "convertible", "spider"),
    "coupe": ("coupe", "coupé"),
    "sportback": ("sportback", "gran coupe", "grandcoupe", "fastback"),
    "monospace": ("monospace", "scenic", "touran", "picasso", "zafira",
                  "sharan", "espace", "galaxy", "verso"),
    # "van" et "combi" retires : en neerlandais "van" veut dire "de".
    # 1 003 citadines sur 5 960 (Golf, Corsa, C3...) etaient classees
    # utilitaire parce que leur description contenait ce mot.
    "utilitaire": ("utilitaire", "bestelwagen", "fourgon", "lichte vracht",
                   "camionnette", "kastenwagen"),
}


@dataclass
class Vehicle:
    make: str | None = None
    model: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    displacement: float | None = None     # 1.6, 2.0 ...
    body: str | None = None               # break, cabrio, sportback ...
    power_kw: int | None = None
    year: int | None = None
    confidence: float = 0.0
    # d'ou vient l'information : "site" (declaree) ou "titre" (devinee)
    model_source: str | None = None
    body_source: str | None = None

    def key(self) -> str:
        """Cle STRICTE : deux vehicules ne sont comparables que s'ils
        partagent marque, modele, carburant, boite, cylindree et carrosserie.
        Une A3 1.6 TDI berline n'est pas une A3 2.0 TDI Sportback."""
        d = f"{self.displacement:.1f}" if self.displacement else "?"
        return (f"{self.make}|{self.model}|{self.fuel}|{self.transmission}"
                f"|{d}|{self.body or 'berline'}")


# Mots qui annoncent une FAMILLE, pas un modele : "BMW Serie 3",
# "Mercedes Classe A". Les prendre pour le modele creait des cles
# fourre-tout — `bmw|serie` melangeait 40 voitures de 1 500 a 26 690 EUR,
# et `mercedes|classe` des Classe A avec des Classe E.
FAMILY_WORDS = {"serie", "series", "classe", "klasse", "class", "modele",
                "model", "type", "gamme"}

# Tokens qui ne designent jamais un modele.
MODEL_JUNK = {"berline", "break", "coupe", "cabrio", "cabriolet", "monospace",
              "suv", "diesel", "essence", "benzine", "elektrisch", "hybride",
              "automaat", "automatique", "manuelle", "manueel", "occasion",
              "km", "euro", "eur", "bj", "bwj", "an", "annee", "jaar", "pk",
              "ch", "kw", "cc", "portes", "deurs", "places", "zit", "tdi",
              "hdi", "cdi", "dci", "tsi", "tfsi", "vendre", "koop", "utilitaire"}

# Peugeot 2008/3008/5008 sont des modeles, pas des annees.
PEUGEOT_YEARLIKE = {"2008", "3008", "5008", "1007", "4007", "4008"}


def _model_token(tok: str, make: str, allow_short: bool = False) -> str | None:
    """Valide un token candidat comme modele.

    `allow_short` sert apres un mot de famille : dans "Serie 1" / "Classe B",
    le chiffre ou la lettre isolee EST le modele.
    """
    tok = tok.strip(" -.,/")
    if not tok:
        return None
    if len(tok) < 2 and not (allow_short and re.fullmatch(r"[a-z0-9]", tok)):
        return None
    # "a" est un mot vide francais, mais "Classe A" est un modele : apres un
    # mot de famille, une lettre isolee reste valide.
    court = allow_short and re.fullmatch(r"[a-z0-9]", tok)
    if tok in FAMILY_WORDS or tok in MODEL_JUNK:
        return None
    if tok in STOPWORDS and not court:
        return None
    # une annee n'est pas un modele (sauf 2008/3008/5008 chez Peugeot)
    if re.fullmatch(r"(19|20)\d{2}", tok) and not (
            make == "peugeot" and tok in PEUGEOT_YEARLIKE):
        return None
    # cylindree ecrite "1.6" / "2,0"
    if re.fullmatch(r"\d[.,]\d", tok):
        return None
    # 320d et 320 doivent converger : le carburant est stocke a part
    return re.sub(r"(?<=\d)[di]$", "", tok)


def _extract_model(make: str, after: str) -> str | None:
    """Modele = premier token exploitable apres la marque.

    Si ce token annonce une famille ("serie", "classe"), deux cas :

      * la suite porte deja un code precis  -> on garde ce code seul, pour que
        "Serie 320d" et "320d" tombent dans la MEME cle ;
      * la suite n'est qu'un chiffre nu     -> on fusionne ("serie 1" ->
        "serie1"), ce qui garde les generations separees au lieu de les
        empiler sous un `bmw|serie` fourre-tout.
    """
    toks = re.findall(r"[a-z0-9][a-z0-9\-\.]{0,14}", after)
    for i, raw in enumerate(toks[:4]):
        base = raw.strip(" -.,/")
        if base in FAMILY_WORDS:
            suite = [t for t in (_model_token(x, make, allow_short=True)
                                 for x in toks[i + 1:i + 4]) if t]
            if not suite:
                return None                      # "serie" seul : inexploitable
            precis = next((t for t in suite
                           if len(t) >= 3 and re.search(r"\d", t)), None)
            return precis or f"{base}{suite[0]}"
        tok = _model_token(base, make)
        if tok:
            return tok
    return None


# Modele declare par 2ememain -> marque, DERIVE de la base reelle
# (464 associations, retenues a partir de 8 observations et 90 % de
# concordance). Sert de repli quand la marque n'apparait pas dans le
# titre : "GOLF 5 UNITED" -> volkswagen, "3 reeks" -> bmw.
MODEL_BRAND = {
    "1-reeks": "bmw", "100": "audi", "1007": "peugeot",
    "107": "peugeot", "108": "peugeot", "124-spider": "fiat",
    "156": "alfa romeo", "159": "alfa romeo", "19": "renault",
    "190-serie": "mercedes", "2": "mazda", "2-reeks": "bmw",
    "2-reeks-active-tourer": "bmw", "2-reeks-gran-coupe": "bmw", "2-reeks-gran-tourer": "bmw",
    "200-serie": "mercedes", "2008": "peugeot", "206": "peugeot",
    "207": "peugeot", "208": "peugeot", "240": "volvo",
    "2cv": "citroen", "3-reeks": "bmw", "3-reeks-gt": "bmw",
    "300-serie": "mercedes", "3008": "peugeot", "307": "peugeot",
    "308": "peugeot", "4": "renault", "4-reeks": "bmw",
    "4-reeks-gran-coupe": "bmw", "407": "peugeot", "408": "peugeot",
    "5-reeks": "bmw", "5-reeks-gt": "bmw", "500": "fiat",
    "5008": "peugeot", "500c": "fiat", "500e": "fiat",
    "500l": "fiat", "500x": "fiat", "508": "peugeot",
    "595": "abarth", "6": "mazda", "6-reeks": "bmw",
    "6-sportbreak": "mazda", "600": "fiat", "7-reeks": "bmw",
    "80": "audi", "90": "audi", "911": "porsche",
    "924": "porsche", "928": "porsche", "944": "porsche",
    "a-klasse": "mercedes", "a1": "audi", "a2": "audi",
    "a3": "audi", "a4": "audi", "a5": "audi",
    "a6": "audi", "a7": "audi", "a8": "audi",
    "accord": "honda", "adam": "opel", "agila": "opel",
    "alhambra": "seat", "almera": "nissan", "altea": "seat",
    "altea-xl": "seat", "alto": "suzuki", "amarok": "volkswagen",
    "antara": "opel", "arkana": "renault", "arona": "seat",
    "arteon": "volkswagen", "astra": "opel", "asx": "mitsubishi",
    "ateca": "seat", "atos": "hyundai", "auris": "toyota",
    "austral": "renault", "avenger": "jeep", "avensis": "toyota",
    "aveo": "chevrolet", "aygo": "toyota", "aygo-x": "toyota",
    "b": "mg", "b-klasse": "mercedes", "b-max": "ford",
    "baleno": "suzuki", "barchetta": "fiat", "bayon": "hyundai",
    "beetle-kever": "volkswagen", "berlingo": "citroen", "bigster": "dacia",
    "bipper": "peugeot", "boxer": "peugeot", "boxster": "porsche",
    "bravo": "fiat", "c-hr": "toyota", "c-klasse": "mercedes",
    "c-max": "ford", "c1": "citroen", "c2": "citroen",
    "c3": "citroen", "c3-aircross": "citroen", "c3-picasso": "citroen",
    "c30": "volvo", "c4": "citroen", "c4-cactus": "citroen",
    "c4-grand-picasso": "citroen", "c5": "citroen", "c5-aircross": "citroen",
    "c5-x": "citroen", "c70": "volvo", "caddy-combi": "volkswagen",
    "caddy-maxi": "volkswagen", "captiva": "chevrolet", "captur": "renault",
    "carens": "kia", "cascada": "opel", "cayenne": "porsche",
    "cayman": "porsche", "celerio": "suzuki", "celica": "toyota",
    "cherokee": "jeep", "chevy-van": "chevrolet", "citan-combi": "mercedes",
    "citigo": "skoda", "civic": "honda", "cl": "mercedes",
    "cla": "mercedes", "clio": "renault", "clk": "mercedes",
    "cls": "mercedes", "clubman": "mini", "colt": "mitsubishi",
    "combo-tour": "opel", "compass": "jeep", "cooper": "mini",
    "cooper-s": "mini", "corolla": "toyota", "corolla-cross": "toyota",
    "corolla-ts": "toyota", "corsa": "opel", "corsa-e": "opel",
    "corvette": "chevrolet", "countryman": "mini", "cr-v": "honda",
    "crossland-x": "opel", "cruze": "chevrolet", "crx": "honda",
    "ct-h": "lexus", "cx-3": "mazda", "cx-30": "mazda",
    "cx-5": "mazda", "defender": "land rover", "delta": "lancia",
    "discovery": "land rover", "discovery-sport": "land rover", "doblo": "fiat",
    "dokker": "dacia", "ds": "ds", "ds-3": "ds",
    "ds-4": "ds", "ds-7": "ds", "ds3": "citroen",
    "ds4": "citroen", "ds5": "citroen", "ducato": "fiat",
    "duster": "dacia", "e-klasse": "mercedes", "e-pace": "jaguar",
    "e-tron": "audi", "eclipse": "mitsubishi", "ecosport": "ford",
    "edge": "ford", "ehs": "mg", "eos": "volkswagen",
    "espace": "renault", "expert-combi": "peugeot", "f": "mg",
    "f-150": "ford", "f-pace": "jaguar", "fabia": "skoda",
    "fiesta": "ford", "focus": "ford", "forfour": "smart",
    "formentor": "cupra", "fortwo": "smart", "fox": "volkswagen",
    "freelander": "land rover", "frontera": "opel", "fusion": "ford",
    "g-klasse": "mercedes", "galaxy": "ford", "getz": "hyundai",
    "ghibli": "maserati", "giulia": "alfa romeo", "giulietta": "alfa romeo",
    "gla": "mercedes", "glb": "mercedes", "glc": "mercedes",
    "glc-coupe": "mercedes", "gle": "mercedes", "glk": "mercedes",
    "golf": "volkswagen", "golf-plus": "volkswagen", "golf-sportsvan": "volkswagen",
    "golf-variant": "volkswagen", "grand-c-max": "ford", "grand-cherokee": "jeep",
    "grand-scenic": "renault", "grand-vitara": "suzuki", "grande-punto": "fiat",
    "grandland": "opel", "grandland-x": "opel", "gtv": "alfa romeo",
    "hilux": "toyota", "hr-v": "honda", "i-pace": "jaguar",
    "i10": "hyundai", "i20": "hyundai", "i3": "bmw",
    "i30": "hyundai", "i40": "hyundai", "ibiza": "seat",
    "id3": "volkswagen", "idea": "fiat", "ignis": "suzuki",
    "impreza": "subaru", "insignia": "opel", "ioniq": "hyundai",
    "iq": "toyota", "is": "lexus", "ix20": "hyundai",
    "ix35": "hyundai", "jazz": "honda", "jetta": "volkswagen",
    "jimny": "suzuki", "jogger": "dacia", "john-cooper-works": "mini",
    "juke": "nissan", "jumper": "citroen", "jumpy-combi": "citroen",
    "junior": "alfa romeo", "ka": "ford", "kadjar": "renault",
    "kamiq": "skoda", "kangoo": "renault", "karl": "opel",
    "karoq": "skoda", "kodiaq": "skoda", "koleos": "renault",
    "kona": "hyundai", "korando": "ssangyong", "kuga": "ford",
    "l200": "mitsubishi", "laguna": "renault", "lancer": "mitsubishi",
    "landcruiser": "toyota", "lbx": "lexus", "leaf": "nissan",
    "lodgy": "dacia", "logan": "dacia", "logan-mcv": "dacia",
    "m-klasse": "mercedes", "macan": "porsche", "master": "renault",
    "megane": "renault", "meriva": "opel", "mg4": "mg",
    "micra": "nissan", "mito": "alfa romeo", "model-3": "tesla",
    "model-s": "tesla", "model-y": "tesla", "modus": "renault",
    "mokka": "opel", "mokkax": "opel", "mondeo": "ford",
    "movano": "opel", "mr2": "toyota", "multivan": "volkswagen",
    "musa": "lancia", "mustang": "ford", "mx-30": "mazda",
    "mx-5": "mazda", "mx-5-rf": "mazda", "navara-double-cab": "nissan",
    "nemo": "citroen", "niro": "kia", "niva": "lada",
    "note": "nissan", "nv400": "nissan", "nx": "lexus",
    "octavia": "skoda", "one": "mini", "optima": "kia",
    "orlando": "chevrolet", "outlander": "mitsubishi", "pajero": "mitsubishi",
    "panamera": "porsche", "panda": "fiat", "partner": "peugeot",
    "partner-tepee": "peugeot", "passat": "volkswagen", "patrol": "nissan",
    "picanto": "kia", "pixo": "nissan", "polestar-2": "polestar",
    "polo": "volkswagen", "prius": "toyota", "pro-cee-d": "kia",
    "proace": "toyota", "proace-city": "toyota", "pulsar": "nissan",
    "puma": "ford", "punto": "fiat", "punto-evo": "fiat",
    "q2": "audi", "q3": "audi", "q30": "infiniti",
    "q5": "audi", "q7": "audi", "qashqai": "nissan",
    "qashqai2": "nissan", "quattro": "audi", "quattroporte": "maserati",
    "qubo": "fiat", "ram-1500": "dodge", "range-rover": "land rover",
    "range-rover-evoque": "land rover", "range-rover-sport": "land rover", "range-rover-velar": "land rover",
    "ranger": "ford", "rapid": "skoda", "rav4": "toyota",
    "rcz": "peugeot", "renegade": "jeep", "rexton": "ssangyong",
    "rifter": "peugeot", "rio": "kia", "rodius": "ssangyong",
    "roomster": "skoda", "rx-8": "mazda", "rx-h": "lexus",
    "s-cross": "suzuki", "s-klasse": "mercedes", "s-max": "ford",
    "s-type": "jaguar", "s3": "audi", "s4": "audi",
    "s40": "volvo", "s60": "volvo", "s80": "volvo",
    "s90": "volvo", "saab-9-3": "saab", "saab-9-5": "saab",
    "saab-900": "saab", "samurai": "suzuki", "sandero": "dacia",
    "sandero-stepway": "dacia", "santa-fe": "hyundai", "saxo": "citroen",
    "scala": "skoda", "scenic": "renault", "scirocco": "volkswagen",
    "scudo": "fiat", "series": "land rover", "sharan": "volkswagen",
    "silverado": "chevrolet", "sirion": "daihatsu", "sl": "mercedes",
    "slc": "mercedes", "slk": "mercedes", "sorento": "kia",
    "soul": "kia", "space-star": "mitsubishi", "space-tourer": "citroen",
    "spark": "chevrolet", "spider": "alfa romeo", "splash": "suzuki",
    "sportage": "kia", "spring": "dacia", "sprinter-combi": "mercedes",
    "sq5": "audi", "starlet": "toyota", "stelvio": "alfa romeo",
    "stonic": "kia", "superb": "skoda", "swift": "suzuki",
    "sx4": "suzuki", "symbioz": "renault", "t-cross": "volkswagen",
    "t-roc": "volkswagen", "taigo": "volkswagen", "talento": "fiat",
    "talisman": "renault", "tarraco": "seat", "tigra": "opel",
    "tiguan": "volkswagen", "tipo": "fiat", "tivoli": "ssangyong",
    "toledo": "seat", "tonale": "alfa romeo", "touareg": "volkswagen",
    "touran": "volkswagen", "tourneo-connect": "ford", "tourneo-courier": "ford",
    "trafic": "renault", "transit": "ford", "transporter": "volkswagen",
    "trax": "chevrolet", "tt": "audi", "tucson": "hyundai",
    "twingo": "renault", "up": "volkswagen", "ux": "lexus",
    "v-klasse": "mercedes", "v40": "volvo", "v50": "volvo",
    "v60": "volvo", "v70": "volvo", "v90": "volvo",
    "vectra": "opel", "venga": "kia", "verso": "toyota",
    "verso-s": "toyota", "viano": "mercedes", "vitara": "suzuki",
    "vito": "mercedes", "vivaro": "opel", "wind": "renault",
    "wrangler": "jeep", "x-trail": "nissan", "x-type": "jaguar",
    "x1": "bmw", "x2": "bmw", "x3": "bmw",
    "x4": "bmw", "x5": "bmw", "x6": "bmw",
    "xc40": "volvo", "xc60": "volvo", "xc90": "volvo",
    "xceed": "kia", "xe": "jaguar", "xf": "jaguar",
    "xj": "jaguar", "xjs": "jaguar", "xk": "jaguar",
    "xlv": "ssangyong", "xsara": "citroen", "yaris": "toyota",
    "yaris-cross": "toyota", "yeti": "skoda", "ypsilon": "lancia",
    "z3": "bmw", "z4": "bmw", "zafira": "opel",
    "zoe": "renault", "zs": "mg",
}


def _model_du_site(valeur: str | None, make: str | None) -> str | None:
    """Normalise le modele declare par 2ememain.

    "Overige modellen" (= autres modeles) n'est pas un modele : c'est le
    fourre-tout du site, il ne doit surtout pas devenir une cle.
    """
    v = norm_text(valeur)
    if not v or v in ("overige modellen", "andere", "autre", "overige",
                      "other", "overige modellen/merken"):
        return None
    # "Saab 9-3" -> on retire la marque si elle est repetee dans le modele
    if make and v.startswith(make + " "):
        v = v[len(make) + 1:]
    v = re.sub(r"[^a-z0-9\- ]", "", v).strip()
    v = re.sub(r"\s+", "-", v)
    return v[:24] or None


def _marque_du_modele(valeur: str | None) -> str | None:
    """Retrouve la marque a partir du modele declare par le site.

    Deux chemins : le modele contient deja la marque ("Saab 9-3"), ou la
    table MODEL_BRAND l'associe sans ambiguite. Sauve les titres ou la
    marque n'apparait pas — 3,1 % des annonces de la base.
    """
    v = norm_text(valeur)
    if not v:
        return None
    for b in sorted(BRANDS, key=len, reverse=True):
        if v.startswith(b):
            return b
    return MODEL_BRAND.get(_model_du_site(valeur, None) or "")


def vehicle_usable(v: "Vehicle", min_conf: float = 0.55) -> bool:
    """Le vehicule est-il assez sûrement identifie pour servir de base a
    une comparaison ? Sans marque ET modele, la reponse est non : mieux
    vaut aucune estimation qu'une estimation batie sur un mauvais pool."""
    if not (v.make and v.model):
        return False
    if v.model in FAMILY_WORDS or len(v.model) < 2:
        return False
    return v.confidence >= min_conf


# Carrosseries declarees par 2ememain -> notre vocabulaire interne.
SITE_BODY = {
    "berline": "berline", "sedan": "berline", "hatchback": "berline",
    "stadsauto": "berline", "citadine": "berline",
    "break": "break", "stationwagen": "break", "combi": "break",
    "coupe": "coupe", "cabriolet": "cabrio", "roadster": "cabrio",
    "monovolume": "monospace", "mpv": "monospace",
    "suv of terreinwagen": "suv", "suv": "suv", "terreinwagen": "suv",
    "4x4": "suv", "tout-terrain": "suv",
    "bestelwagen": "utilitaire", "utilitaire": "utilitaire",
    "lichte vracht": "utilitaire", "minibus": "utilitaire",
}
SITE_BODY_INCONNU = {"overige carrosserie", "andere", "autre", "overige"}


def canon_body(value: str | None) -> str | None:
    """Ramene la carrosserie DECLAREE par le site a notre vocabulaire."""
    v = norm_text(value)
    if not v or v in SITE_BODY_INCONNU:
        return None
    if v in SITE_BODY:
        return SITE_BODY[v]
    for k, canon in SITE_BODY.items():
        if k in v:
            return canon
    return None


def normalize_vehicle(title: str, description: str = "", year: int | None = None,
                      fuel_hint: str | None = None,
                      transmission_hint: str | None = None,
                      site_model: str | None = None,
                      site_body: str | None = None) -> Vehicle:
    t = norm_text(title)
    full = t + " " + norm_text(description)[:600]
    v = Vehicle(year=year)
    conf = 0.0

    # Marque — on retient le mot RÉELLEMENT présent dans le titre, pas le
    # nom canonique : sinon "Vw Polo" cherche "volkswagen" dans le texte,
    # ne le trouve pas, et prend "vw" comme modèle.
    matched = None
    for alias, real in sorted(BRAND_ALIASES.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(alias)}\b", t):
            v.make, matched = real, alias
            break
    if not v.make:
        for b in sorted(BRANDS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(b)}\b", t):
                v.make, matched = b, b
                break
    if v.make:
        conf += 0.40

    # Modèle — la valeur DÉCLARÉE par 2ememain prime sur la devinette faite
    # à partir du titre. C'est elle qui évite les clés fourre-tout, et elle
    # sauve les titres où la marque n'apparaît pas ("GOLF 5 UNITED").
    declare = _model_du_site(site_model, v.make)
    if declare:
        v.model = declare
        v.model_source = "site"
        conf += 0.30
        if not v.make:
            v.make = _marque_du_modele(site_model) or v.make
    elif v.make and matched:
        after = t.split(matched, 1)[-1].strip()
        v.model = _extract_model(v.make, after)
        if v.model:
            v.model_source = "titre"
            conf += 0.25

    # Carburant — le champ du site fait foi, ramené à sa forme canonique.
    # Le suffixe des codes moteur (320d, 118i) sert de repli.
    v.fuel = canon_fuel(fuel_hint)
    if not v.fuel:
        if re.search(r"\b\d{3}\s?d\b|\b\d{2,3}\s?cdi\b|\bd\d\b", t):
            v.fuel = "diesel"
        elif re.search(r"\b\d{3}\s?i\b|\b\d{3}\s?e\b", t):
            v.fuel = "essence"
    if not v.fuel:
        v.fuel = canon_fuel(full)
    if v.fuel:
        conf += 0.15

    # Boîte
    if transmission_hint:
        v.transmission = "automatique" if "auto" in norm_text(transmission_hint) else "manuelle"
    else:
        if any(h in full for h in AUTO_HINTS):
            v.transmission = "automatique"
        elif any(h in full for h in MANUAL_HINTS):
            v.transmission = "manuelle"
    if v.transmission:
        conf += 0.10

    # Cylindree : 1.6 TDI, 2.0d, 1,4 essence
    m = re.search(r"\b([0-9])[.,]([0-9])\b", t)
    if m:
        cc = float(f"{m.group(1)}.{m.group(2)}")
        if 0.6 <= cc <= 6.5:
            v.displacement = cc
            conf += 0.05

    # Carrosserie — le site d'abord. Les mots-clés ne servent que de repli :
    # c'est eux qui avaient classé 1 003 citadines en "utilitaire" à cause du
    # mot néerlandais "van".
    v.body = canon_body(site_body)
    if v.body:
        v.body_source = "site"
    else:
        for label, mots in BODY_HINTS.items():
            if any(re.search(rf"\b{re.escape(w)}\b", full) for w in mots):
                v.body = label
                v.body_source = "titre"
                break

    # Puissance
    m = re.search(r"(\d{2,3})\s?(ch|pk|hp)\b", full)
    if m:
        v.power_kw = int(int(m.group(1)) * 0.7355)
        conf += 0.05
    elif (m := re.search(r"(\d{2,3})\s?kw\b", full)):
        v.power_kw = int(m.group(1))
        conf += 0.05

    if year:
        conf += 0.05

    v.confidence = round(min(conf, 1.0), 2)
    return v


# ═══════════════════════════════════════════════════════════
# 2. DETECTION DES DÉFAUTS (avec négation)
# ═══════════════════════════════════════════════════════════

@dataclass
class DefectHit:
    code: str
    category: str
    severity: int
    matched: str
    context: str
    negated: bool
    confidence: float
    market_discount: tuple[int, int]
    pro_cost: tuple[int, int]
    risk_penalty: int = 0
    checklist: list[str] = field(default_factory=list)
    # v2 : d'ou vient la certitude. "fault_term" = la formulation EST un
    # defaut ; "component+marker" = un organe cite avec un marqueur de panne.
    evidence: str = "fault_term"
    trigger: str | None = None      # le marqueur de panne qui a tranche


MIN_COMPARABLES = 8      # en dessous, on refuse d'evaluer

# Une proposition = l'unite de rattachement. Les annonces sont des listes
# d'equipement ("airco, cruise control, jantes alu") : chercher un marqueur
# de panne a +/- 6 mots sans respecter les frontieres de proposition faisait
# de "airco" un defaut des qu'un mot negatif trainait plus loin.
# Le point n'est PAS un separateur entre chiffres : "165.000 km".
_CLAUSE_RE = re.compile(r"(?<!\d)\.(?!\d)|[;!?•|()\[\]\n\r]|,| - | -- |\u2022")


def _clauses(text: str) -> list[str]:
    return [c for c in (p.strip() for p in _CLAUSE_RE.split(text)) if c]


def _compile_terms(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    """Un terme prefixe par "re:" est une expression reguliere brute.
    Les autres sont pris litteralement, bornes par des frontieres de mot."""
    out = []
    for t in terms or []:
        t = strip_accents(str(t).lower()).strip()
        if not t:
            continue
        if t.startswith("re:"):
            try:
                out.append((t[3:], re.compile(t[3:])))
            except re.error:
                continue
        else:
            out.append((t, re.compile(rf"\b{re.escape(t)}\b")))
    return out


_LEX_CACHE: dict[int, dict] = {}


def _lexicon_index(lexicon: dict) -> dict:
    """Compile une fois par lexique : la detection tourne sur 53 000 annonces."""
    key = id(lexicon)
    hit = _LEX_CACHE.get(key)
    if hit is not None:
        return hit

    idx = {
        "faults": _compile_terms(lexicon.get("fault_markers", [])),
        "upkeep": _compile_terms(lexicon.get("maintenance_markers", [])),
        "negations": _compile_terms(lexicon.get("negations_global", [])),
        "defects": [],
    }
    for d in lexicon.get("defects", []):
        comps = list(d.get("components_fr", []) or []) + \
                list(d.get("components_nl", []) or [])
        fauts = list(d.get("faults_fr", []) or []) + \
                list(d.get("faults_nl", []) or [])
        # Compatibilite v1 : sans les nouvelles cles, terms_* sont des
        # formulations auto-suffisantes, comme avant.
        if not comps and not fauts:
            fauts = list(d.get("terms_fr", []) or []) + \
                    list(d.get("terms_nl", []) or [])
        idx["defects"].append({
            "raw": d,
            "components": _compile_terms(comps),
            "faults": _compile_terms(fauts),
        })
    _LEX_CACHE[key] = idx
    return idx


def _first_match(clause: str, terms: list[tuple[str, re.Pattern]]) -> str | None:
    """Renvoie le TEXTE reellement trouve — un motif brut serait illisible
    en base et dans l'alerte Telegram."""
    for label, rx in terms:
        m = rx.search(clause)
        if m:
            return m.group(0).strip() or label
    return None


def detect_defects(text: str, lexicon: dict) -> list[DefectHit]:
    """Detection v2 — distingue l'organe cite de l'organe en panne.

    Regles, appliquees proposition par proposition :

      1. une formulation de defaut ("motorschade", "koppeling versleten")
         vaut defaut a elle seule ;
      2. le seul nom d'un organe ("airco", "versnellingsbak") est NEUTRE :
         il ne devient un defaut que si un marqueur de panne figure dans la
         MEME proposition ;
      3. une negation explicite ("geen", "aucun", "jamais") prime sur tout ;
      4. un marqueur d'entretien fait ("vervangen", "neuf") marque l'organe
         comme sain, pas comme defectueux ;
      5. les modificateurs ("vendu en l'état") ne se nient jamais.

    Un organe cite sans aucun de ces signaux ne produit AUCUN hit : c'est
    une caracteristique du vehicule, pas une panne.
    """
    body = norm_text(text)
    if not body:
        return []
    idx = _lexicon_index(lexicon)
    hits: list[DefectHit] = []
    seen: set[str] = set()

    for clause in _clauses(body):
        neg = _first_match(clause, idx["negations"])
        fault_mark = _first_match(clause, idx["faults"])
        upkeep = _first_match(clause, idx["upkeep"])

        for entry in idx["defects"]:
            d = entry["raw"]
            code = d["code"]
            if code in seen:
                continue

            matched = _first_match(clause, entry["faults"])
            evidence = "fault_term"
            if matched is None:
                comp = _first_match(clause, entry["components"])
                if comp is None:
                    continue
                # L'organe est cite. Sans signal, c'est de l'equipement.
                if fault_mark is None and upkeep is None and neg is None:
                    continue
                matched = comp
                evidence = "component+marker" if fault_mark else "component"

            is_modifier = d["category"] == "modifier"
            if is_modifier:
                negated = False
            elif neg:
                negated = True
            elif evidence == "fault_term":
                negated = bool(upkeep) and fault_mark is None
            else:
                negated = fault_mark is None

            # Une deduction "organe + marqueur" est moins sure qu'une
            # formulation explicite : la certitude descend, et avec elle la
            # confiance finale de l'estimation.
            conf = float(d.get("base_confidence", 0.7))
            if evidence == "component+marker":
                conf = round(conf * 0.85, 2)

            seen.add(code)
            hits.append(DefectHit(
                code=code,
                category=d["category"],
                severity=d["severity"],
                matched=matched,
                context=clause[:240],
                negated=negated,
                confidence=conf,
                market_discount=tuple(d["market_discount"]),
                pro_cost=tuple(d["pro_cost"]),
                risk_penalty=d.get("risk_penalty", 0),
                checklist=d.get("checklist", []),
                evidence=evidence,
                trigger=fault_mark if evidence == "component+marker" else None,
            ))
    return hits


# ═══════════════════════════════════════════════════════════
# 3. MARKET ENGINE
# ═══════════════════════════════════════════════════════════

@dataclass
class Valuation:
    pmin: int | None = None      # la moins chere comparable du site
    p25: int | None = None
    p50: int | None = None
    p75: int | None = None
    n: int = 0
    method: str = "insufficient_data"
    confidence: float = 0.0
    # ── tracabilite : permet d'expliquer une alerte apres coup ──
    pool_verifie: float = 0.0     # part du pool passee par la detection
    iqr_ratio: float = 0.0        # dispersion relative
    flou_moyen: float = 0.0       # dimensions inconnues par comparable
    rejets_flous: int = 0         # comparables ecartes faute d'annee/km
    comparables: list = field(default_factory=list)
    # ── v3 : l'ancre, c'est la VRAIE moins chere comparable ──
    moins_chere_brute: int | None = None   # le minimum absolu, meme incomplet
    ancre_complete: bool = True            # l'ancre a-t-elle une config connue ?
    mediane: int | None = None
    exclus: list = field(default_factory=list)   # aberrants bas ecartes
    doublons: int = 0                      # republications retirees
    niveau: str = ""                       # strict | elargi | large


UNKNOWN = ("none", "?", "", "null")


def _compat(target_key: str, cand_key: str) -> tuple[bool, int]:
    """Compare deux cles champ par champ.

    Marque et modele doivent toujours coincider. Pour les autres dimensions
    (carburant, boite, cylindree, carrosserie), l'egalite n'est exigee que
    si l'information est connue des DEUX cotes : une annonce qui ne precise
    pas sa boite ne doit pas etre exclue, mais chaque inconnue coute de la
    confiance.

    Retourne (compatible, nombre_d_inconnues).
    """
    a, b = target_key.split("|"), cand_key.split("|")
    if len(a) != len(b):
        return False, 0
    if a[0] != b[0] or a[1] != b[1]:        # marque + modele : strict
        return False, 0
    flous = 0
    for x, y in zip(a[2:], b[2:]):
        xu, yu = x.lower() in UNKNOWN, y.lower() in UNKNOWN
        if xu or yu:
            flous += 1
            continue
        if x != y:
            return False, 0
    return True, flous


def _mad_filter(prices: list[float]) -> list[int]:
    """Suppression des aberrants par écart absolu médian."""
    if len(prices) < 4:
        return list(range(len(prices)))
    med = statistics.median(prices)
    devs = [abs(p - med) for p in prices]
    mad = statistics.median(devs) or 1.0
    return [i for i, p in enumerate(prices) if abs(p - med) / (1.4826 * mad) <= 3.0]


# Tolerances mesurees sur la base reelle, pas choisies au jugé.
# Ecart de prix median entre deux voitures de MEME cle :
#     annee   1 an -> 12 %   2 ans -> 17 %   3 ans -> 21 %   5 ans -> 33 %
#     km      10 % ->  1 %   30 %  -> 11 %   50 %  -> 12 %   80 % -> 17 %
# L'annee pese ~4x plus que le kilometrage : on serre l'annee, on relache le
# kilometrage. L'ancien reglage (±1 an / ±15 % km) faisait l'inverse et
# ecartait 177 des 251 annonces du jour restees sans comparables.
NIVEAUX = (
    {"nom": "strict", "year": 1, "km": 0.30, "fiabilite": 1.00},
    {"nom": "elargi", "year": 2, "km": 0.40, "fiabilite": 0.93},
    {"nom": "large",  "year": 3, "km": 0.50, "fiabilite": 0.85},
)

# Au-dela de ce nombre de dimensions inconnues, un comparable reste utile
# pour situer le marche mais ne peut pas servir d'ANCRE a lui seul.
FLOU_MAX_ANCRE = 1
MIN_ANCRES_COMPLETES = 3


def _cle_doublon(c: dict) -> tuple:
    """Deux annonces republiees decrivent la MEME voiture. Les compter deux
    fois donne l'illusion qu'il existe plusieurs voitures a ce prix."""
    return (norm_text(c.get("title"))[:60], c.get("price_eur"),
            c.get("year"), c.get("mileage_km"))


def _dedupliquer(comps: list[dict]) -> tuple[list[dict], int]:
    vus, out = set(), []
    for c in comps:
        k = _cle_doublon(c)
        if k in vus:
            continue
        vus.add(k)
        out.append(c)
    return out, len(comps) - len(out)


def _aberrants_bas(prix: list[float]) -> set[int]:
    """Indices des prix anormalement BAS.

    On ne filtre que vers le bas : c'est l'ancre qui nous interesse, et une
    annonce a 1 000 EUR au milieu d'un marche a 5 000 EUR ne doit pas
    devenir la reference. Les prix hauts, eux, ne genent personne.
    """
    if len(prix) < 6:
        return set()
    med = statistics.median(prix)
    ecarts = [abs(p - med) for p in prix]
    mad = statistics.median(ecarts) or 1.0
    # Deux criteres, l'un statistique, l'autre de bon sens : une voiture a
    # moins de 45 % de la mediane de sa propre configuration n'est pas la
    # meme voiture (epave, erreur de saisie, prix par mois...). L'ecart
    # median mesure seul laissait passer 1 900 EUR dans un marche a 4 400.
    return {i for i, p in enumerate(prix)
            if p < med and ((med - p) / (1.4826 * mad) > 3.0
                            or p < med * 0.45)}


def _choisir_ancre(comps: list[dict]) -> tuple[dict, dict | None]:
    """Retourne (ancre, moins_chere_brute).

    L'ancre est la VRAIE moins chere — jamais une moyenne. Mais une annonce
    dont la configuration est largement inconnue est compatible avec presque
    tout : si c'est elle la moins chere et qu'il existe assez de comparables
    complets, on prend le moins cher des complets et on le signale.
    """
    par_prix = sorted(comps, key=lambda c: c["price_eur"])
    brute = par_prix[0]
    complets = [c for c in par_prix if c.get("_flous", 0) <= FLOU_MAX_ANCRE]
    if brute.get("_flous", 0) <= FLOU_MAX_ANCRE:
        return brute, None
    if len(complets) >= MIN_ANCRES_COMPLETES:
        return complets[0], brute
    return brute, None


def value_market(target: dict, pool: list[dict]) -> Valuation:
    """Constitue les comparables et designe la moins chere.

    Trois paliers de tolerance, du plus strict au plus large. On s'arrete au
    premier qui atteint MIN_COMPARABLES : la marque, le modele, le
    carburant, la boite, la cylindree et la carrosserie restent TOUJOURS
    exiges — on n'elargit que sur l'annee et le kilometrage.
    """
    t_year, t_km = target.get("year"), target.get("mileage_km")
    if not t_year or not t_km:
        return Valuation(method="insufficient_data")

    for lvl in NIVEAUX:
        comps = []
        rejets_flous = 0
        for c in pool:
            if c.get("has_defect") or not c.get("price_eur"):
                continue
            ok, flous = _compat(target.get("vkey", ""), c.get("vkey") or "")
            if not ok:
                continue
            if not c.get("year") or not c.get("mileage_km"):
                rejets_flous += 1
                continue
            if abs(c["year"] - t_year) > lvl["year"]:
                continue
            if abs(c["mileage_km"] - t_km) > max(t_km * lvl["km"], 15000):
                continue
            comps.append({**c, "_flous": flous})

        comps, doublons = _dedupliquer(comps)
        if len(comps) < MIN_COMPARABLES:
            continue

        prix = [float(c["price_eur"]) for c in comps]
        idx_ab = _aberrants_bas(prix)
        exclus = sorted(int(prix[i]) for i in idx_ab)
        comps = [c for i, c in enumerate(comps) if i not in idx_ab]
        prix = [p for i, p in enumerate(prix) if i not in idx_ab]
        if len(comps) < MIN_COMPARABLES:
            continue

        ancre, brute = _choisir_ancre(comps)
        n = len(comps)
        tries = sorted(prix)
        p25 = int(tries[max(0, int(n * 0.25) - 1)])
        p50 = int(statistics.median(tries))
        p75 = int(tries[min(n - 1, int(n * 0.75))])
        iqr_ratio = (p75 - p25) / p50 if p50 else 1.0

        # ── qualite du pool ──
        flou_moyen = sum(c.get("_flous", 0) for c in comps) / n
        penalite_flou = max(0.70, 1 - flou_moyen * 0.10)
        connus = sum(1 for c in comps
                     if c.get("defauts_analyses", "has_defect" in c))
        part_verifiee = connus / n
        penalite_verif = 0.80 + 0.20 * part_verifiee
        penalite_disp = max(0.0, 1 - min(iqr_ratio, 0.6) * 0.8)
        conf = (min(1.0, n / 12) * penalite_disp * penalite_flou
                * penalite_verif * lvl["fiabilite"])

        val = Valuation(
            pmin=int(ancre["price_eur"]), p25=p25, p50=p50, p75=p75, n=n,
            method="weighted_median" if lvl["nom"] == "strict"
            else "weighted_median_elargi",
            confidence=round(conf, 2))
        val.moins_chere_brute = int(brute["price_eur"]) if brute else int(ancre["price_eur"])
        val.ancre_complete = brute is None
        val.mediane = p50
        val.exclus = exclus
        val.doublons = doublons
        val.niveau = lvl["nom"]
        val.pool_verifie = round(part_verifiee, 2)
        val.iqr_ratio = round(iqr_ratio, 3)
        val.flou_moyen = round(flou_moyen, 2)
        val.rejets_flous = rejets_flous
        val.comparables = [
            {"price_eur": int(c["price_eur"]), "year": c.get("year"),
             "mileage_km": c.get("mileage_km"), "vkey": c.get("vkey"),
             "seller_type": c.get("seller_type"), "flous": c.get("_flous", 0)}
            for c in sorted(comps, key=lambda x: x["price_eur"])[:40]
        ]
        return val

    return Valuation()


# ═══════════════════════════════════════════════════════════
# 4. REPAIR / RISK / RESALE / URGENCY
# ═══════════════════════════════════════════════════════════

def estimate_repairs(defects: list[DefectHit]) -> dict:
    active = [d for d in defects if not d.negated and d.category != "modifier"]
    lo = sum(d.pro_cost[0] for d in active)
    hi = sum(d.pro_cost[1] for d in active)
    mkt_lo = sum(d.market_discount[0] for d in active)
    mkt_hi = sum(d.market_discount[1] for d in active)
    margin = int(hi * 0.15) + (300 if active else 0)
    conf = min([d.confidence for d in active], default=1.0)
    return {
        "pro_low": lo, "pro_high": hi + margin,
        "market_discount_low": mkt_lo, "market_discount_high": mkt_hi,
        "safety_margin": margin, "confidence": conf,
        "items": [(d.code, d.pro_cost, d.market_discount) for d in active],
        "checklist": [c for d in active for c in d.checklist],
    }


NEGO_MOTS = ("a discuter", "à discuter", "negociable", "négociable",
             "faire offre", "prix a debattre", "bieden", "onderhandelbaar",
             "prijs bespreekbaar", "vertrek", "snel weg", "moet weg",
             "doit partir", "urgent", "demenagement", "demenage")


def estimate_negotiation(listing: dict, defects: list[DefectHit],
                         age_days: float, drops: int) -> dict:
    """Estime la remise obtenable au telephone.

    ⚠ LES TAUX CI-DESSOUS SONT DES HYPOTHESES DE TRAVAIL, PAS DES MESURES.

    Ils n'ont jamais ete confrontes a un prix de transaction reel : le
    systeme n'observe que des prix DEMANDES. Une baisse affichee sur le
    site n'est pas une remise obtenue au telephone. Tant que les prix
    reellement negocies ne sont pas saisis (bouton "Acheté" du feedback),
    ces valeurs restent des parametres de reglage.

    Consequence appliquee dans compute_deal : une marge qui n'existe que
    grace a cette hypothese ne peut pas produire une alerte de haut rang.
    """
    taux = 0.05
    raisons = []

    actifs = [d for d in defects if not d.negated and d.category != "modifier"]
    if actifs:
        taux += 0.08
        raisons.append("défaut déclaré")
    if any(d.code == "as_is" for d in defects):
        taux += 0.05
        raisons.append("vendu en l'état")

    if age_days > 45:
        taux += 0.09
        raisons.append(f"en ligne depuis {age_days:.0f} j")
    elif age_days > 25:
        taux += 0.06
        raisons.append(f"en ligne depuis {age_days:.0f} j")
    elif age_days > 12:
        taux += 0.03

    if drops >= 2:
        taux += 0.06
        raisons.append(f"{drops} baisses déjà consenties")
    elif drops == 1:
        taux += 0.03

    txt = norm_text((listing.get("title") or "") + " " +
                    (listing.get("description") or ""))
    if any(m in txt for m in NEGO_MOTS):
        taux += 0.07
        raisons.append("vendeur ouvert à la négociation")

    km = listing.get("mileage_km") or 0
    if km > 220000:
        taux += 0.04
        raisons.append("kilométrage élevé")

    taux = min(taux, 0.28)
    prix = listing.get("price_eur") or 0
    return {
        "taux": round(taux, 3),
        "prix_negocie": int(round(prix * (1 - taux))),
        "remise": int(round(prix * taux)),
        "raisons": raisons,
        "hypothese": True,          # jamais valide sur des prix de transaction
        "base": "taux heuristiques v1 — a recalibrer avec tes prix reels",
    }


# Defauts dont le cout de remise en etat n'est PAS chiffrable depuis le
# texte d'une annonce. Un choc peut etre un pare-choc a 300 EUR comme un
# chassis au marbre a 6 000 EUR : aucune estimation honnete n'est possible.
NON_CHIFFRABLES = {"accident", "corrosion", "for_parts", "engine",
                   "unspecified"}


def score_confidence(listing: dict, vehicle: "Vehicle", defects: list[DefectHit],
                     val: Valuation, rep: dict,
                     drops: int = 0) -> tuple[float, list[str]]:
    """Fiabilite REELLE de l'estimation, avec le detail de ce qui la limite.

    L'ancienne version ne mesurait que la qualite de l'echantillon de
    marche : un marche parfaitement echantillonne + une annonce mal comprise
    donnait 82 % de confiance sur une epave. La confiance doit repondre a
    "ai-je compris cette annonce ?", pas seulement "ai-je assez de
    comparables ?".
    """
    raisons: list[str] = []
    conf = val.confidence

    if not conf:
        return 0.0, ["pas de marché de référence exploitable"]

    # ── 1. identification du vehicule (plus de plancher artificiel) ──
    # L'ancien max(vehicle.confidence, 0.5) relevait a 50 % la confiance
    # d'un vehicule non identifie.
    conf *= vehicle.confidence
    if vehicle.confidence < 0.7:
        raisons.append(f"véhicule identifié à {vehicle.confidence:.0%} seulement")
    if not vehicle.fuel:
        conf *= 0.85
        raisons.append("carburant inconnu")
    if not listing.get("year"):
        conf *= 0.75
        raisons.append("année inconnue")
    if not listing.get("mileage_km"):
        conf *= 0.75
        raisons.append("kilométrage inconnu")

    # ── 2. certitude sur les defauts ──
    # Effet AMORTI : la fiabilite du marche de reference ne depend pas de la
    # certitude sur le defaut. Un defaut mal cerne coute au plus 25 % de
    # confiance, il ne divise pas l'estimation par deux.
    conf *= 0.75 + 0.25 * rep["confidence"]
    actifs = [d for d in defects if not d.negated and d.category != "modifier"]
    deduits = [d for d in actifs if d.evidence == "component+marker"]
    if deduits:
        raisons.append("défaut déduit du contexte, non affirmé : "
                       + ", ".join(d.code for d in deduits))

    # ── 3. qualite du pool ──
    if val.n < 12:
        raisons.append(f"seulement {val.n} comparables")
    if val.iqr_ratio > 0.35:
        raisons.append(f"comparables hétérogènes (dispersion {val.iqr_ratio:.0%})")
    if val.pool_verifie < 0.5:
        raisons.append(f"{1 - val.pool_verifie:.0%} du marche de reference "
                       "n'a jamais été contrôlé pour défauts")
    if val.method.endswith("elargi"):
        raisons.append("estimation obtenue par élargissement année/kilométrage")

    # ── 4. DECOTE INEXPLIQUEE — le garde-fou central ──
    # Une annonce tres en dessous du marche n'est une affaire que si les
    # defauts detectes expliquent l'ecart. Sinon, l'annonce dit quelque
    # chose que le moteur n'a pas compris : c'est le cas de l'Aygo
    # "schadewagen" a 2 500 EUR pour un marche a 18 490 EUR.
    ref = val.p50 or val.pmin
    prix = listing.get("price_eur")
    inexplique = 0.0
    if ref and prix:
        reelle = (ref - prix) / ref
        # Ce qui explique legitimement un prix bas :
        #   a) la decote que le marche applique aux defauts detectes ;
        #   b) la dispersion naturelle du marche — se caler sur la moins
        #      chere du site (pmin) plutot que sur la mediane n'a rien
        #      d'anormal, c'est meme le principe du systeme.
        #   c) les baisses de prix REELLEMENT observees : quand on a vu le
        #      vendeur descendre palier par palier, le prix bas est constate,
        #      pas mysterieux. C'est l'inverse d'une annonce affichee d'emblee
        #      a 2 500 EUR sans que rien ne l'explique.
        dispersion = max(0, ref - (val.pmin or ref))
        initial = listing.get("prix_initial")
        baisse = max(0, initial - prix) if initial and initial > prix else 0
        if not baisse and drops:
            baisse = min(drops * 0.04, 0.20) * ref
        expliquee = min(1.0, (rep["market_discount_high"] + dispersion + baisse) / ref)
        inexplique = reelle - expliquee
        if inexplique > 0.45:
            conf *= 0.25
            raisons.append(f"décote de {reelle:.0%} inexpliquée par les défauts "
                           f"détectés — l'annonce cache probablement autre chose")
        elif inexplique > 0.32:
            conf *= 0.55
            raisons.append(f"décote de {reelle:.0%} mal expliquée par les "
                           f"défauts détectés")
        elif inexplique > 0.22:
            conf *= 0.80
            raisons.append(f"décote de {reelle:.0%} partiellement inexpliquée")

    # ── 5. defauts non chiffrables ──
    bloquants = [d.code for d in actifs if d.code in NON_CHIFFRABLES]
    if bloquants:
        conf = min(conf, 0.45)
        raisons.append("coût de remise en état non chiffrable depuis l'annonce : "
                       + ", ".join(bloquants))

    return round(max(0.0, min(1.0, conf)), 2), raisons


def score_risk(listing: dict, defects: list[DefectHit], val: Valuation) -> float:
    risk = 100.0
    active = [d for d in defects if not d.negated]

    for d in active:
        risk -= d.risk_penalty
        if d.category == "major":
            risk -= 12
        elif d.category == "mechanical":
            risk -= 6
        if d.confidence < 0.65:      # défaut mal cerné
            risk -= 8

    desc = listing.get("description") or ""
    if len(desc) < 120:
        risk -= 15
    if (listing.get("photo_count") or 0) < 4:
        risk -= 12
    if not listing.get("mileage_km") or not listing.get("year"):
        risk -= 10
    if listing.get("year") and listing["year"] < 2011:
        risk -= 8

    # Signal d'arnaque : trop beau, sur une voiture SANS défaut déclaré
    if val.p50 and listing.get("price_eur") and not active:
        ratio = listing["price_eur"] / val.p50
        if ratio < 0.45:
            risk -= 40
        elif ratio < 0.60:
            risk -= 18

    if re.search(r"\b(transport|livraison|envoi|paypal|western union)\b",
                 norm_text(desc)):
        risk -= 25

    if len(desc) > 400:
        risk += 5
    if (listing.get("photo_count") or 0) >= 10:
        risk += 5

    return round(max(0.0, min(100.0, risk)), 1)


def score_resale(val: Valuation, pool_size: int, vehicle: Vehicle) -> float:
    s = 55.0
    if pool_size >= 40:
        s += 18          # modèle très présent = liquide
    elif pool_size >= 15:
        s += 10
    elif pool_size < 6:
        s -= 12
    if vehicle.transmission == "automatique":
        s += 6
    if vehicle.fuel in ("essence", "hybride"):
        s += 5
    if val.confidence >= 0.8:
        s += 6
    return round(max(0.0, min(100.0, s)), 1)


def score_urgency(deal_type: str, age_days: float, drops: int,
                  last_drop_days: float | None) -> float:
    if deal_type == "A":
        # saine sous-évaluée : part vite
        return round(max(10.0, 100 - age_days * 24 * 60 / 60 * 2), 1) if age_days < 2 \
            else 15.0
    # TYPE B : l'urgence MONTE avec l'âge et les baisses.
    # Base neutre : "rien ne presse" ne doit pas valoir "mauvaise affaire".
    u = 55.0
    if age_days > 30:
        u += 25
    elif age_days > 14:
        u += 12
    if drops >= 2:
        u += 20
    elif drops == 1:
        u += 8
    if last_drop_days is not None and last_drop_days <= 7:
        u += 15
    return round(min(100.0, u), 1)


# ═══════════════════════════════════════════════════════════
# 5. DEAL ENGINE
# ═══════════════════════════════════════════════════════════

# Une urgence faible sur un TYPE B signifie "rien ne presse", pas "mauvaise
# affaire". Son poids est donc volontairement bas : elle sert à faire remonter
# une annonce ancienne qui baisse, jamais à en écarter une.
WEIGHTS = {
    "margin_pct": 0.32, "tdv_eur": 0.22, "confidence": 0.15,
    "resale": 0.11, "risk": 0.13, "urgency": 0.07,
}
WEIGHTS_VERSION = "v1.1"


def _norm(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return max(0.0, min(100.0, (x - lo) / (hi - lo) * 100))


def tiers_max_sans_nego(profile: dict) -> float:
    """Plafond applique quand la marge repose sur la remise supposee.

    On autorise l'alerte — c'est bien le metier : on appelle pour negocier —
    mais jamais au-dessus du premier palier, tant que rien n'est obtenu.
    """
    return float(profile["tiers"]["great"]["min"]) - 0.1


def segment_for(price: int, profile: dict) -> dict:
    for s in profile["segments"]:
        if s["price_from"] <= price <= s["price_to"]:
            return s
    return profile["segments"][-1]


def compute_deal(listing: dict, vehicle: Vehicle, defects: list[DefectHit],
                 val: Valuation, pool_size: int, age_days: float,
                 drops: int, last_drop_days: float | None,
                 profile: dict) -> dict:
    price = listing["price_eur"]
    # Reference : pmin = la moins chere du site. C'est le vrai concurrent.
    ref_key = profile["profile"].get("market_reference", "pmin")
    rep = estimate_repairs(defects)
    active = [d for d in defects if not d.negated and d.category != "modifier"]
    deal_type = "B" if active else "A"

    # Ce qui compte n'est pas le prix affiche mais celui obtenu au telephone.
    nego = estimate_negotiation(listing, defects, age_days, drops)
    prix_cible = nego["prix_negocie"]

    true_low = prix_cible + rep["pro_low"]
    true_high = prix_cible + rep["pro_high"]
    # Marge SANS aucune hypothese de negociation : ce qui reste si le
    # vendeur ne lache pas un euro.
    true_high_affiche = price + rep["pro_high"]

    ref = getattr(val, ref_key, None) or val.p50
    if not ref:
        return {
            "deal_score": 0, "tier": "below", "deal_type": deal_type,
            "reason": "données insuffisantes — pas assez de comparables",
            "negociation": nego,
            "valuation": val, "repairs": rep,
            "true_cost_low": true_low, "true_cost_high": true_high,
            "true_deal_value": None, "margin_pct": None,
            "risk": 0, "resale": 0, "urgency": 0, "confidence": 0,
            "confidence_limites": ["pas assez de comparables fiables"],
            "explanation": [], "checklist": rep["checklist"],
        }

    tdv = ref - true_high
    margin_pct = tdv / ref * 100
    # Part de la marge qui repose uniquement sur l'hypothese de negociation.
    tdv_affiche = ref - true_high_affiche
    marge_hypothetique = tdv_affiche <= 0 < tdv
    part_hypothese = (nego["remise"] / tdv) if tdv > 0 else 0.0

    risk = score_risk(listing, defects, val)
    resale = score_resale(val, pool_size, vehicle)
    urgency = score_urgency(deal_type, age_days, drops, last_drop_days)
    confidence, limites = score_confidence(listing, vehicle, defects, val, rep, drops)

    raw = (
        WEIGHTS["margin_pct"] * _norm(margin_pct, 3, 28)
        + WEIGHTS["tdv_eur"] * _norm(tdv, 300, 5000)
        + WEIGHTS["confidence"] * confidence * 100
        + WEIGHTS["resale"] * resale
        + WEIGHTS["risk"] * risk
        + WEIGHTS["urgency"] * urgency
    )

    # ── GARDE-FOUS ──────────────────────────────────────────────
    # Chaque plafond est trace : une alerte retenue doit pouvoir etre
    # expliquee, une alerte bloquee aussi.
    seg = segment_for(price, profile)
    plafonds: list[str] = []
    # Un cran sous le seuil de notification REEL. `notification_threshold`
    # etait declare dans profile.yaml mais aucun code ne le lisait : le vrai
    # seuil etait tiers.good.min (75). Il pilote desormais l'envoi.
    seuil = float(profile.get("notification_threshold", 75))
    PLAFOND_BLOQUANT = seuil - 1

    conf_min = seg.get("min_confidence", 0.50)
    if confidence < conf_min:
        raw = min(raw, PLAFOND_BLOQUANT)
        plafonds.append(f"confiance {confidence:.0%} < {conf_min:.0%} exiges "
                        f"sur le segment {seg['name']}")

    if tdv < seg["min_margin_eur"] or margin_pct < seg["min_margin_pct"]:
        raw = min(raw, PLAFOND_BLOQUANT)
        plafonds.append(f"marge {int(tdv)} EUR / {margin_pct:.0f} % sous le "
                        f"minimum du segment {seg['name']} "
                        f"({seg['min_margin_eur']} EUR / {seg['min_margin_pct']} %)")

    # Le risque a desormais un veto : il ne pesait que 13 % du score et ne
    # pouvait pas bloquer une annonce manifestement suspecte.
    risque_max = seg.get("max_risk_penalty")
    if risque_max is not None and risk < (100 - risque_max):
        raw = min(raw, PLAFOND_BLOQUANT)
        plafonds.append(f"risque trop eleve (score {risk:.0f}, plancher "
                        f"{100 - risque_max})")

    # Une marge qui n'existe QUE grace a l'hypothese de negociation ne peut
    # pas produire une alerte de haut rang : le vendeur n'a encore rien
    # lache, et ces taux n'ont jamais ete valides sur des ventes reelles.
    if marge_hypothetique:
        raw = min(raw, tiers_max_sans_nego(profile))
        plafonds.append("marge inexistante au prix affiche — elle repose "
                        "entierement sur la remise supposee")
    elif part_hypothese > 0.5:
        raw = min(raw, tiers_max_sans_nego(profile))
        plafonds.append(f"{part_hypothese:.0%} de la marge vient de la remise "
                        f"supposee, pas du prix affiche")

    # Voiture annoncee pour pieces : jamais une opportunite de revente.
    if any(d.code == "for_parts" and not d.negated for d in defects):
        raw = min(raw, PLAFOND_BLOQUANT)
        plafonds.append("vehicule annonce pour pieces")

    score = round(max(0.0, min(100.0, raw)), 1)
    tiers = profile["tiers"]
    if score >= tiers["sniper"]["min"]:
        tier = "sniper"
    elif score >= tiers["great"]["min"]:
        tier = "great"
    elif score >= tiers["good"]["min"]:
        tier = "good"
    elif score >= seuil:
        # Bande entre le seuil de notification et le premier palier : ca vaut
        # un coup d'oeil, pas un deplacement.
        tier = "watch"
    else:
        tier = "below"

    # ── WHY_THIS_DEAL() ──
    expl = []
    ecart_aff = (ref - price) / ref * 100
    ecart_neg = (ref - prix_cible) / ref * 100
    expl.append(f"Moins chère du marché : {ref} € ({val.n} comparables)")
    if ecart_aff < 0 <= ecart_neg:
        expl.append(f"Affichée {abs(ecart_aff):.0f} % AU-DESSUS, mais "
                    f"négociable à ~{prix_cible} € soit {ecart_neg:.0f} % en dessous")
    else:
        expl.append(f"Affichée {price} €, cible de négociation ~{prix_cible} € "
                    f"({ecart_neg:.0f} % sous le plancher)")
    if nego["raisons"]:
        expl.append("Levier : " + ", ".join(nego["raisons"][:3]))
    if active:
        gap_lo = rep["market_discount_low"] - rep["pro_high"]
        names = ", ".join(d.code for d in active)
        expl.append(f"Défaut(s) : {names}")
        expl.append(f"Coût garage {rep['market_discount_low']}–{rep['market_discount_high']} € "
                    f"vs ton coût {rep['pro_low']}–{rep['pro_high']} €")
        if gap_lo > 0:
            expl.append(f"Écart de compétence : ~{gap_lo} € en ta faveur")
    else:
        expl.append("Aucun défaut déclaré — vérifier pourquoi le prix est bas")
    if drops >= 2:
        expl.append(f"{drops} baisses de prix en {age_days:.0f} j — vendeur mûr")
    if risk < 60:
        expl.append("⚠️ Risque élevé — informations insuffisantes ou signaux suspects")

    return {
        "deal_score": score, "tier": tier, "deal_type": deal_type,
        "valuation": val, "repairs": rep,
        "true_cost_low": true_low, "true_cost_high": true_high,
        "true_deal_value": int(tdv), "margin_pct": round(margin_pct, 1),
        "risk": risk, "resale": resale, "urgency": urgency,
        "reference": ref, "reference_key": ref_key,
        "negociation": nego, "prix_negocie": prix_cible,
        "listing_price": price,
        "defauts_detail": [
            {"code": d.code, "negated": d.negated, "evidence": d.evidence,
             "matched": d.matched, "trigger": d.trigger,
             "confidence": d.confidence,
             "pro_cost": list(d.pro_cost),
             "market_discount": list(d.market_discount)}
            for d in defects
        ],
        "confidence": confidence, "confidence_limites": limites,
        "plafonds": plafonds,
        "marge_affichee": int(tdv_affiche),
        "part_hypothese": round(part_hypothese, 2),
        "explanation": expl,
        "checklist": rep["checklist"], "weights_version": WEIGHTS_VERSION,
    }
