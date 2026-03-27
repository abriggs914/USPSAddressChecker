from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
import streamlit as st

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
        return self.dpv_value == "Y"


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
    
    st.write(f"Lookup: {street=}, {city=}, {state=}, {zip_code=}, {secondary_address=}, {timeout=}")

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


if __name__ == "__main__":
    result = lookup_address(
        street="133 Springhill Ave",
        city="Bowling Green",
        state="KY",
        zip_code="42101",
    )
    print(asdict(result))