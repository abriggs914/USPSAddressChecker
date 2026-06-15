# rating_engine.py
from __future__ import annotations

import math
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Literal, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Type aliases
# ─────────────────────────────────────────────────────────────────────────────
ViewportAge     = Literal["FRESH", "STALE"]
LocationBasis   = Literal["EXPLICIT_QUERY", "USER", "VIEWPORT", "TEST_LOCALE"]
RelevanceLabel  = Literal["Navigational", "Excellent", "Good", "Acceptable", "Bad"]
NameRating      = Literal["Correct", "Partially Correct", "Incorrect", "Can't Verify", "n/a"]
AddressRating   = Literal["Correct", "Correct with Formatting Issue", "Incorrect", "Can't Verify", "n/a"]
PinRating       = Literal["Perfect", "Approximate", "Next Door", "Wrong", "Can't Verify", "n/a"]
IntentType      = Literal[
    "NO_MAPS_INTENT", "ADDRESS", "POI_OR_BUSINESS",
    "CATEGORY", "PRODUCT_SERVICE", "LOCALITY",
    "TRANSIT", "COORDINATE", "EMOJI",
]
ClosedStatus    = Literal["OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"]

# Severity for assumption flags
AssumptionSeverity = Literal["error", "warning", "info"]


# ─────────────────────────────────────────────────────────────────────────────
# Data-classes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AssumptionFlag:
    """One investigable assumption the rater must confirm or override."""
    field: str                      # which field / concept
    message: str                    # human-readable description
    severity: AssumptionSeverity    # error = blocks confidence, warning = degrades, info = FYI
    action: str                     # what the rater should do


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
    user_inside_viewport: Optional[bool] = None   # None = unknown


@dataclass
class ResultInput:
    name: str
    address: str
    classification: str
    result_type: str                   # BUSINESS | ADDRESS | LOCALITY | TRANSIT | NATURAL_FEATURE
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

    # Pin evidence – all must be set by UI to get a decisive pin rating
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
    explicit_location: Optional[str]   # e.g. "Rockville MD" parsed from query
    has_near_me: bool
    is_chain: bool
    probably_unique: bool              # single-location POI / unique POI
    location_modifier: Optional[str] = None   # city/state extracted from chain query


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

    # Structured assumptions the rater must verify
    assumption_flags: list[AssumptionFlag]

    comment: str


# ─────────────────────────────────────────────────────────────────────────────
# Lookup tables
# ─────────────────────────────────────────────────────────────────────────────
CHAIN_LOCATORS: dict[str, str] = {
    # Fast food
    "mcdonald's":       "https://www.mcdonalds.com/us/en-us/restaurant-locator.html",
    "mcdonalds":        "https://www.mcdonalds.com/us/en-us/restaurant-locator.html",
    "burger king":      "https://www.burgerking.com/store-locator",
    "kfc":              "https://www.kfc.com/find-a-kfc",
    "taco bell":        "https://www.tacobell.com/find-a-taco-bell",
    "wendy's":          "https://www.wendys.com/restaurant-locator",
    "wendys":           "https://www.wendys.com/restaurant-locator",
    "subway":           "https://www.subway.com/en-US/FindASubway",
    "chick-fil-a":      "https://www.chick-fil-a.com/locations",
    "chick fil a":      "https://www.chick-fil-a.com/locations",
    "chickfila":        "https://www.chick-fil-a.com/locations",
    "whataburger":      "https://whataburger.com/locations",
    "popeyes":          "https://www.popeyes.com/store-locator",
    "five guys":        "https://www.fiveguys.com/locations",
    "in-n-out":         "https://www.in-n-out.com/locations",
    "in n out":         "https://www.in-n-out.com/locations",
    "sonic":            "https://www.sonicdrivein.com/locations",
    "dairy queen":      "https://www.dairyqueen.com/en-us/locator/",
    "jack in the box":  "https://www.jackinthebox.com/locations",
    "hardee's":         "https://www.hardees.com/locations",
    "hardees":          "https://www.hardees.com/locations",
    "carl's jr":        "https://www.carlsjr.com/locations",
    "carls jr":         "https://www.carlsjr.com/locations",
    "arby's":           "https://arbys.com/locations",
    "arbys":            "https://arbys.com/locations",
    "panera":           "https://www.panerabread.com/en-us/cafe-locator.html",
    "panera bread":     "https://www.panerabread.com/en-us/cafe-locator.html",
    "chipotle":         "https://www.chipotle.com/order",
    "domino's":         "https://www.dominos.com/en/pages/locator/",
    "dominos":          "https://www.dominos.com/en/pages/locator/",
    "pizza hut":        "https://www.pizzahut.com/locator",
    "papa john's":      "https://www.papajohns.com/order/store-finder",
    "papa johns":       "https://www.papajohns.com/order/store-finder",
    "little caesars":   "https://littlecaesars.com/en-us/store-locator/",
    "dunkin":           "https://www.dunkindonuts.com/en/locations",
    "dunkin donuts":    "https://www.dunkindonuts.com/en/locations",
    "starbucks":        "https://www.starbucks.com/store-locator",
    "tim hortons":      "https://www.timhortons.com/store-locator",
    "panda express":    "https://www.pandaexpress.com/locations",
    "raising cane's":   "https://www.raisingcanes.com/locations",
    "wingstop":         "https://www.wingstop.com/order",
    "freddy's":         "https://www.freddysusa.com/locations/",
    "freddys":          "https://www.freddysusa.com/locations/",
    "applebee's":       "https://restaurants.applebees.com/en-us/",
    "applebees":        "https://restaurants.applebees.com/en-us/",
    # Retail
    "walmart":          "https://www.walmart.com/store/finder",
    "target":           "https://www.target.com/store-locator/find-stores",
    "costco":           "https://www.costco.com/warehouse-locations",
    "home depot":       "https://www.homedepot.com/l/storelocator",
    "lowe's":           "https://www.lowes.com/store",
    "lowes":            "https://www.lowes.com/store",
    "best buy":         "https://www.bestbuy.com/site/store-locator/store-finder",
    "walgreens":        "https://www.walgreens.com/storelocator/find.jsp",
    "cvs":              "https://www.cvs.com/store-locator/landing",
    "rite aid":         "https://www.riteaid.com/locations",
    "dollar tree":      "https://www.dollartree.com/locations/index",
    "dollar general":   "https://www.dollargeneral.com/store-directory",
    "family dollar":    "https://stores.familydollar.com/",
    "tj maxx":          "https://tjmaxx.tjx.com/store-locator",
    "marshalls":        "https://www.marshalls.com/us/store/index.jsp",
    "ross":             "https://www.rossstores.com/store-finder",
    "whole foods":      "https://www.wholefoodsmarket.com/stores",
    "trader joe's":     "https://www.traderjoes.com/home/stores",
    "trader joes":      "https://www.traderjoes.com/home/stores",
    "aldi":             "https://stores.aldi.us/",
    "kroger":           "https://www.kroger.com/stores/search",
    "safeway":          "https://www.safeway.com/stores/grocery-stores-near-me.html",
    "publix":           "https://www.publix.com/locations",
    "meijer":           "https://www.meijer.com/shopping/store-locator.html",
    "sam's club":       "https://www.samsclub.com/club-finder",
    "wegmans":          "https://www.wegmans.com/stores/",
    "dsw":              "https://www.dsw.com/en/us/stores",
    "saks fifth avenue":"https://www.saksfifthavenue.com/stores",
    "saks off 5th":     "https://www.saksoff5th.com/stores",
    # Fuel / Convenience
    "shell":            "https://www.shell.com/motorists/shell-station-locator.html",
    "chevron":          "https://www.chevronwithtechron.com/en_us/home/find-a-station.html",
    "bp":               "https://www.bp.com/en_us/united-states/home/find-a-gas-station.html",
    "exxon":            "https://www.exxon.com/en/find-station",
    "mobil":            "https://www.mobil.com/en/find-station",
    "7-eleven":         "https://www.7-eleven.com/en/store-locator",
    "7 eleven":         "https://www.7-eleven.com/en/store-locator",
    "circle k":         "https://www.circlek.com/find-a-store",
    "speedway":         "https://www.speedway.com/storelocator",
    # Hotels
    "marriott":         "https://www.marriott.com/find-hotels/findHotels.mi",
    "hilton":           "https://www.hilton.com/en/locations/",
    "holiday inn":      "https://www.ihg.com/holidayinn/hotels/us/en/find-hotels/hotel/list",
    "hampton inn":      "https://www.hilton.com/en/hampton/",
    "hyatt":            "https://www.hyatt.com/find-a-hotel",
    "best western":     "https://www.bestwestern.com/en_US/find-a-hotel.html",
    "motel 6":          "https://www.motel6.com/en/home/find-a-motel.html",
    # Banks
    "chase":            "https://locator.chase.com/",
    "bank of america":  "https://www.bankofamerica.com/banking-centers-atms/",
    "wells fargo":      "https://www.wellsfargo.com/locator/",
    "citibank":         "https://online.citi.com/US/JRS/portal/template.do?ID=ATMBranchLocator",
    "td bank":          "https://www.td.com/us/en/personal-banking/locations/",
    "us bank":          "https://www.usbank.com/bank-accounts/locations.html",
    # Other services
    "ups store":        "https://www.theupsstore.com/tools/find-a-store",
    "fedex":            "https://local.fedex.com/",
    "usps":             "https://tools.usps.com/find-location.htm",
    "planet fitness":   "https://www.planetfitness.com/gyms",
    "la fitness":       "https://www.lafitness.com/pages/clublocator.aspx",
    "anytime fitness":  "https://www.anytimefitness.com/gyms/",
    "autozone":         "https://www.autozone.com/locations",
    "o'reilly":         "https://www.oreillyauto.com/store-locator",
    "oreilly":          "https://www.oreillyauto.com/store-locator",
    "advance auto parts":"https://shop.advanceautoparts.com/o/store-locator",
    "jiffy lube":       "https://www.jiffylube.com/locations",
    "valvoline":        "https://www.vioc.com/locations",
    # Transit
    "amtrak":           "https://www.amtrak.com/find-a-station",
    "greyhound":        "https://www.greyhound.com/en/locations",
}

TRANSIT_HINTS   = {"station", "airport", "terminal", "metro", "subway", "train", "bus stop", "bart"}
NO_MAPS_TERMS   = {"weather", "time", "facebook", "instagram", "youtube", "netflix", "twitter", "tiktok"}

# Container-category terms: querying one of these expects the container, not a store inside it
CATEGORY_CONTAINER_TERMS = {
    "mall", "shopping center", "shopping centre", "airport", "terminal",
    "park", "complex", "center", "centre", "hospital", "campus",
}

RELEVANCE_ORDER = ["Bad", "Acceptable", "Good", "Excellent", "Navigational"]


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_key(s: str) -> str:
    s = normalize_ws(s).lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w\s]", "", s)
    return normalize_ws(s)


def demote(relevance: RelevanceLabel, steps: int) -> RelevanceLabel:
    idx = RELEVANCE_ORDER.index(relevance)
    return RELEVANCE_ORDER[max(0, idx - steps)]  # type: ignore[return-value]


def google_maps_link(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def google_maps_address_link(address: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"


def bing_maps_link(lat: float, lon: float) -> str:
    return f"https://www.bing.com/maps?cp={lat}~{lon}&lvl=17"


def bing_maps_address_link(address: str) -> str:
    return f"https://www.bing.com/maps?q={urllib.parse.quote(address)}"


def usps_lookup_link(address: str) -> str:
    return f"https://tools.usps.com/zip-code-lookup.htm?byaddress"


def get_chain_locator(query: str) -> tuple[str, bool]:
    """Return (url, found). Falls back to a Google search if not in the table."""
    q = query.lower().strip()
    if q in CHAIN_LOCATORS:
        return CHAIN_LOCATORS[q], True
    for key, url in CHAIN_LOCATORS.items():
        if key in q or q in key:
            return url, True
    encoded = urllib.parse.quote(f"{query} store locator official site")
    return f"https://www.google.com/search?q={encoded}", False


# ─────────────────────────────────────────────────────────────────────────────
# Query classification
# ─────────────────────────────────────────────────────────────────────────────
def _extract_location_modifier(query_lower: str) -> Optional[str]:
    """
    Detect explicit location modifiers like 'in Rockville MD' or 'Rockville MD'
    appended to a chain name.  Returns the location string or None.
    """
    m = re.search(r"\b(?:in|near|at|around|within)\s+(.+)$", query_lower)
    if m:
        return m.group(1).strip()
    # trailing city+state pattern like "wegmans rockville md"
    m2 = re.search(r"\b([a-z][a-z\s]+,?\s+[a-z]{2})\s*$", query_lower)
    if m2:
        candidate = m2.group(1).strip()
        # avoid matching the chain name itself
        if len(candidate.split()) >= 2:
            return candidate
    return None


def classify_query(query: str) -> QueryIntent:
    q = normalize_ws(query)
    ql = q.lower()

    if not q:
        return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

    if any(term in ql for term in NO_MAPS_TERMS):
        return QueryIntent("NO_MAPS_INTENT", q, None, False, False, False)

    if re.fullmatch(r"-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?", q):
        return QueryIntent("COORDINATE", q, None, False, False, True)

    has_near_me = any(tok in ql for tok in ("near me", "nearby", "nearest", "closest"))

    locator_url, is_chain = get_chain_locator(q)
    location_modifier = _extract_location_modifier(ql) if not has_near_me else None

    # Street address: digit followed by street name
    if re.search(r"\b\d+\s+[a-z]", ql):
        return QueryIntent("ADDRESS", q, location_modifier, has_near_me, is_chain, True, location_modifier)

    # Transit
    if any(tok in ql for tok in TRANSIT_HINTS):
        probably_unique = not is_chain
        return QueryIntent("TRANSIT", q, location_modifier, has_near_me, is_chain, probably_unique, location_modifier)

    if is_chain:
        probably_unique = location_modifier is not None and not has_near_me
        return QueryIntent(
            "POI_OR_BUSINESS", q, location_modifier, has_near_me, True, probably_unique, location_modifier
        )

    # Category container?
    if any(term in ql for term in CATEGORY_CONTAINER_TERMS):
        return QueryIntent("CATEGORY", q, location_modifier, has_near_me, False, False, location_modifier)

    # Fallback: named POI
    return QueryIntent("POI_OR_BUSINESS", q, location_modifier, has_near_me, False, False, location_modifier)


# ─────────────────────────────────────────────────────────────────────────────
# Location basis
# ─────────────────────────────────────────────────────────────────────────────
def determine_location_basis(ctx: QueryContext, qi: QueryIntent) -> LocationBasis:
    """Determine which coordinate anchor to use per GL §2.3.2."""
    if qi.explicit_location or qi.location_modifier:
        return "EXPLICIT_QUERY"
    if ctx.viewport_age == "STALE":
        return "USER" if ctx.user_lat is not None else "TEST_LOCALE"
    # Fresh viewport
    if ctx.user_inside_viewport is True:
        return "USER"
    if ctx.user_inside_viewport is False:
        return "VIEWPORT"
    # Unknown – treat as user inside if coords available
    return "USER" if ctx.user_lat is not None else "TEST_LOCALE"


# ─────────────────────────────────────────────────────────────────────────────
# Navigational determination
# ─────────────────────────────────────────────────────────────────────────────
def has_navigational_result(qi: QueryIntent, results: list[ResultInput]) -> bool:
    """
    True when exactly one real-world result satisfies the query uniquely.
    Chain queries without a unique location modifier are NOT navigational.
    """
    if qi.intent_type == "NO_MAPS_INTENT":
        return False
    if qi.is_chain and not qi.probably_unique:
        return False
    if qi.intent_type == "ADDRESS":
        # Navigational only when the exact address is verified to exist
        return any(r.usps_exists is True for r in results)

    qk = normalize_key(qi.raw_query)
    exact = [r for r in results if normalize_key(r.name) == qk]
    if len(exact) == 1:
        return True
    fuzzy = [r for r in results if qk and qk in normalize_key(r.name)]
    return len(fuzzy) == 1 and qi.probably_unique


# ─────────────────────────────────────────────────────────────────────────────
# Language / script check
# ─────────────────────────────────────────────────────────────────────────────
def is_unexpected_language_or_script(result_name: str, locale: str) -> bool:
    if locale != "en_US":
        return False
    return bool(re.search(r"[\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF]", result_name or ""))


# ─────────────────────────────────────────────────────────────────────────────
# Connection strength
# ─────────────────────────────────────────────────────────────────────────────
def _connection_strength(qi: QueryIntent, result: ResultInput) -> str:
    """
    Returns "PRIMARY" | "SECONDARY" | "UNLIKELY" | "NONE".

    Key rules:
    - ADDRESS query + non-address result → NONE  (§5.1.8 / §10.1)
    - POI/Business query + address-only result → NONE  (§5.1.8)
    - Store inside a queried container (mall, airport, etc.) → NONE (§5.1.8)
    - Sam's Club ≠ Sam's Club Pharmacy  (sub-brand mismatch) → NONE
    - Service-level mismatch (Saks vs Saks OFF 5TH) → SECONDARY (Good start)
    """
    qk = normalize_key(qi.raw_query)
    rn = normalize_key(result.name)
    rc = normalize_key(result.classification)
    rt = result.result_type.upper()

    if qi.intent_type == "NO_MAPS_INTENT":
        return "NONE"

    # ADDRESS query: result must be an address-type result
    if qi.intent_type == "ADDRESS":
        if rt not in ("ADDRESS",):
            return "NONE"   # business at correct address ≠ address result (§10.1)
        return "PRIMARY" if (result.usps_valid is True or result.usps_exists is True) else "NONE"

    # POI/Business query: address-only result is not sufficient (§5.1.8)
    if qi.intent_type in ("POI_OR_BUSINESS", "CATEGORY") and rt == "ADDRESS":
        return "NONE"

    # Container mismatch: user asked for mall/airport/campus, got store inside it
    if _is_sub_business_mismatch(qi, result):
        return "NONE"

    # Sub-brand mismatch: e.g. "Sam's Club" → "Sam's Club Pharmacy"
    if _is_sub_brand_mismatch(qi, result):
        return "NONE"

    # Exact name match
    if qk and rn == qk:
        return "PRIMARY"

    # Query is a substring of result name (e.g. "Starbucks" in "Starbucks Reserve")
    if qk and qk in rn:
        return "PRIMARY"

    # Category queries: classification match
    if qi.intent_type == "CATEGORY":
        if qk and (qk in rc or rc in qk):
            return "PRIMARY"
        category_synonyms: dict[str, set[str]] = {
            "zoo":  {"zoo", "wildlife park", "animal park", "wildlife preserve"},
            "mall": {"mall", "shopping center", "shopping centre", "outlet"},
        }
        for base, words in category_synonyms.items():
            if base in qk and any(w in rc for w in words):
                return "PRIMARY"

    # Transit queries
    if qi.intent_type == "TRANSIT":
        if any(tok in rn for tok in TRANSIT_HINTS) or any(tok in rc for tok in TRANSIT_HINTS):
            return "PRIMARY"

    # Service-level mismatch (e.g. Saks OFF 5TH for "Saks Fifth Avenue") → Good at best
    if _is_service_level_mismatch(qi, result):
        return "SECONDARY"

    # Partial name token overlap
    q_tokens = set(qk.split())
    r_tokens = set(rn.split())
    if q_tokens & r_tokens:
        return "SECONDARY"

    # Classification token overlap
    if q_tokens & set(rc.split()):
        return "SECONDARY"

    return "NONE"


def _is_sub_business_mismatch(qi: QueryIntent, result: ResultInput) -> bool:
    """Query is for a container (mall, airport) but result is a store inside it."""
    qk = normalize_key(qi.raw_query)
    rc = normalize_key(result.classification)

    query_is_container = any(term in qk for term in CATEGORY_CONTAINER_TERMS)
    if not query_is_container:
        return False
    result_is_container = any(term in rc for term in CATEGORY_CONTAINER_TERMS)
    # If the result itself is not a container-type, it's a sub-business mismatch
    return not result_is_container


def _is_sub_brand_mismatch(qi: QueryIntent, result: ResultInput) -> bool:
    """
    Detect cases like "Sam's Club" → "Sam's Club Pharmacy" or
    "Costco" → "Costco Gasoline" where the result is a different entity
    under the same brand umbrella.
    """
    qk = normalize_key(qi.raw_query)
    rn = normalize_key(result.name)

    if not qk or not rn:
        return False
    if qk == rn:
        return False
    # Result name starts with query name but has extra words that change the entity
    SUB_BRAND_SUFFIXES = {
        "pharmacy", "gasoline", "gas", "optical", "tire", "cafe",
        "express", "go", "mini", "jr", "lite", "plus",
    }
    if rn.startswith(qk + " "):
        suffix = rn[len(qk):].strip()
        if any(s in suffix for s in SUB_BRAND_SUFFIXES):
            return True
    return False


def _is_service_level_mismatch(qi: QueryIntent, result: ResultInput) -> bool:
    """
    Detect queries for a premium/specific brand returning a discount/outlet variant.
    e.g. "Saks Fifth Avenue" → "Saks OFF 5TH"  (GL §5.28)
    """
    qk = normalize_key(qi.raw_query)
    rn = normalize_key(result.name)
    if not qk or not rn:
        return False

    service_pairs = [
        ("saks fifth avenue", "saks off 5th"),
        ("nordstrom", "nordstrom rack"),
        ("neiman marcus", "last call"),
        ("bloomingdale's", "bloomingdale's outlet"),
    ]
    for full, discount in service_pairs:
        if full in qk and discount in rn:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Distance demotion  (GL §5.4 / §5.6 / §5.7 / §2.3.2)
# ─────────────────────────────────────────────────────────────────────────────
def _reference_distance_km(
    ctx: QueryContext, qi: QueryIntent, result: ResultInput
) -> Optional[float]:
    """Pick the right distance field based on location basis."""
    basis = determine_location_basis(ctx, qi)
    if basis in ("USER",):
        return result.distance_to_user_km
    if basis == "VIEWPORT":
        return result.distance_to_viewport_km
    if basis == "EXPLICIT_QUERY":
        # For chain+location-modifier queries, distance_to_viewport is best proxy
        return result.distance_to_viewport_km
    return result.distance_to_user_km


def _rank_by_distance(
    all_results: list[ResultInput], current_km: Optional[float],
    ctx: QueryContext, qi: QueryIntent,
) -> Optional[int]:
    """0-indexed rank of this result by reference distance among open results."""
    def ref(r: ResultInput) -> Optional[float]:
        basis = determine_location_basis(ctx, qi)
        if basis == "USER":
            return r.distance_to_user_km
        return r.distance_to_viewport_km

    vals = sorted(
        v for r in all_results
        if (v := ref(r)) is not None and r.status != "PERMANENT_CLOSURE"
    )
    if current_km is None or not vals:
        return None
    for idx, v in enumerate(vals):
        if math.isclose(v, current_km, rel_tol=1e-6, abs_tol=1e-6):
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

    if relevance == "Bad":
        return relevance, reasons

    # Location-modifier queries: distance from the named locality dominates
    # We still demote by rank among returned results as proxy
    many_possible = qi.is_chain or qi.intent_type in ("CATEGORY",)
    few_possible  = not many_possible

    current_km = _reference_distance_km(ctx, qi, result)
    rank = _rank_by_distance(all_results, current_km, ctx, qi)

    # Demotion steps by rank
    if rank is None:
        # Can't determine rank → no automated demotion, flag it
        return relevance, reasons

    if many_possible:
        demotions = min(rank, 3)   # 0→0, 1→-1, 2→-2, 3+→-3 (Bad)
    else:
        # Few possible results: be lenient (§5.7)
        demotions = 0 if rank <= 1 else 1

    # FRESH + user INSIDE viewport: inner results cannot be Bad for distance alone (§2.3.2)
    if (
        ctx.viewport_age == "FRESH"
        and ctx.user_inside_viewport is True
        and result.distance_to_user_km is not None
    ):
        # Inside the viewport bbox → cap demotion so it can't reach Bad
        if demotions >= 3:
            demotions = 2  # max Acceptable, never Bad for distance alone

    if demotions > 0:
        reasons.append("Distance/Prominence Issue")

    return demote(relevance, demotions), reasons


# ─────────────────────────────────────────────────────────────────────────────
# Permanent closure rule  (GL §5.19)
# ─────────────────────────────────────────────────────────────────────────────
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
        if r is not result and r.status not in ("PERMANENT_CLOSURE", "CLOSED")
    ]

    expected = (len(all_results) == 1) or (qi.is_chain and not open_alternatives)

    if expected:
        notes.append(
            "PERMANENT_CLOSURE shown but expected (no open alternatives nearby); rated as if open."
        )
        return relevance, notes

    # Unexpected permanent closure with open options nearby → demote 2, max Acceptable
    new_rel = demote(relevance, 2)
    if new_rel in ("Excellent", "Navigational"):
        new_rel = "Acceptable"
    notes.append(
        "Unexpected PERMANENT_CLOSURE: open options exist nearby. Max rating = Acceptable."
    )
    return new_rel, notes


# ─────────────────────────────────────────────────────────────────────────────
# Relevance scoring  (GL §5)
# ─────────────────────────────────────────────────────────────────────────────
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
        return "Bad", ["Query has no maps intent."], ["User Intent Issue"]

    strength = _connection_strength(qi, result)
    if strength == "NONE":
        return "Bad", ["No sufficient query-result connection (§5.1)."], ["User Intent Issue"]

    # Base relevance from connection strength
    if strength == "PRIMARY":
        base: RelevanceLabel = "Navigational" if has_nav_result else "Excellent"
    elif strength == "SECONDARY":
        base = "Good"
    else:  # UNLIKELY — currently not used separately but guard it
        base = "Acceptable"

    notes.append(f"Connection: {strength}. Base = {base}.")

    # Distance demotion
    base, dist_reasons = _apply_distance_demotion(base, qi, ctx, result, all_results)
    demotion_reasons.extend(dist_reasons)

    # Permanent closure adjustment
    base, pc_notes = _apply_permanent_closure_rule(base, result, qi, all_results)
    notes.extend(pc_notes)

    # Ensure demotion_reasons is populated when needed
    if base in ("Good", "Acceptable", "Bad") and not demotion_reasons:
        demotion_reasons.append("User Intent Issue")

    return base, notes, demotion_reasons


# ─────────────────────────────────────────────────────────────────────────────
# Name accuracy  (GL §6)
# ─────────────────────────────────────────────────────────────────────────────
def score_name(result: ResultInput) -> NameRating:
    if result.result_type.upper() == "ADDRESS":
        return "n/a"
    if not normalize_ws(result.official_name):
        return "Can't Verify"

    shown    = normalize_key(result.name)
    official = normalize_key(result.official_name)

    if shown == official:
        return "Correct"
    if shown and official and (shown in official or official in shown):
        return "Partially Correct"
    return "Incorrect"


# ─────────────────────────────────────────────────────────────────────────────
# Address accuracy  (GL §7)
# ─────────────────────────────────────────────────────────────────────────────
def _detect_address_issues(result_addr: str, official_addr: str) -> list[str]:
    rk = normalize_key(result_addr)
    ok = normalize_key(official_addr)
    if not rk or not ok:
        return []

    issues: list[str] = []

    r_nums = re.findall(r"\b\d+\w*\b", result_addr)
    o_nums = re.findall(r"\b\d+\w*\b", official_addr)
    if r_nums and o_nums and r_nums[0] != o_nums[0]:
        issues.append("Street Number")

    street_types = {
        " street", " st", " avenue", " ave", " boulevard", " blvd",
        " road", " rd", " drive", " dr", " lane", " ln", " court", " ct",
        " place", " pl", " way", " circle", " cir",
    }
    if rk != ok and any(t in rk or t in ok for t in street_types):
        if "Street Number" not in issues:
            issues.append("Street Name")

    zips_r = re.findall(r"\b\d{5}\b", result_addr)
    zips_o = re.findall(r"\b\d{5}\b", official_addr)
    if zips_r and zips_o and zips_r[0] != zips_o[0]:
        issues.append("Postal Code")

    return issues


def score_address(result: ResultInput) -> tuple[AddressRating, list[str]]:
    rt = result.result_type.upper()

    # ADDRESS-type results: USPS DPV is authoritative
    if rt == "ADDRESS":
        if result.usps_exists is True:
            return "Correct", []
        if result.usps_exists is False:
            return "Incorrect", ["Address does not exist"]
        # Not yet checked
        return "Can't Verify", []

    # POI/Business: compare against official address if provided
    if normalize_ws(result.official_address) and normalize_ws(result.address):
        if normalize_key(result.official_address) == normalize_key(result.address):
            return "Correct", []
        issues = _detect_address_issues(result.address, result.official_address)
        if issues:
            return "Incorrect", issues
        return "Correct with Formatting Issue", []

    # USPS match as fallback
    if result.usps_exists is True and result.usps_match_status:
        if result.usps_match_status.lower() in {"exact normalized match", "equivalent match", "close match"}:
            return "Correct", []

    return "Can't Verify", []


# ─────────────────────────────────────────────────────────────────────────────
# Pin accuracy  (GL §9)
# ─────────────────────────────────────────────────────────────────────────────
def score_pin(
    result: ResultInput,
    address_rating: AddressRating,
    address_issues: list[str],
) -> PinRating:
    if result.lat is None or result.lon is None:
        return "Wrong"

    if address_rating == "Incorrect" and "Address does not exist" in address_issues:
        return "Can't Verify"

    if result.pin_boundary_identifiable is False:
        return "Can't Verify"

    if result.pin_same_property is True:
        return "Perfect" if result.pin_precise is True else "Approximate"

    if result.pin_adjacent_property is True:
        return "Next Door"

    if result.pin_same_block is True:
        return "Approximate"

    if result.pin_same_property is False:
        return "Wrong"

    return "Can't Verify"


# ─────────────────────────────────────────────────────────────────────────────
# Assumption-flag generator  ← the key new component
# ─────────────────────────────────────────────────────────────────────────────
def build_assumption_flags(
    ctx: QueryContext,
    qi: QueryIntent,
    result: ResultInput,
    rating: RatingResult,
) -> list[AssumptionFlag]:
    """
    Return a prioritised list of things the rater must verify before
    accepting the engine's suggestion.
    """
    flags: list[AssumptionFlag] = []

    # ── Viewport / user position ──────────────────────────────────────────
    if ctx.viewport_age == "STALE":
        flags.append(AssumptionFlag(
            field="Viewport Age",
            message="Viewport is STALE → user location is the location intent, not the viewport.",
            severity="warning",
            action="Confirm user coordinates are available and accurate. "
                   "Distance demotions are measured from the user, not the viewport.",
        ))

    if ctx.user_inside_viewport is None:
        flags.append(AssumptionFlag(
            field="User Position Relative to Viewport",
            message="Unknown whether user is inside or outside the fresh viewport.",
            severity="warning",
            action="Determine if user lat/lon falls within the viewport rectangle. "
                   "If user is INSIDE: results inside viewport cannot be Bad for distance alone. "
                   "If user is OUTSIDE: all viewport results are Excellent-eligible.",
        ))

    if ctx.user_lat is None or ctx.user_lon is None:
        flags.append(AssumptionFlag(
            field="User Coordinates",
            message="User coordinates are missing.",
            severity="warning",
            action="Without user coords, distance-to-user cannot be computed. "
                   "Location intent falls back to viewport or test locale.",
        ))

    if ctx.viewport_lat is None or ctx.viewport_lon is None:
        flags.append(AssumptionFlag(
            field="Viewport Coordinates",
            message="Viewport center coordinates are missing.",
            severity="warning",
            action="Without viewport coords, viewport-based distance cannot be computed. "
                   "Relevance may be inaccurate.",
        ))

    # ── Business status ───────────────────────────────────────────────────
    if result.status == "UNKNOWN":
        flags.append(AssumptionFlag(
            field="Business Status",
            message="Business status is UNKNOWN — it has been assumed OPEN for relevance.",
            severity="error",
            action="Research whether this business is currently open, temporarily closed, "
                   "or permanently closed. Check Google Maps, official website, or social media. "
                   "If permanently closed AND open options exist nearby, relevance is capped at Acceptable.",
        ))

    if result.status in ("CLOSED", "PERMANENT_CLOSURE"):
        flags.append(AssumptionFlag(
            field="Closed/DNE Flag",
            message="Business is flagged closed or DNE. Relevance is still rated AS IF OPEN.",
            severity="info",
            action="Do NOT auto-demote to Bad. Rate relevance as if open. "
                   "If PERMANENT_CLOSURE is unexpected (open alternatives exist), max = Acceptable. "
                   "If expected (only result or all chain locations closed), Navigational/Excellent eligible.",
        ))

    # ── Address existence ─────────────────────────────────────────────────
    rt = result.result_type.upper()
    if rt == "ADDRESS":
        if result.usps_exists is None:
            flags.append(AssumptionFlag(
                field="Address Existence (USPS DPV)",
                message="USPS DPV check not run or inconclusive. Address existence is UNVERIFIED.",
                severity="error",
                action="Look up the address at https://tools.usps.com/zip-code-lookup.htm?byaddress. "
                       "DPV=Y → address exists (Correct). "
                       "DPV=N or 'N' indicator → address does not exist (Incorrect). "
                       "If the address does not exist, relevance is still rated normally but "
                       "address accuracy = Incorrect – Address does not exist, and pin = Can't Verify.",
            ))
        elif result.usps_exists is False:
            flags.append(AssumptionFlag(
                field="Address Existence (USPS DPV)",
                message="USPS DPV confirms this address does NOT exist.",
                severity="error",
                action="Address accuracy = Incorrect – Address does not exist. "
                       "Pin accuracy = Can't Verify. "
                       "Relevance may still be Excellent if this is the same address as the query "
                       "(§10.3 Query Address Does Not Exist). "
                       "Check whether the closest verified address on the same street was returned.",
            ))

    # ── Chain queries ─────────────────────────────────────────────────────
    if qi.is_chain:
        locator_url, found = get_chain_locator(qi.raw_query)
        flags.append(AssumptionFlag(
            field="Chain – Closest Location Verification",
            message=(
                f"Chain query detected. Distance rank is estimated from RETURNED results only. "
                f"Real-world rank may differ."
            ),
            severity="error",
            action=(
                f"Verify all real-world locations using the official locator: {locator_url}\n"
                f"If a closer location exists but wasn't returned, demote this result accordingly. "
                f"Reminder: chain queries are NOT navigational unless a unique location modifier "
                f"points to a single store."
            ),
        ))

    if qi.is_chain and qi.location_modifier:
        flags.append(AssumptionFlag(
            field="Chain – Location Modifier",
            message=f"Query has a location modifier: '{qi.location_modifier}'. "
                    f"User and viewport are IGNORED — rate against the named locality.",
            severity="warning",
            action="Find all chain locations within and near the named locality. "
                   "The closest within the locality = Excellent. "
                   "Next closest = Good (-1). Beyond that = Acceptable/Bad.",
        ))

    # ── Sub-brand / entity mismatch ───────────────────────────────────────
    if _is_sub_brand_mismatch(qi, result):
        flags.append(AssumptionFlag(
            field="Entity Mismatch (Sub-brand)",
            message=f"Result '{result.name}' appears to be a sub-brand of '{qi.raw_query}', "
                    f"not the same entity.",
            severity="error",
            action="Confirm whether the query intent and result are the same entity. "
                   "Sam's Club ≠ Sam's Club Pharmacy. Costco ≠ Costco Gasoline. "
                   "If different entities, relevance = Bad (§5.1.8).",
        ))

    # ── Store inside a container ──────────────────────────────────────────
    if _is_sub_business_mismatch(qi, result):
        flags.append(AssumptionFlag(
            field="Container Mismatch (Store inside queried container)",
            message=f"Query appears to be for a container ({qi.raw_query}) but result is a "
                    f"store/business inside it.",
            severity="error",
            action="Confirm: does the result show the mall/airport/etc. itself, or a store inside it? "
                   "A store inside the queried container = Bad (§5.1.8). "
                   "The container itself = potentially Navigational/Excellent.",
        ))

    # ── Address-only result for a business query ──────────────────────────
    if qi.intent_type in ("POI_OR_BUSINESS",) and rt == "ADDRESS":
        flags.append(AssumptionFlag(
            field="Address-Result for Business Query",
            message="Result is an address-type result, but the query is for a named business/POI.",
            severity="error",
            action="An address result for a business query = Bad (§5.1.8 / §10.1). "
                   "The user cannot confirm from an address alone that this is the right place.",
        ))

    # ── Business at address for an address query ──────────────────────────
    if qi.intent_type == "ADDRESS" and rt not in ("ADDRESS",):
        flags.append(AssumptionFlag(
            field="Business-Result for Address Query",
            message="Query is for an address but result is a named business/POI.",
            severity="error",
            action="A business result for an address query = Bad (§10.1). "
                   "The result title does not show the address, so the user cannot confirm accuracy.",
        ))

    # ── Street-only result for a full address query ───────────────────────
    if qi.intent_type == "ADDRESS" and rt == "ADDRESS":
        # If result name looks like just a street (no number) and query has a number
        q_has_num = bool(re.search(r"\b\d+\b", qi.raw_query))
        r_has_num = bool(re.search(r"\b\d+\b", result.name))
        if q_has_num and not r_has_num:
            flags.append(AssumptionFlag(
                field="Street-only Result for Full Address Query",
                message="Query specifies a full street number, but result appears to be the street only.",
                severity="warning",
                action="Street-only result for a specific address query = Acceptable (§10.1). "
                       "The user can find the street but not the exact address. "
                       "Cannot be Navigational unless the exact address is returned.",
            ))

    # ── Service-level mismatch ────────────────────────────────────────────
    if _is_service_level_mismatch(qi, result):
        flags.append(AssumptionFlag(
            field="Service-Level Mismatch",
            message=f"Result appears to be a lower-tier version of the queried brand (§5.28).",
            severity="warning",
            action="Initial rating for a service-level mismatch = Good (not Excellent). "
                   "Demote further based on distance if needed.",
        ))

    # ── Official name not provided ────────────────────────────────────────
    if rt != "ADDRESS" and not normalize_ws(result.official_name):
        flags.append(AssumptionFlag(
            field="Official Name",
            message="No official name was provided. Name accuracy will be 'Can't Verify'.",
            severity="info",
            action="Look up the official name on the business website, Google Maps, or Bing. "
                   "Check for misspellings, missing/incorrect LLC/Inc suffixes, holding-company names, "
                   "or former names no longer in use. Enter the official name to get a precise rating.",
        ))

    # ── Official address not provided ─────────────────────────────────────
    if rt != "ADDRESS" and not normalize_ws(result.official_address):
        flags.append(AssumptionFlag(
            field="Official Address",
            message="No official address was provided. Address accuracy will be 'Can't Verify'.",
            severity="info",
            action="Find the official address on the business website or Google Maps. "
                   "Check street number, direction (N/S/E/W), street type (St vs Blvd), "
                   "postal code, and locality. Enter it to get a precise address rating.",
        ))

    # ── Pin evidence ──────────────────────────────────────────────────────
    pin_inputs_missing = (
        result.pin_same_property is None
        and result.pin_adjacent_property is None
        and result.pin_same_block is None
    )
    if pin_inputs_missing:
        flags.append(AssumptionFlag(
            field="Pin Accuracy",
            message="No pin evidence entered. Pin accuracy defaults to 'Can't Verify'.",
            severity="info",
            action="Open the result in Google Maps or Bing Maps (use the coordinate links). "
                   "Determine if the pin:\n"
                   "  • Falls on the correct rooftop → Perfect\n"
                   "  • Is on the correct property but not the rooftop → Approximate\n"
                   "  • Is on the immediately adjacent property (same street, same side, same block) → Next Door\n"
                   "  • Is outside all of the above → Wrong\n"
                   "  • Boundary can't be determined → Can't Verify\n"
                   "For campuses/multi-rooftop: pin anywhere within the full parcel = Perfect.",
        ))

    # ── Result coordinates missing ────────────────────────────────────────
    if result.lat is None or result.lon is None:
        flags.append(AssumptionFlag(
            field="Result Coordinates",
            message="Result lat/lon not provided. Distance cannot be computed and pin = Wrong.",
            severity="warning",
            action="Enter the result coordinates (visible in the TryRating interface) "
                   "so distance ranking and pin evaluation can work correctly.",
        ))

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# Comment builder
# ─────────────────────────────────────────────────────────────────────────────
def build_comment(
    ctx: QueryContext,
    qi: QueryIntent,
    result: ResultInput,
    rating: RatingResult,
) -> str:
    parts: list[str] = []

    parts.append(f"User intent: {qi.raw_query}.")

    basis = determine_location_basis(ctx, qi)
    parts.append(f"Location basis: {basis}.")

    rel_head = f"[Relevance: {rating.relevance}"
    if rating.demotion_reasons:
        rel_head += " – " + ", ".join(rating.demotion_reasons)
    rel_head += "]"
    parts.append(rel_head)

    if rating.relevance_notes:
        parts.append(" ".join(rating.relevance_notes))

    if rating.business_closed_or_dne:
        parts.append(
            "Business/POI Closed or DNE flag selected; relevance rated as if open per GL §4.2."
        )

    parts.append(f"[Name: {rating.name_rating}]")
    parts.append(f"[Address: {rating.address_rating}]")
    if rating.address_issues:
        parts.append(f"Address issue(s): {', '.join(rating.address_issues)}.")

    parts.append(f"[Pin: {rating.pin_rating}]")

    if qi.is_chain:
        locator_url, _ = get_chain_locator(qi.raw_query)
        parts.append(
            f"Chain query: verify all real-world locations at the official locator before finalising distance rank: {locator_url}"
        )

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────
def score_result(
    ctx: QueryContext,
    result: ResultInput,
    all_results: list[ResultInput],
) -> RatingResult:
    qi = classify_query(ctx.query)
    nav = has_navigational_result(qi, all_results)

    # ── Flag: unexpected language/script → lock everything
    if is_unexpected_language_or_script(result.name, ctx.locale):
        dummy = RatingResult(
            has_navigational_result=nav,
            unexpected_language_or_script=True,
            business_closed_or_dne=False,
            relevance="Bad",
            relevance_notes=["Result name/title is in unexpected language or script; all other ratings locked."],
            demotion_reasons=[],
            name_rating="n/a",
            address_rating="n/a",
            address_issues=[],
            pin_rating="n/a",
            assumption_flags=[
                AssumptionFlag(
                    field="Unexpected Language / Script",
                    message="Result name is in an unexpected language or script for this locale.",
                    severity="error",
                    action="Check the 'Result name/title is in unexpected language or script' box. "
                           "All other ratings are locked and not applicable.",
                )
            ],
            comment="Unexpected language/script flag set; remaining ratings not applicable.",
        )
        return dummy

    business_closed_or_dne = result.status in ("CLOSED", "PERMANENT_CLOSURE")

    relevance, relevance_notes, demotion_reasons = score_relevance(
        ctx=ctx,
        qi=qi,
        result=result,
        all_results=all_results,
        has_nav_result=nav,
    )

    name_rating                    = score_name(result)
    address_rating, address_issues = score_address(result)
    pin_rating                     = score_pin(result, address_rating, address_issues)

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
        assumption_flags=[],
        comment="",
    )
    out.assumption_flags = build_assumption_flags(ctx, qi, result, out)
    out.comment = build_comment(ctx, qi, result, out)
    return out
