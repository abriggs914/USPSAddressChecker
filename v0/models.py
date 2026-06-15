from dataclasses import dataclass, field
from typing import Optional, Literal, List

ViewportAge = Literal["FRESH", "STALE"]
ClosedStatus = Literal["OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"]
Relevance = Literal["Navigational", "Excellent", "Good", "Acceptable", "Bad"]
NameRating = Literal["Correct", "Partially Correct", "Incorrect", "Can't Verify", "n/a"]
AddressRating = Literal["Correct", "Correct with Formatting Issue", "Incorrect", "Can't Verify", "n/a"]
PinRating = Literal["Perfect", "Approximate", "Next Door", "Wrong", "Can't Verify", "n/a"]

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

@dataclass
class ResultInput:
    name: str
    address_line: str
    classification: str
    type: str
    status: ClosedStatus
    distance_to_user_km: Optional[float]
    distance_to_viewport_km: Optional[float]
    lat: Optional[float]
    lon: Optional[float]
    official_name: str = ""
    official_address: str = ""
    usps_exists: Optional[bool] = None
    usps_valid: Optional[bool] = None
    usps_match_status: str = ""
    usps_match_notes: List[str] = field(default_factory=list)

@dataclass
class RatingDecision:
    has_navigational_result: bool
    unexpected_language: bool
    closed_or_dne: bool
    relevance: Relevance
    relevance_reasons: List[str]
    demotion_reasons: List[str]
    name_rating: NameRating
    address_rating: AddressRating
    address_issues: List[str]
    pin_rating: PinRating
    comment: str