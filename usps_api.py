from __future__ import annotations

import re
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
import streamlit as st
from utils.sql_utility import no_specials
from utils.streamlit_utility import in_streamlit

import requests
from dotenv import load_dotenv


load_dotenv()


class USPSApiError(RuntimeError):
    pass


@dataclass
class AddressLookupResult:
    input_street: str
    input_city: str
    input_state: str
    input_zip: str | None

    exists: bool
    standardized_street: str | None
    standardized_city: str | None
    standardized_state: str | None
    zip5: str | None
    zip4: str | None
    delivery_point_zip: str | None

    dpv_accessible: bool
    dpv_value: str | None
    dpv_field_path: str | None

    raw_response: Dict[str, Any]
    error: str | None
    
    def valid(self):
        return str(self.dpv_value).strip().upper() == "Y"


state_acronyms = {
    "AL":"Alabama",
    "AK":"Alaska",
    "AS":"American Samoa",
    "AZ":"Arizona",
    "AR":"Arkansas",
    "CA":"California",
    "CO":"Colorado",
    "CT":"Connecticut",
    "DE":"Delaware",
    "DC":"District of Columbia",
    "FM":"Federated States of Micronesia",
    "FL":"Florida",
    "GA":"Georgia",
    "GU":"Guam",
    "HI":"Hawaii",
    "ID":"Idaho",
    "IL":"Illinois",
    "IN":"Indiana",
    "IA":"Iowa",
    "KS":"Kansas",
    "KY":"Kentucky",
    "LA":"Louisiana",
    "ME":"Maine",
    "MH":"Marshall Islands",
    "MD":"Maryland",
    "MA":"Massachusetts",
    "MI":"Michigan",
    "MN":"Minnesota",
    "MS":"Mississippi",
    "MO":"Missouri",
    "MT":"Montana",
    "NE":"Nebraska",
    "NV":"Nevada",
    "NH":"New Hampshire",
    "NJ":"New Jersey",
    "NM":"New Mexico",
    "NY":"New York",
    "NC":"North Carolina",
    "ND":"North Dakota",
    "MP":"Northern Mariana Islands",
    "OH":"Ohio",
    "OK":"Oklahoma",
    "OR":"Oregon",
    "PW":"Palau",
    "PA":"Pennsylvania",
    "PR":"Puerto Rico",
    "RI":"Rhode Island",
    "SC":"South Carolina",
    "SD":"South Dakota",
    "TN":"Tennessee",
    "TX":"Texas",
    "UT":"Utah",
    "VT":"Vermont",
    "VI":"Virgin Islands",
    "VA":"Virginia",
    "WA":"Washington",
    "WV":"West Virginia",
    "WI":"Wisconsin",
    "WY":"Wyoming",
    "AA":"Armed Forces Americas",
    "AE":"Armed Forces Africa",
    "AE":"Armed Forces Canada",
    "AE":"Armed Forces Europe",
    "AE":"Armed Forces Middle East",
    "AP":"Armed Forces Pacific",
}
def valid_state(state_in: str) -> str:
    state_in = no_specials(state_in.lower().strip())
    sa_l = {no_specials(k.lower().strip()): no_specials(v.lower().strip()) for k, v in state_acronyms.items()}
    if len(state_in) > 2:
        # full state name passed
        as_l = {v: k for k, v in sa_l.items()}
        state = as_l.get(state_in, "")
        return state.upper()
    elif len(state_in) == 2:
        # state acronym
        state = sa_l.get(state_in, "")
        return (state_in if state else state).upper()
    return ""
    

def _get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise USPSApiError(f"Missing required environment variable: {name}")
    return value


def _base_url() -> str:
    use_tem = os.getenv("USPS_USE_TEM", "true").strip().lower() in {"1", "true", "yes", "y"}
    # USPS says testing can be done by switching apis.usps.com to apis-tem.usps.com.
    return "https://apis-tem.usps.com" if use_tem else "https://apis.usps.com"


def get_oauth_token(timeout: int = 30) -> str:
    client_id = _get_env("USPS_CLIENT_ID")
    client_secret = _get_env("USPS_CLIENT_SECRET")

    url = f"{_base_url()}/oauth2/v3/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    response = requests.post(url, data=data, timeout=timeout)
    if not response.ok:
        raise USPSApiError(
            f"OAuth token request failed: {response.status_code} {response.text[:500]}"
        )

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise USPSApiError(f"OAuth response did not include access_token: {payload}")

    return token


def _find_first_matching_field(obj: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Search recursively for likely DPV-related keys.
    Returns (path, value_as_string).
    """
    candidate_keys = {
        "DPVConfirmation",
        "dpvConfirmationIndicator",
        "dpv_confirmation_indicator",
        "dpvIndicator",
        "dpv_indicator",
        "deliveryPointValidation",
        "delivery_point_validation",
        "DPVConfirmationIndicator",
        "DPVIndicator",
    }

    def walk(node: Any, path: str) -> Tuple[Optional[str], Optional[str]]:
        if isinstance(node, dict):
            for key, value in node.items():
                next_path = f"{path}.{key}" if path else key
                if key in candidate_keys:
                    return next_path, None if value is None else str(value)
                found_path, found_value = walk(value, next_path)
                if found_path:
                    return found_path, found_value
        elif isinstance(node, list):
            for i, value in enumerate(node):
                next_path = f"{path}[{i}]"
                found_path, found_value = walk(value, next_path)
                if found_path:
                    return found_path, found_value
        return None, None

    return walk(obj, "")


def _extract_standardized_fields(payload: Dict[str, Any]) -> Tuple[
    Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
]:
    """
    Best-effort extraction because USPS response shape may vary by environment/version.
    """
    # Common likely locations / names:
    possible_street_keys = ["streetAddress", "deliveryAddress", "addressLine1", "address1"]
    possible_city_keys = ["city", "cityName"]
    possible_state_keys = ["state", "stateCode"]
    possible_zip5_keys = ["ZIPCode", "zipCode", "zip5"]
    possible_zip4_keys = ["ZIPPlus4", "zipPlus4", "zip4"]
    possible_delivery_point_keys = ["deliveryPointZIP", "deliveryPointZip", "delivery_point_zip"]

    def find_value(node: Any, candidate_keys: list[str]) -> Optional[str]:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in candidate_keys and value not in (None, ""):
                    return str(value)
                nested = find_value(value, candidate_keys)
                if nested is not None:
                    return nested
        elif isinstance(node, list):
            for item in node:
                nested = find_value(item, candidate_keys)
                if nested is not None:
                    return nested
        return None

    street = find_value(payload, possible_street_keys)
    city = find_value(payload, possible_city_keys)
    state = find_value(payload, possible_state_keys)
    zip5 = find_value(payload, possible_zip5_keys)
    zip4 = find_value(payload, possible_zip4_keys)
    delivery_point_zip = find_value(payload, possible_delivery_point_keys)

    return street, city, state, zip5, zip4, delivery_point_zip


def lookup_address(
    street: str,
    city: str,
    state: str,
    zip_code: str | None = None,
    secondary_address: str | None = None,
    timeout: int = 30,
) -> AddressLookupResult:
    """
    USPS v3 Address API lookup.

    Official examples show GET /addresses/v3/address with query parameters such as:
    streetAddress, secondaryAddress, city, state, ZIPCode, ZIPPlus4.
    """
    token = get_oauth_token(timeout=timeout)
    
    state = valid_state(state)
    
    (st.write if in_streamlit() else print)(f"Lookup: {street=}, {city=}, {state=}, {zip_code=}, {secondary_address=}, {timeout=}")

    params: Dict[str, str] = {
        "streetAddress": street.strip(),
        "city": city.strip(),
        "state": state.strip().upper(),
    }
    if zip_code and zip_code.strip():
        params["ZIPCode"] = zip_code.strip()
    if secondary_address and secondary_address.strip():
        params["secondaryAddress"] = secondary_address.strip()

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token}",
    }

    url = f"{_base_url()}/addresses/v3/address"
    response = requests.get(url, headers=headers, params=params, timeout=timeout)

    if response.status_code == 404:
        return AddressLookupResult(
            input_street=street,
            input_city=city,
            input_state=state,
            input_zip=zip_code,
            exists=False,
            standardized_street=None,
            standardized_city=None,
            standardized_state=None,
            zip5=None,
            zip4=None,
            delivery_point_zip=None,
            dpv_accessible=False,
            dpv_value=None,
            dpv_field_path=None,
            raw_response={},
            error="USPS returned 404 / address not found.",
        )

    if not response.ok:
        return AddressLookupResult(
            input_street=street,
            input_city=city,
            input_state=state,
            input_zip=zip_code,
            exists=False,
            standardized_street=None,
            standardized_city=None,
            standardized_state=None,
            zip5=None,
            zip4=None,
            delivery_point_zip=None,
            dpv_accessible=False,
            dpv_value=None,
            dpv_field_path=None,
            raw_response={},
            error=f"USPS API error: {response.status_code} {response.text[:500]}",
        )

    payload = response.json()

    standardized_street, standardized_city, standardized_state, zip5, zip4, delivery_point_zip = (
        _extract_standardized_fields(payload)
    )

    dpv_field_path, dpv_value = _find_first_matching_field(payload)

    # Best-effort existence rule:
    # If USPS returns a successful payload with standardized address or ZIP data, treat it as existing.
    exists = any([
        standardized_street,
        standardized_city,
        standardized_state,
        zip5,
        zip4,
        delivery_point_zip,
    ])

    return AddressLookupResult(
        input_street=street,
        input_city=city,
        input_state=state,
        input_zip=zip_code,
        exists=exists,
        standardized_street=standardized_street,
        standardized_city=standardized_city,
        standardized_state=standardized_state,
        zip5=zip5,
        zip4=zip4,
        delivery_point_zip=delivery_point_zip,
        dpv_accessible=dpv_field_path is not None,
        dpv_value=dpv_value,
        dpv_field_path=dpv_field_path,
        raw_response=payload,
        error=None if exists else "USPS returned a successful response but no recognizable address fields were found.",
    )
    
    
def parse_usps_result(result: Any) -> dict:
    dpv = (getattr(result, "dpv_value", "") or "").strip().upper()
    dpv_accessible = bool(getattr(result, "dpv_accessible", False))

    if dpv_accessible:
        exists = True if dpv == "Y" else False if dpv == "N" else None
    else:
        exists = None

    return {
        "ok": True,
        "valid": bool(result.valid()),
        "exists": exists,
        "dpv_value": dpv or None,
        "dpv_accessible": dpv_accessible,
        "standardized_street": getattr(result, "standardized_street", None),
        "standardized_city": getattr(result, "standardized_city", None),
        "standardized_state": getattr(result, "standardized_state", None),
        "zip5": getattr(result, "zip5", None),
        "zip4": getattr(result, "zip4", None),
        "error": getattr(result, "error", None),
        "raw_response": getattr(result, "raw_response", None),
    }
    

def parse_simple_address(full_address: str) -> dict[str, str]:
    """
    Best-effort parser for US-style addresses.
    Expected rough input:
        226300 Bluegill Ave, Schofield, WI 54476
    """
    out = {"street": "", "city": "", "state": "", "zip": ""}
    if not full_address.strip():
        (st.write if in_streamlit() else print)(f"A==\n\t{out=}")
        return out

    parts = [p.strip() for p in full_address.split(",")]
    if len(parts) >= 1:
        out["street"] = parts[0]

    if len(parts) >= 2:
        out["city"] = parts[1]

    if len(parts) >= 3:
        tail = " ".join(parts[2:]).replace(",", "")
        m = re.match(r"([A-Za-z]{2})\s+(\d{5})", tail)
        if m:
            out["state"] = m.group(1)
            out["zip"] = m.group(2)
        else:
            out["state"] = tail

    out["state"] = valid_state(out["state"])
    (st.write if in_streamlit() else print)(f"B==\n\t{out=}")
    return out


if __name__ == "__main__":
    def test0():
        a1 = dict(
            street="133 Springhill Ave",
            city="Bowling Green",
            state="KY",
            zip_code="42101"
        )
        a2 = dict(
            street="3713 silver oak ct",
            city="tulsa",
            state="ok",
            zip_code="74107"
        )
        a3 = dict(
            street="379 us highway 285",
            city="fairplay",
            state="co",
            zip_code="80440"
        )
        a4 = dict(
            street="9201 huron st",
            city="thornton",
            state="co",
            zip_code="80260"
        )
        for a in [a1, a2, a3, a4]:
            result = lookup_address(**a)
            print(f"\t==>{result.valid()}")
            print(asdict(result))
            
    def test1():
        a1 = "133 springhill ave., bowling green, ky, 42101"
        print(parse_simple_address(a1))
        
    test1()