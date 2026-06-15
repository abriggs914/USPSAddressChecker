# rating_engine.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
import urllib.parse
import math
import re

import streamlit as st


ViewportAge = Literal["FRESH", "STALE"]
LocationBasis = Literal["EXPLICIT_QUERY", "USER", "VIEWPORT", "TEST_LOCALE"]

RelevanceLabel = Literal["Navigational", "Excellent", "Good", "Acceptable", "Bad"]
NameRating = Literal["Correct", "Partially Correct", "Incorrect", "Can't Verify", "n/a"]
AddressRating = Literal["Correct", "Correct with Formatting Issue", "Incorrect", "Can't Verify", "n/a"]
PinRating = Literal["Perfect", "Approximate", "Next Door", "Wrong", "Can't Verify", "n/a"]

IntentType = Literal[
    "NO_MAPS_INTENT",
    "ADDRESS",
    "POI_OR_BUSINESS",
    "CATEGORY",
    "PRODUCT_SERVICE",
    "LOCALITY",
    "TRANSIT",
    "COORDINATE",
    "EMOJI",
]

ClosedStatus = Literal["OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"]


@dataclass
class QueryContext:
    query: str
    viewport_age: ViewportAge
    locale: str
    country: str
    user_lat: Optional[float]
    user_lon: Optional[float]
    viewport_lat: Optional[float] = None
    viewport_lon: Optional[float] = None
    user_inside_viewport: Optional[bool] = None


@dataclass
class ResultInput:
    name: str
    address: str
    classification: str
    result_type: str
    status: ClosedStatus
    distance_to_user_km: Optional[float]
    distance_to_viewport_km: Optional[float]
    lat: Optional[float]
    lon: Optional[float]

    official_name: str = ""
    official_address: str = ""

    usps_valid: Optional[bool] = None
    usps_exists: Optional[bool] = None
    usps_match_status: str = ""
    usps_match_notes: list[str] = field(default_factory=list)

    pin_verified: bool = False
    pin_same_property: Optional[bool] = None
    pin_same_block: Optional[bool] = None
    pin_adjacent_property: Optional[bool] = None
    pin_precise: Optional[bool] = None
    pin_boundary_identifiable: Optional[bool] = None


@dataclass
class QueryIntent:
    intent_type: IntentType
    raw_query: str
    explicit_location: Optional[str]
    has_near_me: bool
    is_chain: bool
    probably_unique: bool


@dataclass
class RatingResult:
    has_navigational_result: bool
    unexpected_language_or_script: bool
    business_closed_or_dne: bool

    relevance: RelevanceLabel
    relevance_notes: list[str]
    demotion_reasons: list[str]

    name_rating: NameRating
    address_rating: AddressRating
    address_issues: list[str]
    pin_rating: PinRating

    comment: str


# CHAIN_HINTS = {
#     "starbucks", "mcdonalds", "mcdonald's", "subway", "walmart", "costco",
#     "target", "shell", "burger king", "wendy's", "tim hortons", "dollarama"
# }

# CATEGORY_HINTS = {
#     "zoo", "mall", "shopping center", "shopping centre", "hospital", "bank",
#     "hotel", "gas station", "pharmacy", "park", "airport", "school",
#     "wildlife park", "museum", "restaurant", "library"
# }

CHAIN_LOCATORS = {
    # Fast food
    "mcdonald's": "https://www.mcdonalds.com/us/en-us/restaurant-locator.html",
    "mcdonalds":  "https://www.mcdonalds.com/us/en-us/restaurant-locator.html",
    "burger king":"https://www.burgerking.com/store-locator",
    "kfc":        "https://www.kfc.com/find-a-kfc",
    "taco bell":  "https://www.tacobell.com/find-a-taco-bell",
    "wendy's":    "https://www.wendys.com/restaurant-locator",
    "wendys":     "https://www.wendys.com/restaurant-locator",
    "subway":     "https://www.subway.com/en-US/FindASubway",
    "chick-fil-a":"https://www.chick-fil-a.com/locations",
    "chickfila":  "https://www.chick-fil-a.com/locations",
    "chick fil a":"https://www.chick-fil-a.com/locations",
    "whataburger":"https://whataburger.com/locations",
    "popeyes":    "https://www.popeyes.com/store-locator",
    "five guys":  "https://www.fiveguys.com/locations",
    "in-n-out":   "https://www.in-n-out.com/locations",
    "in n out":   "https://www.in-n-out.com/locations",
    "sonic":      "https://www.sonicdrivein.com/locations",
    "dairy queen":"https://www.dairyqueen.com/en-us/locator/",
    "jack in the box": "https://www.jackinthebox.com/locations",
    "hardee's":   "https://www.hardees.com/locations",
    "hardees":    "https://www.hardees.com/locations",
    "carl's jr":  "https://www.carlsjr.com/locations",
    "carls jr":   "https://www.carlsjr.com/locations",
    "arbys":      "https://arbys.com/locations",
    "arby's":     "https://arbys.com/locations",
    "panera":     "https://www.panerabread.com/en-us/cafe-locator.html",
    "panera bread":"https://www.panerabread.com/en-us/cafe-locator.html",
    "chipotle":   "https://www.chipotle.com/order",
    "domino's":   "https://www.dominos.com/en/pages/locator/",
    "dominos":    "https://www.dominos.com/en/pages/locator/",
    "pizza hut":  "https://www.pizzahut.com/locator",
    "papa john's":"https://www.papajohns.com/order/store-finder",
    "papa johns": "https://www.papajohns.com/order/store-finder",
    "little caesars": "https://littlecaesars.com/en-us/store-locator/",
    "dunkin":     "https://www.dunkindonuts.com/en/locations",
    "dunkin donuts": "https://www.dunkindonuts.com/en/locations",
    "starbucks":  "https://www.starbucks.com/store-locator",
    "tim hortons":"https://www.timhortons.com/store-locator",
    "panda express": "https://www.pandaexpress.com/locations",
    "raising cane's": "https://www.raisingcanes.com/locations",
    "wingstop":   "https://www.wingstop.com/order",
    "freddy's":   "https://www.freddysusa.com/locations/",
    "freddys":    "https://www.freddysusa.com/locations/",

    # Retail
    "walmart":    "https://www.walmart.com/store/finder",
    "target":     "https://www.target.com/store-locator/find-stores",
    "costco":     "https://www.costco.com/warehouse-locations",
    "home depot": "https://www.homedepot.com/l/storelocator",
    "lowe's":     "https://www.lowes.com/store",
    "lowes":      "https://www.lowes.com/store",
    "best buy":   "https://www.bestbuy.com/site/store-locator/store-finder",
    "walgreens":  "https://www.walgreens.com/storelocator/find.jsp",
    "cvs":        "https://www.cvs.com/store-locator/landing",
    "rite aid":   "https://www.riteaid.com/locations",
    "dollar tree":"https://www.dollartree.com/locations/index",
    "dollar general": "https://www.dollargeneral.com/store-directory",
    "family dollar": "https://stores.familydollar.com/",
    "tj maxx":    "https://tjmaxx.tjx.com/store-locator",
    "marshalls":  "https://www.marshalls.com/us/store/index.jsp",
    "ross":       "https://www.rossstores.com/store-finder",
    "whole foods":"https://www.wholefoodsmarket.com/stores",
    "trader joe's": "https://www.traderjoes.com/home/stores",
    "trader joes":"https://www.traderjoes.com/home/stores",
    "aldi":       "https://stores.aldi.us/",
    "kroger":     "https://www.kroger.com/stores/search",
    "safeway":    "https://www.safeway.com/stores/grocery-stores-near-me.html",
    "publix":     "https://www.publix.com/locations",
    "meijer":     "https://www.meijer.com/shopping/store-locator.html",
    "sam's club": "https://www.samsclub.com/club-finder",

    # Fuel / Convenience
    "shell":      "https://www.shell.com/motorists/shell-station-locator.html",
    "chevron":    "https://www.chevronwithtechron.com/en_us/home/find-a-station.html",
    "bp":         "https://www.bp.com/en_us/united-states/home/find-a-gas-station.html",
    "exxon":      "https://www.exxon.com/en/find-station",
    "mobil":      "https://www.mobil.com/en/find-station",
    "7-eleven":   "https://www.7-eleven.com/en/store-locator",
    "7 eleven":   "https://www.7-eleven.com/en/store-locator",
    "circle k":   "https://www.circlek.com/find-a-store",
    "speedway":   "https://www.speedway.com/storelocator",

    # Hotels
    "marriott":   "https://www.marriott.com/find-hotels/findHotels.mi",
    "hilton":     "https://www.hilton.com/en/locations/",
    "holiday inn":"https://www.ihg.com/holidayinn/hotels/us/en/find-hotels/hotel/list",
    "hampton inn":"https://www.hilton.com/en/hampton/",
    "hyatt":      "https://www.hyatt.com/find-a-hotel",
    "best western": "https://www.bestwestern.com/en_US/find-a-hotel.html",
    "motel 6":    "https://www.motel6.com/en/home/find-a-motel.html",

    # Banks
    "chase":      "https://locator.chase.com/",
    "bank of america": "https://www.bankofamerica.com/banking-centers-atms/",
    "wells fargo":"https://www.wellsfargo.com/locator/",
    "citibank":   "https://online.citi.com/US/JRS/portal/template.do?ID=ATMBranchLocator",
    "td bank":    "https://www.td.com/us/en/personal-banking/locations/",
    "us bank":    "https://www.usbank.com/bank-accounts/locations.html",

    # Others
    "ups store":  "https://www.theupsstore.com/tools/find-a-store",
    "fedex":      "https://local.fedex.com/",
    "usps":       "https://tools.usps.com/find-location.htm",
    "planet fitness": "https://www.planetfitness.com/gyms",
    "la fitness": "https://www.lafitness.com/pages/clublocator.aspx",
    "anytime fitness": "https://www.anytimefitness.com/gyms/",
    "autozone":   "https://www.autozone.com/locations",
    "o'reilly":   "https://www.oreillyauto.com/store-locator",
    "oreilly":    "https://www.oreillyauto.com/store-locator",
    "advance auto parts": "https://shop.advanceautoparts.com/o/store-locator",
    "jiffy lube": "https://www.jiffylube.com/locations",
    "valvoline":  "https://www.vioc.com/locations",

    # Transit / Transport
    "amtrak":     "https://www.amtrak.com/find-a-station",
    "greyhound":  "https://www.greyhound.com/en/locations",
}

CLASSIFICATION_KEYWORDS = {
    "pizza":        ["pizza", "italian", "pasta"],
    "burger":       ["burger", "fast food", "american food"],
    "mexican":      ["mexican", "taco", "burrito", "tex-mex"],
    "chinese":      ["chinese", "asian", "dim sum"],
    "gas station":  ["gas", "fuel", "petrol", "station", "shell", "chevron", "bp", "exxon"],
    "grocery":      ["grocery", "supermarket", "food store", "market"],
    "pharmacy":     ["pharmacy", "drug store", "walgreens", "cvs", "rite aid"],
    "hotel":        ["hotel", "motel", "inn", "lodging", "marriott", "hilton"],
    "bank":         ["bank", "atm", "financial", "chase", "wells fargo"],
    "airport":      ["airport", "terminal", "aviation", "airfield"],
    "mall":         ["mall", "shopping center", "plaza", "outlet"],
    "hospital":     ["hospital", "medical center", "health", "clinic"],
    "transit":      ["station", "transit", "subway", "metro", "bus terminal", "train"],
}

TRANSIT_HINTS = {"station", "airport", "terminal", "metro", "subway", "train", "bus"}
NO_MAPS_TERMS = {"weather", "time", "facebook", "instagram", "youtube", "netflix"}

CATEGORY_CONTAINER_TERMS = {
    "mall", "shopping center", "shopping centre", "airport", "terminal",
    "park", "complex", "center", "centre", "hospital", "campus"
}

def detect_classification_issue(query: str, classification: str) -> str | None:
    """Return warning string if classification seems inconsistent with query."""
    q_lower = query.lower()
    c_lower = classification.lower()
    for cat, keywords in CLASSIFICATION_KEYWORDS.items():
        # Does classification match a category?
        if any(k in c_lower for k in keywords):
            # Does the query strongly imply a different category?
            for other_cat, other_kw in CLASSIFICATION_KEYWORDS.items():
                if other_cat != cat and any(k in q_lower for k in other_kw):
                    return f"Query suggests **{other_cat}** but classification is **{cat}** — possible mismatch (Section 6.3.2)"
    return None

def get_chain_locator(query: str) -> tuple[str | None, bool]:
    """Return (url, found) for the query chain."""
    q = query.lower().strip()
    # Try exact match first
    if q in CHAIN_LOCATORS:
        return CHAIN_LOCATORS[q], True
    # Try substring match
    for key, url in CHAIN_LOCATORS.items():
        if key in q or q in key:
            return url, True
    # Build a Google search fallback
    encoded = urllib.parse.quote(f"{query} store locator official site")
    return f"https://www.google.com/search?q={encoded}", False

def google_maps_link(lat: float, lon: float, label: str = "") -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def google_maps_address_link(address: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_key(s: str) -> str:
    s = normalize_ws(s).lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w\s]", "", s)
    return normalize_ws(s)


# def classify_query(query: str, class_in: str) -> QueryIntent:
#     q = normalize_ws(query)
#     ql = q.lower()

#     if not q:
#         return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

#     if ql in NO_MAPS_TERMS:
#         return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

#     if re.fullmatch(r"-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?", q):
#         return QueryIntent("COORDINATE", q, None, False, False, True)

#     has_near_me = any(tok in ql for tok in ("near me", "nearby", "nearest", "closest"))
#     explicit_location = None

#     m = re.search(r"\b(?:in|at|near|around|within)\s+(.+)$", ql)
#     if m and not has_near_me:
#         explicit_location = m.group(1).strip()

#     # is_chain = any(chain in ql for chain in CHAIN_HINTS)
#     locator_url, is_chain = get_chain_locator(query)
#     st.write(f"Query: {query}")
#     st.link_button(locator_url, locator_url)
#     st.write(f"{is_chain=}")

#     if re.search(r"\b\d+\s+[a-z]", ql):
#         return QueryIntent("ADDRESS", q, explicit_location, has_near_me, is_chain, True)

#     if any(tok in ql for tok in TRANSIT_HINTS):
#         return QueryIntent("TRANSIT", q, explicit_location, has_near_me, is_chain, True)

#     # if any(tok in ql for tok in CATEGORY_HINTS):
#     issue = detect_classification_issue(q, class_in)
#     st.write("issue")
#     st.write(issue)
#     if issue:
#         st.toast("--B HERE")
#         return QueryIntent("CATEGORY", q, explicit_location, has_near_me, is_chain, False)

#     if is_chain:
#         probably_unique = explicit_location is not None and not has_near_me
#         return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, True, probably_unique)

#     if re.fullmatch(r"[A-Za-z .'-]+", q):
#         # broad fallback for localities/simple named places
#         return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, False, False)

#     return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, False, False)


def classify_query(query: str, class_in: str) -> QueryIntent:
    q = normalize_ws(query)
    ql = q.lower()

    if not q:
        return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

    if ql in NO_MAPS_TERMS:
        return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

    if re.fullmatch(r"-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?", q):
        return QueryIntent("COORDINATE", q, None, False, False, True)

    has_near_me = any(tok in ql for tok in ("near me", "nearby", "nearest", "closest"))
    explicit_location = None

    m = re.search(r"\b(?:in|at|near|around|within)\s+(.+)$", ql)
    if m and not has_near_me:
        explicit_location = m.group(1).strip()

    locator_url, is_chain = get_chain_locator(query)

    if re.search(r"\b\d+\s+[a-z]", ql):
        return QueryIntent("ADDRESS", q, explicit_location, has_near_me, is_chain, True)

    if any(tok in ql for tok in TRANSIT_HINTS):
        return QueryIntent("TRANSIT", q, explicit_location, has_near_me, is_chain, True)

    issue = detect_classification_issue(q, class_in)
    if issue:
        return QueryIntent("CATEGORY", q, explicit_location, has_near_me, is_chain, False)

    if is_chain:
        probably_unique = explicit_location is not None and not has_near_me
        return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, True, probably_unique)

    if re.fullmatch(r"[A-Za-z .'-]+", q):
        return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, False, False)

    return QueryIntent("POI_OR_BUSINESS", q, explicit_location, has_near_me, False, False)


def determine_location_basis(ctx: QueryContext, qi: QueryIntent) -> LocationBasis:
    if qi.explicit_location:
        return "EXPLICIT_QUERY"
    if ctx.viewport_age == "STALE":
        return "USER" if ctx.user_lat is not None and ctx.user_lon is not None else "TEST_LOCALE"
    if ctx.user_inside_viewport is True:
        return "USER"
    if ctx.user_inside_viewport is False:
        return "VIEWPORT"
    return "USER" if ctx.user_lat is not None and ctx.user_lon is not None else "TEST_LOCALE"


def is_unexpected_language_or_script(query: str, result_name: str, locale: str, country: str) -> bool:
    # Keep conservative. Only hard-flag obvious non-Latin script for en_US use-case.
    if locale != "en_US":
        return False
    s = result_name or ""
    has_non_latin = bool(re.search(r"[\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF]", s))
    return has_non_latin


def has_navigational_result(qi: QueryIntent, results: list[ResultInput]) -> bool:
    if qi.intent_type == "NO_MAPS_INTENT":
        return False

    if qi.intent_type == "ADDRESS":
        return any(r.usps_exists is True for r in results)

    if qi.is_chain and not qi.probably_unique:
        return False

    qk = normalize_key(qi.raw_query)
    exact = [r for r in results if normalize_key(r.name) == qk]
    if exact:
        return True

    fuzzy = [r for r in results if qk and qk in normalize_key(r.name)]
    return len(fuzzy) == 1 and qi.probably_unique


def _base_relevance_for_connection(is_nav_query: bool, strength: str) -> RelevanceLabel:
    if strength == "PRIMARY":
        return "Navigational" if is_nav_query else "Excellent"
    if strength == "SECONDARY":
        return "Good"
    if strength == "UNLIKELY":
        return "Acceptable"
    return "Bad"


def _connection_strength(qi: QueryIntent, result: ResultInput) -> str:
    qk = normalize_key(qi.raw_query)
    rn = normalize_key(result.name)
    rc = normalize_key(result.classification)
    ra = normalize_key(result.address)
    
    st.write(f"_connection_strength")
    st.write(f"{qi=}")
    st.write(f"{result=}")
    st.write(f"{qk=}")
    st.write(f"{rn=}")
    st.write(f"{rc=}")
    st.write(f"{ra=}")

    if qi.intent_type == "NO_MAPS_INTENT":
        return "NONE"

    if qi.intent_type == "ADDRESS":
        st.toast("HERE")
        st.write("--A result")
        st.write(result)
        return "PRIMARY" if result.usps_valid is True else "NONE"

    if qk and rn == qk:
        return "PRIMARY"

    if qk and qk in rn:
        return "PRIMARY"

    if qi.intent_type == "CATEGORY":
        if qk and (qk in rc or rc in qk):
            return "PRIMARY"

        # “zoo” and “wildlife park” kind of relation
        category_synonyms = {
            "zoo": {"zoo", "wildlife park", "animal park", "wildlife preserve"},
            "mall": {"mall", "shopping center", "shopping centre"},
        }
        for base, words in category_synonyms.items():
            if base in qk and any(w in rc for w in words):
                return "PRIMARY"

    if qi.intent_type == "TRANSIT":
        if any(tok in rn for tok in TRANSIT_HINTS) or any(tok in rc for tok in TRANSIT_HINTS):
            return "PRIMARY"

    if qk and any(tok in rn for tok in qk.split()):
        return "SECONDARY"

    if qk and any(tok in rc for tok in qk.split()):
        return "SECONDARY"

    if qi.intent_type == "POI_OR_BUSINESS" and result.result_type.upper() == "ADDRESS":
        return "NONE"

    if qi.intent_type == "ADDRESS" and result.result_type.upper() != "ADDRESS":
        # business at address is not a valid address-title result
        return "NONE"

    return "NONE"


def _is_sub_business_mismatch(qi: QueryIntent, result: ResultInput) -> bool:
    qk = normalize_key(qi.raw_query)
    rc = normalize_key(result.classification)
    rn = normalize_key(result.name)

    possible_container = any(term in qk for term in CATEGORY_CONTAINER_TERMS)
    if not possible_container:
        return False

    containerish = any(term in rc for term in CATEGORY_CONTAINER_TERMS)
    if containerish:
        return False

    # store inside mall / restaurant inside airport style mismatch
    if result.result_type.upper() == "BUSINESS" and not containerish:
        return True

    return False


def _rank_by_distance(values: list[Optional[float]], current: Optional[float]) -> Optional[int]:
    usable = sorted(v for v in values if v is not None)
    if current is None or not usable:
        return None
    for idx, val in enumerate(usable):
        if math.isclose(val, current, rel_tol=0.0, abs_tol=1e-9):
            return idx
    return None


def _apply_distance_demotion(
    relevance: RelevanceLabel,
    qi: QueryIntent,
    ctx: QueryContext,
    result: ResultInput,
    all_results: list[ResultInput],
) -> tuple[RelevanceLabel, list[str]]:
    reasons: list[str] = []

    if qi.explicit_location:
        return relevance, reasons

    if relevance == "Bad":
        return relevance, reasons

    many_possible = qi.is_chain or qi.intent_type == "CATEGORY"

    distances = [r.distance_to_user_km for r in all_results]
    rank = _rank_by_distance(distances, result.distance_to_user_km)

    demotions = 0
    if many_possible and rank is not None:
        if rank == 0:
            demotions = 0
        elif rank == 1:
            demotions = 1
        elif rank == 2:
            demotions = 2
        else:
            demotions = 3
    elif not many_possible and rank is not None:
        if rank <= 1:
            demotions = 0
        elif rank == 2:
            demotions = 1
        else:
            demotions = 1

    # FRESH + user inside viewport: cannot be Bad for distance alone
    if ctx.viewport_age == "FRESH" and ctx.user_inside_viewport is True and demotions > 0:
        if relevance in ("Navigational", "Excellent"):
            demotions = min(demotions, 2)
        elif relevance == "Good":
            demotions = min(demotions, 1)

    if demotions > 0:
        reasons.append("Distance/Prominence Issue")

    order = ["Bad", "Acceptable", "Good", "Excellent", "Navigational"]
    idx = order.index(relevance)
    new_idx = max(0, idx - demotions)
    return order[new_idx], reasons


def _apply_permanent_closure_rule(
    relevance: RelevanceLabel,
    result: ResultInput,
    qi: QueryIntent,
    all_results: list[ResultInput],
) -> tuple[RelevanceLabel, list[str]]:
    notes: list[str] = []

    if result.status != "PERMANENT_CLOSURE":
        return relevance, notes

    open_alternatives = [
        r for r in all_results
        if r is not result and r.status != "PERMANENT_CLOSURE"
    ]

    expected_pc = False
    if len(all_results) == 1:
        expected_pc = True
    elif qi.is_chain and not open_alternatives:
        expected_pc = True

    if expected_pc:
        notes.append("PERMANENT_CLOSURE shown but expected; rated as if open.")
        return relevance, notes

    # unexpected permanent closure => demote by 2, max Acceptable
    order = ["Bad", "Acceptable", "Good", "Excellent", "Navigational"]
    idx = order.index(relevance)
    new_idx = max(0, idx - 2)
    adjusted = order[new_idx]
    if adjusted in ("Excellent", "Navigational"):
        adjusted = "Acceptable"
    notes.append("Unexpected PERMANENT_CLOSURE with open options nearby; max Acceptable.")
    return adjusted, notes


def score_relevance(
    ctx: QueryContext,
    qi: QueryIntent,
    result: ResultInput,
    all_results: list[ResultInput],
    has_nav_result: bool,
) -> tuple[RelevanceLabel, list[str], list[str]]:
    notes: list[str] = []
    demotion_reasons: list[str] = []

    if qi.intent_type == "NO_MAPS_INTENT":
        return "Bad", ["No maps intent."], ["User Intent Issue"]

    if _is_sub_business_mismatch(qi, result):
        return "Bad", ["Store/business inside queried category container does not satisfy container intent."], ["User Intent Issue"]

    strength = _connection_strength(qi, result)
    if strength == "NONE":
        return "Bad", ["No sufficient query-result connection."], ["User Intent Issue"]

    base = _base_relevance_for_connection(has_nav_result, strength)
    notes.append(f"Initial query-result connection strength: {strength}.")

    base, dist_reasons = _apply_distance_demotion(base, qi, ctx, result, all_results)
    demotion_reasons.extend(dist_reasons)

    base, pc_notes = _apply_permanent_closure_rule(base, result, qi, all_results)
    notes.extend(pc_notes)

    if base in ("Good", "Acceptable", "Bad") and not demotion_reasons:
        demotion_reasons.append("User Intent Issue")

    st.write(f"{base=}, {notes=}, {demotion_reasons=}")

    return base, notes, demotion_reasons


def score_name(result: ResultInput) -> NameRating:
    if result.result_type.upper() == "ADDRESS":
        return "n/a"

    if not normalize_ws(result.official_name):
        return "Can't Verify"

    shown = normalize_key(result.name)
    official = normalize_key(result.official_name)

    if shown == official:
        return "Correct"

    if shown and official and (shown in official or official in shown):
        return "Partially Correct"

    return "Incorrect"


def _detect_address_issue(result_addr: str, official_addr: str) -> list[str]:
    result_k = normalize_key(result_addr)
    official_k = normalize_key(official_addr)

    if not result_k or not official_k:
        return []

    issues: list[str] = []

    result_num = re.findall(r"\b\d+\w*\b", result_addr.lower())
    official_num = re.findall(r"\b\d+\w*\b", official_addr.lower())
    if result_num and official_num and result_num[0] != official_num[0]:
        issues.append("Street Number")

    street_types = [" street", " st", " avenue", " ave", " boulevard", " blvd", " road", " rd", " drive", " dr", " lane", " ln"]
    if result_k != official_k and any(t in result_k or t in official_k for t in street_types):
        if "Street Number" not in issues:
            issues.append("Street Name")

    zip_res = re.findall(r"\b\d{5}\b", result_addr)
    zip_off = re.findall(r"\b\d{5}\b", official_addr)
    if zip_res and zip_off and zip_res[0] != zip_off[0]:
        issues.append("Postal Code")

    return issues


# def score_address(result: ResultInput) -> tuple[AddressRating, list[str]]:
#     issues: list[str] = []

#     if result.result_type.upper() == "ADDRESS" and result.usps_exists is False:
#         return "Incorrect", ["Address does not exist"]

#     if normalize_ws(result.official_address) and normalize_ws(result.address):
#         if normalize_key(result.official_address) == normalize_key(result.address):
#             return "Correct", []

#         issues = _detect_address_issue(result.address, result.official_address)
#         if issues:
#             return "Incorrect", issues

#         return "Correct with Formatting Issue", []

#     if result.usps_exists is True and result.usps_match_status:
#         if result.usps_match_status.lower() in {"exact normalized match", "equivalent match", "close match"}:
#             return "Correct", []

#     if result.usps_exists is False and result.result_type.upper() == "ADDRESS":
#         return "Incorrect", ["Address does not exist"]

#     return "Can't Verify", []


def score_address(result: ResultInput) -> tuple[AddressRating, list[str]]:
    issues: list[str] = []

    # Exact address-type result: DPV truth is authoritative when available.
    if result.result_type.upper() == "ADDRESS":
        if result.usps_exists is True:
            return "Correct", []
        if result.usps_exists is False:
            return "Incorrect", ["Address does not exist"]

    if normalize_ws(result.official_address) and normalize_ws(result.address):
        if normalize_key(result.official_address) == normalize_key(result.address):
            return "Correct", []

        issues = _detect_address_issue(result.address, result.official_address)
        if issues:
            return "Incorrect", issues

        return "Correct with Formatting Issue", []

    if result.usps_exists is True and result.usps_match_status:
        if result.usps_match_status.lower() in {"exact normalized match", "equivalent match", "close match"}:
            return "Correct", []

    if result.result_type.upper() == "ADDRESS" and result.usps_exists is False:
        return "Incorrect", ["Address does not exist"]

    return "Can't Verify", []


def score_pin(result: ResultInput, address_rating: AddressRating, address_issues: list[str]) -> PinRating:
    if result.lat is None or result.lon is None:
        return "Wrong"

    if address_rating == "Incorrect" and "Address does not exist" in address_issues:
        return "Can't Verify"

    if result.pin_boundary_identifiable is False:
        return "Can't Verify"

    if result.pin_same_property is True:
        if result.pin_precise is True:
            return "Perfect"
        return "Approximate"

    if result.pin_adjacent_property is True:
        return "Next Door"

    if result.pin_same_block is True:
        return "Approximate"

    if result.pin_same_property is False:
        return "Wrong"

    return "Can't Verify"


# def build_comment(
#     ctx: QueryContext,
#     qi: QueryIntent,
#     result: ResultInput,
#     rating: RatingResult,
# ) -> str:
#     parts: list[str] = []

#     parts.append(f"User intent: {qi.raw_query}.")

#     if ctx.locale != "en_US":
#         parts.append(f"Unexpected locale input: {ctx.locale}.")
#     if ctx.country != "United States":
#         parts.append(f"Unexpected country input: {ctx.country}.")

#     parts.append(f"Relevance: {rating.relevance}.")
#     if rating.relevance_notes:
#         parts.append(" ".join(rating.relevance_notes))

#     if rating.demotion_reasons:
#         parts.append("Demotion reason(s): " + ", ".join(rating.demotion_reasons) + ".")

#     if rating.business_closed_or_dne:
#         parts.append("Closed/DNE flag selected; relevance still rated as if open.")

#     if rating.name_rating not in {"Correct", "n/a"}:
#         parts.append(f"Name rating: {rating.name_rating}.")

#     if rating.address_rating not in {"Correct", "n/a"}:
#         if rating.address_issues:
#             parts.append(f"Address rating: {rating.address_rating} ({', '.join(rating.address_issues)}).")
#         else:
#             parts.append(f"Address rating: {rating.address_rating}.")

#     if rating.pin_rating not in {"Perfect", "n/a"}:
#         parts.append(f"Pin rating: {rating.pin_rating}.")

#     return " ".join(parts)


def build_comment(
    ctx: QueryContext,
    qi: QueryIntent,
    result: ResultInput,
    rating: RatingResult,
    all_results: Optional[list[ResultInput]] = None,
) -> str:
    parts: list[str] = []

    parts.append(f"User intent: {qi.raw_query}.")

    if ctx.locale != "en_US":
        parts.append(f"Unexpected locale input: {ctx.locale}.")
    if ctx.country != "United States":
        parts.append(f"Unexpected country input: {ctx.country}.")

    rel_head = f"[Relevance- {rating.relevance}"
    if rating.demotion_reasons:
        rel_head += " - " + ", ".join(rating.demotion_reasons)
    rel_head += "]"
    parts.append(rel_head)

    if rating.relevance_notes:
        parts.append(" ".join(rating.relevance_notes))

    if qi.is_chain:
        locator_url, _ = get_chain_locator(qi.raw_query)
        parts.append(
            f"For this chain query, distance is a critical factor. Even if this result looks appropriate, verify whether a closer qualifying location exists using the official locator: {locator_url}"
        )

    if rating.business_closed_or_dne:
        parts.append("Closed/DNE flag selected; relevance is still rated as if open per guideline behavior.")

    parts.append(f"[Name- {rating.name_rating}]")
    if result.official_name:
        parts.append(f"Compare against official naming/source details when available.")

    parts.append(f"[Address- {rating.address_rating}]")
    if rating.address_issues:
        parts.append(f"Address issue(s): {', '.join(rating.address_issues)}.")

    if result.result_type.upper() == "ADDRESS":
        if result.usps_exists is True:
            parts.append("USPS DPV indicates this exact address exists (DPV=Y).")
        elif result.usps_exists is False:
            parts.append("USPS DPV does not confirm this exact address as existing. Treat the address as incorrect unless further evidence shows input/typo issues.")
        else:
            parts.append("USPS DPV could not conclusively verify this exact address. Check for typos, formatting issues, or incomplete locality/state/ZIP details.")

    parts.append(f"[Pin- {rating.pin_rating}]")
    if rating.pin_rating in {"Approximate", "Next Door", "Can't Verify"}:
        parts.append("Pin placement should be checked further against rooftop/property evidence.")

    if all_results:
        parts.extend(_chain_verification_note(qi, result, all_results))

    return " ".join(parts)


def score_result(
    ctx: QueryContext,
    result: ResultInput,
    all_results: list[ResultInput],
    class_in: str
) -> RatingResult:
    qi = classify_query(ctx.query, class_in)
    nav = has_navigational_result(qi, all_results)

    unexpected_language = is_unexpected_language_or_script(ctx.query, result.name, ctx.locale, ctx.country)
    if unexpected_language:
        locked = RatingResult(
            has_navigational_result=nav,
            unexpected_language_or_script=True,
            business_closed_or_dne=False,
            relevance="Bad",
            relevance_notes=["Result title/name is in unexpected language or script; remaining ratings locked."],
            demotion_reasons=[],
            name_rating="n/a",
            address_rating="n/a",
            address_issues=[],
            pin_rating="n/a",
            comment="Result title/name is in an unexpected language or script, so other ratings are not applicable.",
        )
        return locked

    business_closed_or_dne = result.status in {"CLOSED", "PERMANENT_CLOSURE"}

    relevance, relevance_notes, demotion_reasons = score_relevance(
        ctx=ctx,
        qi=qi,
        result=result,
        all_results=all_results,
        has_nav_result=nav,
    )

    name_rating = score_name(result)
    address_rating, address_issues = score_address(result)
    pin_rating = score_pin(result, address_rating, address_issues)

    out = RatingResult(
        has_navigational_result=nav,
        unexpected_language_or_script=False,
        business_closed_or_dne=business_closed_or_dne,
        relevance=relevance,
        relevance_notes=relevance_notes,
        demotion_reasons=demotion_reasons,
        name_rating=name_rating,
        address_rating=address_rating,
        address_issues=address_issues,
        pin_rating=pin_rating,
        comment="",
    )
    out.comment = build_comment(ctx, qi, result, out, all_results=all_results)
    return out

def bing_maps_link(lat: float, lon: float) -> str:
    return f"https://www.bing.com/maps?cp={lat}~{lon}&lvl=17"

def bing_maps_address_link(address: str) -> str:
    return f"https://www.bing.com/maps?q={urllib.parse.quote(address)}"

def usps_lookup_hint_link(address: str) -> str:
    # best-effort public USPS location/search landing, not strict address validation
    return f"https://tools.usps.com/find-location.htm?locationType=po&address={urllib.parse.quote(address)}"

def _closest_open_distance_km(all_results: list[ResultInput]) -> Optional[float]:
    vals = [
        r.distance_to_user_km
        for r in all_results
        if r.distance_to_user_km is not None and r.status != "PERMANENT_CLOSURE"
    ]
    return min(vals) if vals else None


def _chain_verification_note(qi: QueryIntent, result: ResultInput, all_results: list[ResultInput]) -> list[str]:
    notes: list[str] = []
    if not qi.is_chain:
        return notes

    locator_url, found = get_chain_locator(qi.raw_query)
    closest = _closest_open_distance_km(all_results)
    current = result.distance_to_user_km

    if current is None:
        notes.append(
            f"Chain query detected. Distance is a critical factor here. Verify on the official locator: {locator_url}"
        )
        return notes

    if closest is None:
        notes.append(
            f"Chain query detected. This result may be strong, but you should still verify whether a closer open location exists using: {locator_url}"
        )
        return notes

    if math.isclose(current, closest, rel_tol=0.0, abs_tol=1e-9):
        notes.append(
            f"Chain query detected. This appears to be the closest open returned result by distance. Still verify nearby official locations here: {locator_url}"
        )
    else:
        notes.append(
            f"Chain query detected. A closer open returned result appears to exist. Verify closest locations using the official locator: {locator_url}"
        )

    return notes