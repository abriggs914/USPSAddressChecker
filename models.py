# models.py
"""
Shared type aliases and data-classes.
The rating engine (rating_engine.py) owns the canonical definitions;
import from there when possible.  This file re-exports them for
convenience and documents the contract.
"""
from rating_engine import (
    # Type aliases
    ViewportAge,
    LocationBasis,
    RelevanceLabel,
    NameRating,
    AddressRating,
    PinRating,
    IntentType,
    ClosedStatus,
    AssumptionSeverity,
    # Data-classes
    AssumptionFlag,
    QueryContext,
    ResultInput,
    QueryIntent,
    RatingResult,
)

__all__ = [
    "ViewportAge",
    "LocationBasis",
    "RelevanceLabel",
    "NameRating",
    "AddressRating",
    "PinRating",
    "IntentType",
    "ClosedStatus",
    "AssumptionSeverity",
    "AssumptionFlag",
    "QueryContext",
    "ResultInput",
    "QueryIntent",
    "RatingResult",
]
