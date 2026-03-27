from __future__ import annotations

import re
from dataclasses import asdict
from typing import Optional

import pandas as pd
import streamlit as st

from usps_api import USPSApiError, lookup_address


st.set_page_config(page_title="USPS Address Lookup", layout="wide")
st.title("USPS Address Lookup")
st.caption("Uses USPS Developer API, not browser automation.")


# -----------------------------
# Session state initialization
# -----------------------------
DEFAULT_FIELDS = {
    "street": "",
    "city": "",
    "state": "",
    "zip_code": "",
    "secondary": "",
}

if "results" not in st.session_state:
    st.session_state.results = []

for k, v in DEFAULT_FIELDS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -----------------------------
# Normalization / comparison
# -----------------------------
ABBREV_MAP = {
    "ST": "STREET",
    "STREET": "STREET",
    "RD": "ROAD",
    "ROAD": "ROAD",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "AVENUE": "AVENUE",
    "BLVD": "BOULEVARD",
    "BOULEVARD": "BOULEVARD",
    "DR": "DRIVE",
    "DRIVE": "DRIVE",
    "LN": "LANE",
    "LANE": "LANE",
    "CT": "COURT",
    "COURT": "COURT",
    "CIR": "CIRCLE",
    "CIRCLE": "CIRCLE",
    "PKWY": "PARKWAY",
    "PARKWAY": "PARKWAY",
    "PL": "PLACE",
    "PLACE": "PLACE",
    "TER": "TERRACE",
    "TERRACE": "TERRACE",
    "HWY": "HIGHWAY",
    "HIGHWAY": "HIGHWAY",
    "N": "NORTH",
    "S": "SOUTH",
    "E": "EAST",
    "W": "WEST",
    "NE": "NORTHEAST",
    "NW": "NORTHWEST",
    "SE": "SOUTHEAST",
    "SW": "SOUTHWEST",
    "APT": "APARTMENT",
    "STE": "SUITE",
    "UNIT": "UNIT",
}


def clean_text(value: Optional[str]) -> str:
    value = str(value or "").upper().strip()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_tokens(value: Optional[str]) -> list[str]:
    cleaned = clean_text(value)
    if not cleaned:
        return []
    tokens = cleaned.split()
    return [ABBREV_MAP.get(tok, tok) for tok in tokens]


def normalize_joined(value: Optional[str]) -> str:
    return "".join(normalize_tokens(value))


def assess_address_match(
    input_street: Optional[str],
    input_city: Optional[str],
    input_state: Optional[str],
    input_zip: Optional[str],
    result_street: Optional[str],
    result_city: Optional[str],
    result_state: Optional[str],
    result_zip5: Optional[str],
    result_zip4: Optional[str],
) -> dict:
    input_street_tokens = normalize_tokens(input_street)
    result_street_tokens = normalize_tokens(result_street)

    input_city_tokens = normalize_tokens(input_city)
    result_city_tokens = normalize_tokens(result_city)

    input_street_joined = "".join(input_street_tokens)
    result_street_joined = "".join(result_street_tokens)

    input_city_joined = "".join(input_city_tokens)
    result_city_joined = "".join(result_city_tokens)

    input_state_clean = clean_text(input_state)
    result_state_clean = clean_text(result_state)

    input_zip_clean = clean_text(input_zip)
    result_zip5_clean = clean_text(result_zip5)

    notes: list[str] = []

    street_exact = input_street_tokens == result_street_tokens
    street_loose = input_street_joined == result_street_joined

    city_exact = input_city_tokens == result_city_tokens
    city_loose = input_city_joined == result_city_joined

    state_match = (not input_state_clean) or (input_state_clean == result_state_clean)
    zip5_match = (not input_zip_clean) or (input_zip_clean == result_zip5_clean)

    if street_exact:
        notes.append("Street matches after normalization.")
    elif street_loose:
        notes.append("Street appears equivalent after abbreviation/spacing normalization.")
    else:
        notes.append("Street differs from returned result.")

    if city_exact:
        notes.append("City matches after normalization.")
    elif city_loose:
        notes.append("City appears equivalent after spacing normalization.")
    else:
        notes.append("City differs from returned result.")

    if state_match:
        notes.append("State matches.")
    else:
        notes.append("State differs from returned result.")

    if input_zip_clean:
        if zip5_match:
            notes.append("ZIP5 matches.")
        else:
            notes.append("ZIP5 differs from returned result.")

    if result_zip4:
        notes.append(f"USPS returned ZIP+4 suffix: {result_zip4}")

    if street_exact and city_exact and state_match and zip5_match:
        status = "Exact normalized match"
    elif street_loose and city_loose and state_match and zip5_match:
        status = "Equivalent match"
    elif (street_loose or street_exact) and (city_loose or city_exact) and state_match:
        status = "Close match"
    else:
        status = "Returned address differs"

    return {
        "status": status,
        "notes": notes,
    }


def clear_fields():
    for k, v in DEFAULT_FIELDS.items():
        st.session_state[k] = v


# -----------------------------
# Input section
# -----------------------------
st.subheader("Inputs")

with st.form("lookup_form", clear_on_submit=False):
    c1, c2 = st.columns(2)

    with c1:
        st.text_input("Street Address", key="street")
        st.text_input("City", key="city")

    with c2:
        st.text_input("State", key="state", max_chars=2)
        st.text_input("ZIP Code", key="zip_code")

    st.text_input("Apt / Suite / Other", key="secondary")

    b1, b2 = st.columns([1, 1])
    with b1:
        submitted = st.form_submit_button("Lookup")
    with b2:
        cleared = st.form_submit_button("Clear Fields")

if cleared:
    clear_fields()
    st.rerun()

if submitted:
    if not st.session_state.street or not st.session_state.city or not st.session_state.state:
        st.error("Street, city, and state are required.")
    else:
        try:
            result = lookup_address(
                street=st.session_state.street,
                city=st.session_state.city,
                state=st.session_state.state,
                zip_code=st.session_state.zip_code or None,
                secondary_address=st.session_state.secondary or None,
            )

            match_info = assess_address_match(
                input_street=result.input_street,
                input_city=result.input_city,
                input_state=result.input_state,
                input_zip=result.input_zip,
                result_street=result.standardized_street,
                result_city=result.standardized_city,
                result_state=result.standardized_state,
                result_zip5=result.zip5,
                result_zip4=result.zip4,
            )

            result_dict = asdict(result)
            result_dict["address_match_status"] = match_info["status"]
            result_dict["address_match_notes"] = match_info["notes"]

            st.session_state.results.append(result_dict)

        except USPSApiError as e:
            st.error(str(e))
        except Exception as e:
            st.exception(e)


# -----------------------------
# Results section
# -----------------------------
st.subheader("Results")

if st.session_state.results:
    latest = st.session_state.results[-1]

    left, right = st.columns(2)

    with left:
        st.markdown("**Returned Result**")
        st.write(f"Street: {latest.get('standardized_street') or '-'}")
        st.write(f"City: {latest.get('standardized_city') or '-'}")
        st.write(f"State: {latest.get('standardized_state') or '-'}")
        st.write(f"ZIP5: {latest.get('zip5') or '-'}")
        st.write(f"ZIP4: {latest.get('zip4') or '-'}")
        st.write(f"Delivery Point ZIP: {latest.get('delivery_point_zip') or '-'}")

    with right:
        st.markdown("**Lookup Status**")
        st.write(f"Address Exists: {'Yes' if latest.get('exists') else 'No'}")
        st.write(f"DPV Indicator: {latest.get('dpv_value') or 'Not returned'}")
        st.write(f"DPV Accessible: {'Yes' if latest.get('dpv_accessible') else 'No'}")
        st.write(f"Address Match Status: {latest.get('address_match_status') or '-'}")
        if latest.get("error"):
            st.write(f"Error: {latest['error']}")

    if latest.get("address_match_notes"):
        with st.expander("Address Match Details", expanded=True):
            for note in latest["address_match_notes"]:
                st.write(f"- {note}")

    st.markdown("**Lookup History**")
    df = pd.DataFrame([
        {
            "input_street": r.get("input_street"),
            "input_city": r.get("input_city"),
            "input_state": r.get("input_state"),
            "input_zip": r.get("input_zip"),
            "exists": r.get("exists"),
            "standardized_street": r.get("standardized_street"),
            "standardized_city": r.get("standardized_city"),
            "standardized_state": r.get("standardized_state"),
            "zip5": r.get("zip5"),
            "zip4": r.get("zip4"),
            "dpv_indicator": r.get("dpv_value"),
            "dpv_accessible": r.get("dpv_accessible"),
            "address_match_status": r.get("address_match_status"),
            "error": r.get("error"),
        }
        for r in st.session_state.results
    ])
    st.dataframe(df, use_container_width=True)

    with st.expander("Latest raw USPS response"):
        st.json(latest.get("raw_response", {}))

    if st.button("Clear Results"):
        st.session_state.results = []
        st.rerun()

else:
    st.info("No lookups yet.")