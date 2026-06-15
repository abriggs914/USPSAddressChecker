# streamlit_app.py
from __future__ import annotations

import math
import re
from typing import Any, Optional
from dataclasses import asdict

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# ---- Your USPS imports here ----
from usps_api import lookup_address, USPSApiError, parse_simple_address
from utils.location_utility import geocode_address, resolve_location

from rating_engine import (
    QueryContext,
    ResultInput,
    score_result,
    google_maps_link,
    google_maps_address_link,
    bing_maps_link,
    bing_maps_address_link,
    get_chain_locator,
)

# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Maps Search Rating Sandbox",
    page_icon="🗺️",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .small-muted { color: #64748b; font-size: 12px; }
        .metric-box {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px 14px;
            background: #ffffff;
        }
        .decision-box {
            border: 1px solid #dbeafe;
            background: #f8fbff;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .code-ish {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 13px;
        }
        .blurb-box {
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 14px;
            background: #f8fafc;
            white-space: pre-wrap;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 13px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
@st.cache_resource
def get_geolocator() -> Nominatim:
    return Nominatim(user_agent="maps_search_rating_sandbox")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))


def assess_address_match(
    input_addr: str,
    usps_street: str,
    input_city: str,
    usps_city: str,
    input_state: str,
    usps_state: str,
    input_zip: str,
    usps_zip5: str,
) -> dict:
    """
    Light local comparison helper.
    Replace with your richer version if you already have one.
    """
    def nk(s: str) -> str:
        s = (s or "").strip().lower()
        s = s.replace(".", "").replace(",", "")
        s = re.sub(r"\s+", " ", s)
        return s

    exact = (
        nk(input_addr) == nk(usps_street)
        and nk(input_city) == nk(usps_city)
        and nk(input_state) == nk(usps_state)
        and (not input_zip or nk(input_zip) == nk(usps_zip5))
    )
    if exact:
        return {"status": "Exact normalized match", "notes": []}

    close = (
        nk(input_city) == nk(usps_city)
        and nk(input_state) == nk(usps_state)
        and bool(usps_street)
    )
    if close:
        return {"status": "Close match", "notes": ["USPS standardized the street line."]}

    return {"status": "Mismatch", "notes": ["Input address differs from USPS normalized form."]}


@st.cache_data(show_spinner=False)
def verify_address_with_usps(street: str, city: str, state: str, zip_code: str = "", secondary: str = "") -> dict:
    """
    Replace lookup_address(...) with your real USPS implementation.

    Expected semantics:
    - 'exists' comes from DPV Y/N when accessible
    - 'valid' is supporting metadata only
    """
    try:
        result = lookup_address(
            street=street,
            city=city,
            state=state,
            zip_code=zip_code or None,
            secondary_address=secondary or None,
        )

        dpv = (getattr(result, "dpv_value", "") or "").strip().upper()
        dpv_accessible = bool(getattr(result, "dpv_accessible", False))
        if dpv_accessible:
            exists = True if dpv == "Y" else False if dpv == "N" else None
        else:
            exists = None

        match_info = assess_address_match(
            input_addr=street,
            usps_street=getattr(result, "standardized_street", "") or "",
            input_city=city,
            usps_city=getattr(result, "standardized_city", "") or "",
            input_state=state,
            usps_state=getattr(result, "standardized_state", "") or "",
            input_zip=zip_code or "",
            usps_zip5=getattr(result, "zip5", "") or "",
        )

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
            "match_status": match_info["status"],
            "match_notes": match_info["notes"],
            "error": getattr(result, "error", None),
            "raw_response": getattr(result, "raw_response", {}),
        }
    except Exception as e:
        st.error(e)
        return {
            "ok": False,
            "valid": False,
            "exists": None,
            "dpv_value": None,
            "dpv_accessible": False,
            "standardized_street": None,
            "standardized_city": None,
            "standardized_state": None,
            "zip5": None,
            "zip4": None,
            "match_status": "USPS API error",
            "match_notes": [],
            "error": str(e),
            "raw_response": {},
        }


def result_status_from_ui(raw_status: str) -> str:
    s = (raw_status or "OPEN").strip().upper()
    if s in {"OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"}:
        return s
    return "UNKNOWN"


def format_bool(v: Optional[bool]) -> str:
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return "Unknown"


def build_result_input_from_ui(d: dict) -> ResultInput:
    return ResultInput(
        name=d["name"],
        address=d["address"],
        classification=d["classification"],
        result_type=d["result_type"],
        status=result_status_from_ui(d["status"]),
        distance_to_user_km=d.get("distance_to_user_km"),
        distance_to_viewport_km=d.get("distance_to_viewport_km"),
        lat=d.get("resolved_lat"),
        lon=d.get("resolved_lon"),
        official_name=d.get("official_name", ""),
        official_address=d.get("official_address", ""),
        usps_valid=d.get("usps", {}).get("ok"),
        usps_exists=d.get("usps", {}).get("exists"),
        usps_match_status=d.get("usps", {}).get("match_status", ""),
        usps_match_notes=d.get("usps", {}).get("match_notes", []),
        pin_same_property=d.get("pin_same_property"),
        pin_same_block=d.get("pin_same_block"),
        pin_adjacent_property=d.get("pin_adjacent_property"),
        pin_precise=d.get("pin_precise"),
        pin_boundary_identifiable=d.get("pin_boundary_identifiable"),
    )


# def decision_to_blurb(result_name: str, decision) -> str:
#     lines = []
#     lines.append(f"Result: {result_name or '(untitled result)'}")
#     lines.append(f"Navigational result for query: {'Yes' if decision.has_navigational_result else 'No'}")
#     lines.append(f"Unexpected language/script: {'Yes' if decision.unexpected_language_or_script else 'No'}")
#     lines.append(f"Business/POI closed or does not exist: {'Yes' if decision.business_closed_or_dne else 'No'}")
#     lines.append(f"Relevance: {decision.relevance}")
#     if decision.demotion_reasons:
#         lines.append(f"Demotion reasons: {', '.join(decision.demotion_reasons)}")
#     lines.append(f"Name Accuracy: {decision.name_rating}")
#     lines.append(f"Address Accuracy: {decision.address_rating}")
#     if decision.address_issues:
#         lines.append(f"Address Issues: {', '.join(decision.address_issues)}")
#     lines.append(f"Pin Accuracy: {decision.pin_rating}")
#     lines.append("")
#     lines.append("Comment:")
#     lines.append(decision.comment)
#     return "\n".join(lines)


def decision_to_blurb(result_name: str, decision, query: str = "", locator_url: str = "", is_chain: bool = False) -> str:
    lines = []
    lines.append(f"Result: {result_name or '(untitled result)'}")
    lines.append(f"Navigational result for query: {'Yes' if decision.has_navigational_result else 'No'}")
    lines.append(f"Unexpected language/script: {'Yes' if decision.unexpected_language_or_script else 'No'}")
    lines.append(f"Business/POI closed or does not exist: {'Yes' if decision.business_closed_or_dne else 'No'}")
    lines.append(f"Relevance: {decision.relevance}")
    if decision.demotion_reasons:
        lines.append(f"Demotion reasons: {', '.join(decision.demotion_reasons)}")
    lines.append(f"Name Accuracy: {decision.name_rating}")
    lines.append(f"Address Accuracy: {decision.address_rating}")
    if decision.address_issues:
        lines.append(f"Address Issues: {', '.join(decision.address_issues)}")
    lines.append(f"Pin Accuracy: {decision.pin_rating}")
    lines.append("")
    lines.append("Comment:")
    lines.append(decision.comment)

    if is_chain and locator_url:
        lines.append("")
        lines.append("Verification:")
        lines.append(
            f"This is a chain query, so distance should be treated as critical. "
            f"Even if this result appears strong, verify whether a closer qualifying location exists: {locator_url}"
        )

    return "\n".join(lines)


def render_location_links(title: str, lat: Optional[float], lon: Optional[float], address: str = "") -> None:
    st.markdown(f"**{title} Links**")
    cols = st.columns(4)

    if lat is not None and lon is not None:
        cols[0].markdown(f"[Google Maps coord]({google_maps_link(lat, lon)})")
        cols[1].markdown(f"[Bing Maps coord]({bing_maps_link(lat, lon)})")
    else:
        cols[0].markdown("_Google coord unavailable_")
        cols[1].markdown("_Bing coord unavailable_")

    if address.strip():
        cols[2].markdown(f"[Google Maps address]({google_maps_address_link(address)})")
        cols[3].markdown(f"[Bing Maps address]({bing_maps_address_link(address)})")
    else:
        cols[2].markdown("_Google address unavailable_")
        cols[3].markdown("_Bing address unavailable_")


def build_map_df(
    viewport_lat: Optional[float],
    viewport_lon: Optional[float],
    user_lat: Optional[float],
    user_lon: Optional[float],
    results: list[dict],
) -> pd.DataFrame:
    rows = []
    if viewport_lat is not None and viewport_lon is not None:
        rows.append(
            {
                "kind": "Viewport",
                "label": "Viewport",
                "lat": viewport_lat,
                "lon": viewport_lon,
            }
        )
    if user_lat is not None and user_lon is not None:
        rows.append(
            {
                "kind": "User",
                "label": "User",
                "lat": user_lat,
                "lon": user_lon,
            }
        )
    for idx, r in enumerate(results, start=1):
        if r.get("resolved_lat") is not None and r.get("resolved_lon") is not None:
            rows.append(
                {
                    "kind": "Result",
                    "label": f"{idx}. {r.get('name') or f'Result {idx}'}",
                    "lat": r["resolved_lat"],
                    "lon": r["resolved_lon"],
                }
            )
    return pd.DataFrame(rows)


def add_viewport_rectangle(
    m,
    center_lat,
    center_lon,
    width_m=1000,
    height_m=800,
    color="#3b82f6",
    fill=True,
    fill_opacity=0.25,
    tooltip="Viewport Area"
):
    # Approximate conversions
    lat_deg_per_m = 1 / 111_320
    lon_deg_per_m = 1 / (111_320 * math.cos(math.radians(center_lat)))

    half_height_deg = (height_m / 2) * lat_deg_per_m
    half_width_deg = (width_m / 2) * lon_deg_per_m

    south = center_lat - half_height_deg
    north = center_lat + half_height_deg
    west = center_lon - half_width_deg
    east = center_lon + half_width_deg

    folium.Rectangle(
        bounds=[[south, west], [north, east]],
        color=color,
        weight=2,
        fill=fill,
        fill_color=color,
        fill_opacity=fill_opacity,
        tooltip=tooltip
    ).add_to(m)
    
    return dict(
        south=south,
        north=north,
        west=west,
        east=east
    )


def point_in_bbox(lat: Optional[float], lon: Optional[float], south: float, north: float, west: float, east: float) -> Optional[bool]:
    if lat is None or lon is None:
        return None
    return south <= lat <= north and west <= lon <= east


# -----------------------------------------------------------------------------
# Sidebar / Inputs
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🧩 Query Inputs")

    query = st.text_input("Query", placeholder="e.g. Zoo")
    viewport_age = st.selectbox("Viewport Age", ["FRESH", "STALE"], index=0)
    locale = st.text_input("Locale", value="en_US")
    country = st.text_input("Country", value="United States")

    st.divider()
    st.subheader("Viewport")
    vp_mode = st.radio("Viewport Input Mode", ["Address", "Lat/Lon"], horizontal=True, key="vp_mode")
    vp_address = ""
    vp_lat = ""
    vp_lon = ""
    if vp_mode == "Address":
        vp_address = st.text_input("Viewport Address / Place", key="vp_address")
    else:
        vp_lat = st.text_input("Viewport Lat", key="vp_lat")
        vp_lon = st.text_input("Viewport Lon", key="vp_lon")
        
    st.markdown("#### Viewport Rectangle Size")
    vp_width_m = st.slider("Viewport width (meters)", min_value=250, max_value=100000, value=3500, step=250)
    vp_height_m = st.slider("Viewport height (meters)", min_value=250, max_value=100000, value=5000, step=250)

    st.divider()
    st.subheader("User")
    user_mode = st.radio("User Input Mode", ["Address", "Lat/Lon"], horizontal=True, key="user_mode")
    user_address = ""
    user_lat = ""
    user_lon = ""
    if user_mode == "Address":
        user_address = st.text_input("User Address / Place", key="user_address")
    else:
        user_lat = st.text_input("User Lat", key="user_lat")
        user_lon = st.text_input("User Lon", key="user_lon")

    st.divider()
    user_inside_viewport_label = st.radio(
        "User position relative to viewport",
        ["Inside FVP", "Outside FVP", "Unknown / N/A"],
        index=2,
    )
    user_inside_viewport_map = {
        "Inside FVP": True,
        "Outside FVP": False,
        "Unknown / N/A": None,
    }

    st.divider()
    result_count = st.number_input("Number of Results", min_value=1, max_value=5, value=1, step=1)

    st.divider()
    render_map_btn = st.button("🗺️ Render Map", use_container_width=True)
    evaluate_btn = st.button("⚡ Evaluate", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# Main layout
# -----------------------------------------------------------------------------
st.title("🗺️ Maps Search Rating Sandbox")
st.caption("Refactored to score via rating_engine.py instead of legacy manual blurb logic.")

if locale != "en_US":
    st.warning(f"Locale is expected to be en_US, but received: {locale}")
if country != "United States":
    st.warning(f"Country is expected to be United States, but received: {country}")

# -----------------------------------------------------------------------------
# Result entry UI
# -----------------------------------------------------------------------------
result_ui_rows: list[dict] = []

tabs = st.tabs([f"Result {i}" for i in range(1, int(result_count) + 1)])

for idx, tab in enumerate(tabs, start=1):
    with tab:
        st.subheader(f"Result {idx}")

        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name", key=f"r_name_{idx}")
            address = st.text_input("Address", key=f"r_address_{idx}", placeholder="Street, City, ST ZIP")
            classification = st.text_input("Classification", key=f"r_class_{idx}", placeholder="e.g. Wildlife Park")
            result_type = st.selectbox(
                "Type",
                ["BUSINESS", "ADDRESS", "LOCALITY", "TRANSIT", "NATURAL_FEATURE"],
                key=f"r_type_{idx}",
            )
            status = st.selectbox(
                "Status",
                ["OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"],
                key=f"r_status_{idx}",
            )

        with c2:
            result_mode = st.radio(
                "Result Location Mode",
                ["Address", "Lat/Lon", "Same"],
                horizontal=True,
                key=f"r_mode_{idx}",
            )
            result_geocode_addr = ""
            result_lat = ""
            result_lon = ""
            if result_mode in ["Address", "Same"]:
                k_ti = f"r_geocode_addr_{idx}"
                if result_mode == "Same":
                    st.session_state.update({k_ti: address})
                result_geocode_addr = st.text_input(
                    "Result Geocode Address / Place",
                    key=k_ti,
                    placeholder="Used only for map pin placement",
                )
            else:
                result_lat = st.text_input("Result Lat", key=f"r_lat_{idx}")
                result_lon = st.text_input("Result Lon", key=f"r_lon_{idx}")

            official_name = st.text_input("Official Name", key=f"r_official_name_{idx}")
            official_address = st.text_input("Official Address", key=f"r_official_addr_{idx}")

        st.markdown("#### USPS Check")
        parsed = parse_simple_address(address)
        use_usps = st.checkbox(f"Run USPS validation for Result {idx}", value=True, key=f"r_use_usps_{idx}")

        usps_data = {
            "ok": False,
            "valid": False,
            "exists": None,
            "dpv_value": None,
            "dpv_accessible": False,
            "standardized_street": None,
            "standardized_city": None,
            "standardized_state": None,
            "zip5": None,
            "zip4": None,
            "match_status": "",
            "match_notes": [],
            "error": None,
            "raw_response": {},
        }

        if use_usps and parsed["street"] and parsed["city"] and parsed["state"]:
            usps_data = verify_address_with_usps(
                street=parsed["street"],
                city=parsed["city"],
                state=parsed["state"],
                zip_code=parsed["zip"],
                secondary="",
            )

        with st.expander("USPS Data", expanded=False):
            st.json(parsed)
            st.json(usps_data)
        
        u1, u2, u3, u4 = st.columns(4)
        usps_lookup_ok = bool(usps_data["ok"])
        dpv_accessible = bool(usps_data["dpv_accessible"])
        exact_exists = usps_data["exists"] is True

        u1.checkbox("USPS lookup succeeded", value=usps_lookup_ok, disabled=True, key=f"u_valid_{idx}")
        u2.checkbox("DPV accessible", value=dpv_accessible, disabled=True, key=f"u_dpv_{idx}")
        u3.checkbox(
            "Exact address exists (DPV=Y truth)",
            value=exact_exists,
            disabled=True,
            key=f"u_exists_{idx}",
        )
        u4.text_input("USPS Match Status", value=usps_data.get("match_status", ""), disabled=True, key=f"u_match_{idx}")

        if usps_lookup_ok:
            if exact_exists:
                st.success("USPS DPV confirms this exact address exists (DPV=Y).")
            elif dpv_accessible:
                st.error("USPS DPV does not confirm this exact address as existing. Treat as incorrect unless you identify a typo or malformed input.")
            else:
                st.warning("USPS lookup ran, but DPV was not accessible. Check for typos, missing ZIP/state, or formatting issues before concluding.")

        st.markdown("#### Pin Evidence")
        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            pin_boundary_identifiable = st.selectbox(
                "Boundary identifiable?",
                [None, True, False],
                index=0,
                format_func=lambda x: "Unknown" if x is None else str(x),
                key=f"pin_boundary_{idx}",
            )
        with p2:
            pin_same_property = st.selectbox(
                "On correct property?",
                [None, True, False],
                index=0,
                format_func=lambda x: "Unknown" if x is None else str(x),
                key=f"pin_property_{idx}",
            )
        with p3:
            pin_same_block = st.selectbox(
                "Same block / side?",
                [None, True, False],
                index=0,
                format_func=lambda x: "Unknown" if x is None else str(x),
                key=f"pin_block_{idx}",
            )
        with p4:
            pin_adjacent_property = st.selectbox(
                "Adjacent property?",
                [None, True, False],
                index=0,
                format_func=lambda x: "Unknown" if x is None else str(x),
                key=f"pin_adjacent_{idx}",
            )
        with p5:
            pin_precise = st.selectbox(
                "Precise location proven?",
                [None, True, False],
                index=0,
                format_func=lambda x: "Unknown" if x is None else str(x),
                key=f"pin_precise_{idx}",
            )

        result_ui_rows.append(
            {
                "name": name,
                "address": address,
                "classification": classification,
                "result_type": result_type,
                "status": status,
                "mode": result_mode,
                "geocode_addr": result_geocode_addr,
                "lat": result_lat,
                "lon": result_lon,
                "official_name": official_name,
                "official_address": official_address,
                "usps": usps_data,
                "pin_boundary_identifiable": pin_boundary_identifiable,
                "pin_same_property": pin_same_property,
                "pin_same_block": pin_same_block,
                "pin_adjacent_property": pin_adjacent_property,
                "pin_precise": pin_precise,
            }
        )

# -----------------------------------------------------------------------------
# Resolve coordinates
# -----------------------------------------------------------------------------
resolved_vp_lat, resolved_vp_lon, resolved_vp_disp = resolve_location(
    "viewport",
    vp_mode,
    vp_address,
    vp_lat,
    vp_lon,
)

resolved_user_lat, resolved_user_lon, resolved_user_disp = resolve_location(
    "user",
    user_mode,
    user_address,
    user_lat,
    user_lon,
)

st.write("result_ui_rows")
st.write(result_ui_rows)
resolved_results: list[dict] = []
for r in result_ui_rows:
    st.write("--=r")
    st.write(r)
    rr_lat, rr_lon, rr_disp = resolve_location(
        "result",
        r["mode"],
        r["geocode_addr"],
        r["lat"],
        r["lon"],
    )
    row = dict(r)
    row["resolved_lat"] = rr_lat
    row["resolved_lon"] = rr_lon
    row["resolved_disp"] = rr_disp
    
    if resolved_vp_lat is not None and resolved_vp_lon is not None:
        try:
            row["inside_viewport_rect"] = point_in_bbox(
                row["resolved_lat"],
                row["resolved_lon"],
                south,
                north,
                west,
                east,
            )
        except NameError:
            row["inside_viewport_rect"] = None
    else:
        row["inside_viewport_rect"] = None

    if rr_lat is not None and rr_lon is not None and resolved_user_lat is not None and resolved_user_lon is not None:
        row["distance_to_user_km"] = haversine_km(resolved_user_lat, resolved_user_lon, rr_lat, rr_lon)
    else:
        row["distance_to_user_km"] = None

    if rr_lat is not None and rr_lon is not None and resolved_vp_lat is not None and resolved_vp_lon is not None:
        row["distance_to_viewport_km"] = haversine_km(resolved_vp_lat, resolved_vp_lon, rr_lat, rr_lon)
    else:
        row["distance_to_viewport_km"] = None

    resolved_results.append(row)

if query.strip():
    locator_url, found = get_chain_locator(query)
    if found:
        st.markdown(f"**Official Chain Locator:** [Open locator for {query}]({locator_url})")
    else:
        st.markdown(f"**Chain Locator Fallback:** [Search official locator for {query}]({locator_url})")

# -----------------------------------------------------------------------------
# Map
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Map")

map_df = build_map_df(
    viewport_lat=resolved_vp_lat,
    viewport_lon=resolved_vp_lon,
    user_lat=resolved_user_lat,
    user_lon=resolved_user_lon,
    results=resolved_results,
)

if render_map_btn or not map_df.empty:
    if map_df.empty:
        st.info("No mappable coordinates yet.")
    else:
        center_lat = map_df["lat"].mean()
        center_lon = map_df["lon"].mean()

        scatter_data = []
        for _, row in map_df.iterrows():
            if row["kind"] == "Viewport":
                color = [59, 130, 246, 220]
                radius = 140
            elif row["kind"] == "User":
                color = [34, 197, 94, 220]
                radius = 140
            else:
                color = [168, 85, 247, 220]
                radius = 120

            scatter_data.append(
                {
                    "position": [row["lon"], row["lat"]],
                    "label": row["label"],
                    "kind": row["kind"],
                    "color": color,
                    "radius": radius,
                }
            )

        # deck = pdk.Deck(
        #     map_style="mapbox://styles/mapbox/light-v9",
        #     initial_view_state=pdk.ViewState(
        #         latitude=center_lat,
        #         longitude=center_lon,
        #         zoom=11,
        #         pitch=0,
        #     ),
        #     tooltip={"text": "{kind}\n{label}"},
        #     layers=[
        #         pdk.Layer(
        #             "ScatterplotLayer",
        #             data=scatter_data,
        #             get_position="position",
        #             get_fill_color="color",
        #             get_radius="radius",
        #             pickable=True,
        #         )
        #     ],
        # )
        # st.pydeck_chart(deck, use_container_width=True)
        
        m = folium.Map(location=(center_lat, center_lon), zoom_start=11, tiles="CartoDB dark_matter")

        # Viewport center marker (blue square)
        if resolved_vp_disp is not None:
            vp_color_map = "#3b82f6" if viewport_age == "Fresh" else "#f59e0b"
            folium.Marker(
                [resolved_vp_lat, resolved_vp_lon],
                popup=f"Viewport Center<br>{(resolved_vp_lat, resolved_vp_lon)}",
                tooltip="📺 Viewport Center",
                icon=folium.Icon(color="blue" if viewport_age == "Fresh" else "orange",
                                icon="tv", prefix="fa")
            ).add_to(m)
            
            bbox = add_viewport_rectangle(
                m,
                center_lat=resolved_vp_lat,
                center_lon=resolved_vp_lon,
                width_m=vp_width_m,
                height_m=vp_height_m,
                color=vp_color_map,
                fill=True,
                fill_opacity=0.16,
                tooltip="Viewport Bounds"
            )
            south = bbox["south"]
            north = bbox["north"]
            west = bbox["west"]
            east = bbox["east"]

        # User marker (green person)
        if resolved_user_disp is not None:
            folium.Marker(
                [resolved_user_lat, resolved_user_lon],
                popup=f"User<br>{(resolved_user_lat, resolved_user_lon)}",
                tooltip="👤 User Location",
                icon=folium.Icon(color="green", icon="user", prefix="fa")
            ).add_to(m)

        # Result pins
        pin_colors = ["red", "purple", "darkred", "cadetblue", "darkblue", "pink"]
        for i, r in enumerate(resolved_results):
            st.write("==R")
            st.write(r)
            if r["resolved_lat"] is not None:
                popup_html = f"""
                <b>{r['name'] or f'Result {i+1}'}</b><br>
                {r['address'] or ''}<br>
                <i>{r['classification'] or ''}</i>
                {'<br><b style="color:red">⚠ CLOSED</b>' if 'close' in r['status'].lower()  else ''}
                """
                folium.Marker(
                    [r["resolved_lat"], r["resolved_lon"]],
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=f"📍 Result {i+1}: {r['name'] or 'unnamed'}",
                    icon=folium.Icon(color=pin_colors[i % len(pin_colors)],
                                    icon="map-marker", prefix="fa")
                ).add_to(m)
                # Line from user to result
                if resolved_user_disp is not None:
                    folium.PolyLine(
                        [[resolved_user_lat, resolved_user_lon],
                        [r["resolved_lat"], r["resolved_lon"]]],
                        color=("#ef4444" if i == 0 else "#a78bfa"),
                        weight=1.5, opacity=0.5, dash_array="5"
                    ).add_to(m)

        st_folium(m, width=None, height=480, returned_objects=[])
            

# -----------------------------------------------------------------------------
# Resolved context summary
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Resolved Inputs")

a1, a2, a3, a4 = st.columns(4)
a1.markdown(f"**Query**  \n`{query or ''}`")
a2.markdown(f"**Viewport Age**  \n`{viewport_age}`")
a3.markdown(f"**Locale**  \n`{locale}`")
a4.markdown(f"**Country**  \n`{country}`")

b1, b2 = st.columns(2)
b1.markdown(
    f"**Viewport Resolved**  \n"
    f"`{resolved_vp_lat}, {resolved_vp_lon}`  \n"
    f"<span class='small-muted'>{resolved_vp_disp}</span>",
    unsafe_allow_html=True,
)
b2.markdown(
    f"**User Resolved**  \n"
    f"`{resolved_user_lat}, {resolved_user_lon}`  \n"
    f"<span class='small-muted'>{resolved_user_disp}</span>",
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    render_location_links("Viewport", resolved_vp_lat, resolved_vp_lon, vp_address or resolved_vp_disp or "")
with c2:
    render_location_links("User", resolved_user_lat, resolved_user_lon, user_address or resolved_user_disp or "")

# -----------------------------------------------------------------------------
# Evaluation
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Evaluation")

if evaluate_btn:
    if not query.strip():
        st.error("Please enter a query.")
    else:
        query_ctx = QueryContext(
            query=query,
            viewport_age=viewport_age,
            locale=locale,
            country=country,
            user_lat=resolved_user_lat,
            user_lon=resolved_user_lon,
            viewport_lat=resolved_vp_lat,
            viewport_lon=resolved_vp_lon,
            user_inside_viewport=user_inside_viewport_map[user_inside_viewport_label],
        )

        st.write("resolved_results")
        st.write(resolved_results)
        engine_results = [build_result_input_from_ui(r) for r in resolved_results]
        decisions = [score_result(query_ctx, r, engine_results, classification) for r in engine_results]

        # Query-level result banner
        if decisions:
            nav_exists = decisions[0].has_navigational_result
            st.markdown(
                f"""
                <div class="metric-box">
                    <b>Is there a navigational result for this query?</b>
                    <span class="code-ish">{'Yes' if nav_exists else 'No'}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Distance ranking helper
        valid_dist_rows = []
        for i, r in enumerate(resolved_results, start=1):
            d = r.get("distance_to_user_km")
            if d is not None:
                valid_dist_rows.append((i, r.get("name") or f"Result {i}", d))
        valid_dist_rows.sort(key=lambda x: x[2])

        if valid_dist_rows:
            st.markdown("#### Distance to User Ranking")
            for rank, (ri, nm, dkm) in enumerate(valid_dist_rows, start=1):
                st.write(f"#{rank} — Result {ri} ({nm}) — {dkm:.2f} km")

        st.markdown("#### Per-Result Decisions")
        for i, (ui_row, decision) in enumerate(zip(resolved_results, decisions), start=1):
            with st.container():
                
                inside_rect = ui_row.get("inside_viewport_rect")
                st.write("**Inside viewport rectangle?**", format_bool(inside_rect))

                render_location_links(
                    f"Result {i}",
                    ui_row.get("resolved_lat"),
                    ui_row.get("resolved_lon"),
                    ui_row.get("address", "") or ui_row.get("resolved_disp", ""),
                )
                
                st.markdown("<div class='decision-box'>", unsafe_allow_html=True)
                st.markdown(f"### Result {i}: {ui_row.get('name') or f'Result {i}'}")

                c1, c2, c3 = st.columns(3)
                c1.write(f"**Unexpected language/script?** {'Yes' if decision.unexpected_language_or_script else 'No'}")
                c2.write(f"**Business/POI closed or does not exist?** {'Yes' if decision.business_closed_or_dne else 'No'}")
                c3.write(f"**Relevance** {decision.relevance}")

                d1, d2, d3 = st.columns(3)
                d1.write(f"**Name Accuracy** {decision.name_rating}")
                d2.write(f"**Address Accuracy** {decision.address_rating}")
                d3.write(f"**Pin Accuracy** {decision.pin_rating}")

                if decision.address_issues:
                    st.write(f"**Address Issues:** {', '.join(decision.address_issues)}")
                if decision.demotion_reasons:
                    st.write(f"**Demotion Reasons:** {', '.join(decision.demotion_reasons)}")
                if decision.relevance_notes:
                    st.write(f"**Relevance Notes:** {' '.join(decision.relevance_notes)}")

                # blurb = decision_to_blurb(ui_row.get("name", ""), decision)
                locator_url, found = get_chain_locator(query)
                chainish = found
                blurb = decision_to_blurb(
                    ui_row.get("name", ""),
                    decision,
                    query=query,
                    locator_url=locator_url,
                    is_chain=chainish,
                )
                st.text_area(
                    f"Generated Comment / Blurb {i}",
                    value=blurb,
                    height=220,
                    key=f"result_blurb_{i}",
                )
                
                st.write("decision")
                st.write(asdict(decision))

                st.markdown("</div>", unsafe_allow_html=True)