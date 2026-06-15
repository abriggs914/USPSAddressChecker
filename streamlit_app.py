# streamlit_app.py
from __future__ import annotations

import math
import re
from typing import Optional
from dataclasses import asdict

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

from usps_api import lookup_address, USPSApiError, parse_simple_address
from utils.location_utility import geocode_address, resolve_location

from rating_engine import (
    QueryContext,
    ResultInput,
    AssumptionFlag,
    score_result,
    get_chain_locator,
    google_maps_link,
    google_maps_address_link,
    bing_maps_link,
    bing_maps_address_link,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page config & styles
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Maps Search Rating Sandbox",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
        /* General */
        .small-muted  { color: #64748b; font-size: 16px; }
        .code-ish     { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                        font-size: 18px; }

        /* Decision summary card */
        .decision-box {
            border: 1px solid #dbeafe;
            background: #606060;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }

        /* Blurb / comment */
        .blurb-box {
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 14px;
            background: #606060;
            white-space: pre-wrap;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 18px;
        }

        /* Assumption flag cards */
        .flag-error   { border-left: 4px solid #ef4444; background: #606060;
                        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
        .flag-warning { border-left: 4px solid #f59e0b; background: #606060;
                        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
        .flag-info    { border-left: 4px solid #3b82f6; background: #606060;
                        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
        .flag-field   { font-weight: 700; font-size: 18px; margin-bottom: 3px; }
        .flag-msg     { font-size: 18px; margin-bottom: 5px; }
        .flag-action  { font-size: 16px; color: #cbdef3; white-space: pre-wrap; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_geolocator() -> Nominatim:
    return Nominatim(user_agent="maps_search_rating_sandbox")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def format_bool(v: Optional[bool]) -> str:
    if v is True:   return "✅ Yes"
    if v is False:  return "❌ No"
    return "❔ Unknown"


def result_status_from_ui(raw: str) -> str:
    s = (raw or "OPEN").strip().upper()
    return s if s in {"OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"} else "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# USPS helpers
# ─────────────────────────────────────────────────────────────────────────────
def _assess_address_match(
    input_addr: str, usps_street: str,
    input_city: str,  usps_city: str,
    input_state: str, usps_state: str,
    input_zip: str,   usps_zip5: str,
) -> dict:
    def nk(s: str) -> str:
        s = (s or "").strip().lower()
        return re.sub(r"\s+", " ", s.replace(".", "").replace(",", ""))

    if (
        nk(input_addr) == nk(usps_street)
        and nk(input_city) == nk(usps_city)
        and nk(input_state) == nk(usps_state)
        and (not input_zip or nk(input_zip) == nk(usps_zip5))
    ):
        return {"status": "Exact normalized match", "notes": []}

    if nk(input_city) == nk(usps_city) and nk(input_state) == nk(usps_state) and usps_street:
        return {"status": "Close match", "notes": ["USPS standardized the street line."]}

    return {"status": "Mismatch", "notes": ["Input address differs from USPS normalized form."]}


@st.cache_data(show_spinner=False)
def verify_address_with_usps(
    street: str, city: str, state: str,
    zip_code: str = "", secondary: str = "",
) -> dict:
    EMPTY: dict = {
        "ok": False, "valid": False, "exists": None,
        "dpv_value": None, "dpv_accessible": False,
        "standardized_street": None, "standardized_city": None,
        "standardized_state": None, "zip5": None, "zip4": None,
        "match_status": "", "match_notes": [], "error": None, "raw_response": {},
    }
    try:
        result = lookup_address(
            street=street, city=city, state=state,
            zip_code=zip_code or None,
            secondary_address=secondary or None,
        )
        dpv = (getattr(result, "dpv_value", "") or "").strip().upper()
        dpv_accessible = bool(getattr(result, "dpv_accessible", False))
        exists = (True if dpv == "Y" else False if dpv == "N" else None) if dpv_accessible else None

        match_info = _assess_address_match(
            street, getattr(result, "standardized_street", "") or "",
            city,   getattr(result, "standardized_city",  "") or "",
            state,  getattr(result, "standardized_state", "") or "",
            zip_code or "", getattr(result, "zip5", "") or "",
        )
        return {
            "ok": True, "valid": bool(result.valid()), "exists": exists,
            "dpv_value": dpv or None, "dpv_accessible": dpv_accessible,
            "standardized_street": getattr(result, "standardized_street", None),
            "standardized_city":   getattr(result, "standardized_city",   None),
            "standardized_state":  getattr(result, "standardized_state",  None),
            "zip5": getattr(result, "zip5", None), "zip4": getattr(result, "zip4", None),
            "match_status": match_info["status"], "match_notes": match_info["notes"],
            "error": getattr(result, "error", None),
            "raw_response": getattr(result, "raw_response", {}),
        }
    except Exception as exc:
        st.error(f"USPS API error: {exc}")
        return {**EMPTY, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────────────────
def render_location_links(
    title: str, lat: Optional[float], lon: Optional[float], address: str = ""
) -> None:
    st.markdown(f"**{title} Links**")
    cols = st.columns(4)
    if lat is not None and lon is not None:
        cols[0].markdown(f"[Google Maps (coord)]({google_maps_link(lat, lon)})")
        cols[1].markdown(f"[Bing Maps (coord)]({bing_maps_link(lat, lon)})")
    else:
        cols[0].markdown("_Google coord unavailable_")
        cols[1].markdown("_Bing coord unavailable_")
    if address.strip():
        cols[2].markdown(f"[Google Maps (addr)]({google_maps_address_link(address)})")
        cols[3].markdown(f"[Bing Maps (addr)]({bing_maps_address_link(address)})")
    else:
        cols[2].markdown("_Google addr unavailable_")
        cols[3].markdown("_Bing addr unavailable_")


def render_assumption_flags(flags: list[AssumptionFlag]) -> None:
    """Render assumption flags as a prioritised checklist."""
    if not flags:
        st.success("✅ No open assumptions — all required inputs are present.")
        return

    errors   = [f for f in flags if f.severity == "error"]
    warnings = [f for f in flags if f.severity == "warning"]
    infos    = [f for f in flags if f.severity == "info"]

    total = len(flags)
    e, w, i = len(errors), len(warnings), len(infos)
    st.markdown(
        f"**{total} assumption(s) to investigate:** "
        f"🔴 {e} must-verify &nbsp;|&nbsp; 🟡 {w} check &nbsp;|&nbsp; 🔵 {i} FYI"
    )

    for flag in errors + warnings + infos:
        cls = {"error": "flag-error", "warning": "flag-warning", "info": "flag-info"}[flag.severity]
        icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[flag.severity]
        st.markdown(
            f"""
            <div class="{cls}">
                <div class="flag-field">{icon} {flag.field}</div>
                <div class="flag-msg">{flag.message}</div>
                <div class="flag-action">{flag.action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _relevance_badge(r: str) -> str:
    colors = {
        "Navigational": "#1d4ed8",
        "Excellent":    "#15803d",
        "Good":         "#0e7490",
        "Acceptable":   "#d97706",
        "Bad":          "#dc2626",
    }
    c = colors.get(r, "#64748b")
    return (
        f'<span style="background:{c};color:#777;padding:2px 10px;'
        f'border-radius:6px;font-weight:700;font-size:18px">{r}</span>'
    )


def decision_to_blurb(result_name: str, decision, query: str = "") -> str:
    """Generate a concise comment suitable for pasting into TryRating."""
    lines = [
        f"Navigational result for query: {'Yes' if decision.has_navigational_result else 'No'}",
    ]
    if decision.unexpected_language_or_script:
        lines.append("⚠ Result name/title is in unexpected language or script — all other ratings N/A.")
        return "\n".join(lines)

    if decision.business_closed_or_dne:
        lines.append("Business/POI closed or does not exist — relevance rated as if open (§4.2).")

    rel_line = f"Relevance: {decision.relevance}"
    if decision.demotion_reasons:
        rel_line += f" [{', '.join(decision.demotion_reasons)}]"
    lines.append(rel_line)

    if decision.relevance_notes:
        lines.extend(decision.relevance_notes)

    lines.append(f"Name Accuracy: {decision.name_rating}")
    lines.append(f"Address Accuracy: {decision.address_rating}")
    if decision.address_issues:
        lines.append(f"  Issues: {', '.join(decision.address_issues)}")
    lines.append(f"Pin Accuracy: {decision.pin_rating}")

    lines.append("")
    lines.append(decision.comment)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Map helpers
# ─────────────────────────────────────────────────────────────────────────────
def add_viewport_rectangle(
    m, center_lat: float, center_lon: float,
    width_m: int = 3500, height_m: int = 5000,
    color: str = "#3b82f6",
) -> dict:
    lat_deg_per_m = 1 / 111_320
    lon_deg_per_m = 1 / (111_320 * math.cos(math.radians(center_lat)))
    half_h = (height_m / 2) * lat_deg_per_m
    half_w = (width_m  / 2) * lon_deg_per_m
    south, north = center_lat - half_h, center_lat + half_h
    west,  east  = center_lon - half_w, center_lon + half_w
    folium.Rectangle(
        bounds=[[south, west], [north, east]],
        color=color, weight=2,
        fill=True, fill_color=color, fill_opacity=0.14,
        tooltip="Viewport Bounds",
    ).add_to(m)
    return dict(south=south, north=north, west=west, east=east)


def point_in_bbox(
    lat: Optional[float], lon: Optional[float],
    south: float, north: float, west: float, east: float,
) -> Optional[bool]:
    if lat is None or lon is None:
        return None
    return south <= lat <= north and west <= lon <= east


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


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar inputs
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🧩 Query Inputs")

    query        = st.text_input("Query", placeholder="e.g. Starbucks")
    viewport_age = st.selectbox("Viewport Age", ["FRESH", "STALE"], index=0)
    locale       = st.text_input("Locale",  value="en_US")
    country      = st.text_input("Country", value="United States")

    st.divider()
    st.subheader("📺 Viewport")
    vp_mode    = st.radio("Viewport Input Mode", ["Address", "Lat/Lon"], horizontal=True, key="vp_mode")
    vp_address = vp_lat = vp_lon = ""
    if vp_mode == "Address":
        vp_address = st.text_input("Viewport Address / Place", key="vp_address")
    else:
        vp_lat = st.text_input("Viewport Lat", key="vp_lat")
        vp_lon = st.text_input("Viewport Lon", key="vp_lon")

    st.markdown("##### Viewport Rectangle Size")
    vp_width_m  = st.slider("Width (m)",  250, 100_000,  3_500, 250)
    vp_height_m = st.slider("Height (m)", 250, 100_000,  5_000, 250)

    st.divider()
    st.subheader("👤 User")
    user_mode    = st.radio("User Input Mode", ["Address", "Lat/Lon"], horizontal=True, key="user_mode")
    user_address = user_lat = user_lon = ""
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
        "Inside FVP":     True,
        "Outside FVP":    False,
        "Unknown / N/A":  None,
    }

    st.divider()
    result_count  = st.number_input("Number of Results", min_value=1, max_value=5, value=1, step=1)

    st.divider()
    render_map_btn = st.button("🗺️ Render Map",  use_container_width=True)
    evaluate_btn   = st.button("⚡ Evaluate",     use_container_width=True, type="primary")


# ─────────────────────────────────────────────────────────────────────────────
# Title
# ─────────────────────────────────────────────────────────────────────────────
st.title("🗺️ Maps Search Rating Sandbox")

if locale != "en_US":
    st.warning(f"Locale is not en_US (got: {locale}) — unexpected language detection may be inaccurate.")
if country != "United States":
    st.warning(f"Country is not 'United States' (got: {country}).")

# ─────────────────────────────────────────────────────────────────────────────
# Chain locator banner (shows before any result entry)
# ─────────────────────────────────────────────────────────────────────────────
if query.strip():
    locator_url, found = get_chain_locator(query)
    if found:
        st.info(f"🔗 **Official chain locator detected:** [Open locator for *{query}*]({locator_url})")
    else:
        st.caption(f"No known chain locator for *{query}*. [Search for official locator]({locator_url})")


# ─────────────────────────────────────────────────────────────────────────────
# Result entry tabs
# ─────────────────────────────────────────────────────────────────────────────
result_ui_rows: list[dict] = []
tabs = st.tabs([f"Result {i}" for i in range(1, int(result_count) + 1)])

for idx, tab in enumerate(tabs, start=1):
    with tab:
        st.subheader(f"Result {idx}")

        col_a, col_b = st.columns(2)
        with col_a:
            name           = st.text_input("Name",           key=f"r_name_{idx}")
            address        = st.text_input("Address",        key=f"r_address_{idx}",
                                           placeholder="Street, City, ST ZIP")
            classification = st.text_input("Classification", key=f"r_class_{idx}",
                                           placeholder="e.g. Grocery Store")
            result_type    = st.selectbox(
                "Type",
                ["BUSINESS", "ADDRESS", "LOCALITY", "TRANSIT", "NATURAL_FEATURE"],
                key=f"r_type_{idx}",
            )
            status = st.selectbox(
                "Status",
                ["OPEN", "CLOSED", "PERMANENT_CLOSURE", "UNKNOWN"],
                key=f"r_status_{idx}",
            )

        k_official_addr = f"r_official_addr_{idx}"
        with col_b:
            result_mode = st.radio(
                "Result Location Mode",
                ["Address", "Lat/Lon", "Same"],
                horizontal=True, key=f"r_mode_{idx}",
            )
            result_geocode_addr = result_lat = result_lon = ""
            if result_mode in ("Address", "Same"):
                k = f"r_geocode_addr_{idx}"
                if result_mode == "Same":
                    st.session_state.update({k: address, k_official_addr: address})
                result_geocode_addr = st.text_input(
                    "Result Geocode Address / Place", key=k,
                    placeholder="Used only for map pin placement",
                )
            else:
                result_lat = st.text_input("Result Lat", key=f"r_lat_{idx}")
                result_lon = st.text_input("Result Lon", key=f"r_lon_{idx}")

            official_name    = st.text_input("Official Name",    key=f"r_official_name_{idx}")
            official_address = st.text_input("Official Address", key=k_official_addr)

        # ── USPS section ──────────────────────────────────────────────────
        st.markdown("#### 📮 USPS Check")
        parsed   = parse_simple_address(address)
        use_usps = st.checkbox(
            f"Run USPS validation for Result {idx}", value=True, key=f"r_use_usps_{idx}"
        )

        EMPTY_USPS: dict = {
            "ok": False, "valid": False, "exists": None,
            "dpv_value": None, "dpv_accessible": False,
            "standardized_street": None, "standardized_city": None,
            "standardized_state": None, "zip5": None, "zip4": None,
            "match_status": "", "match_notes": [], "error": None, "raw_response": {},
        }
        usps_data = dict(EMPTY_USPS)

        if use_usps and parsed["street"] and parsed["city"] and parsed["state"]:
            usps_data = verify_address_with_usps(
                street=parsed["street"], city=parsed["city"],
                state=parsed["state"], zip_code=parsed["zip"], secondary="",
            )

        with st.expander("USPS Raw Data", expanded=False):
            st.json(parsed)
            st.json(usps_data)

        uc1, uc2, uc3, uc4 = st.columns(4)
        usps_ok       = bool(usps_data["ok"])
        dpv_accessible = bool(usps_data["dpv_accessible"])
        exact_exists  = usps_data["exists"] is True

        uc1.checkbox("USPS lookup OK",         value=usps_ok,        disabled=True, key=f"u_ok_{idx}")
        uc2.checkbox("DPV accessible",          value=dpv_accessible, disabled=True, key=f"u_dpv_{idx}")
        uc3.checkbox("Address exists (DPV=Y)",  value=exact_exists,   disabled=True, key=f"u_exists_{idx}")
        uc4.text_input("Match Status", value=usps_data.get("match_status", ""),
                       disabled=True, key=f"u_match_{idx}")

        if usps_ok:
            if exact_exists:
                st.success("✅ USPS DPV confirms address exists (DPV=Y).")
            elif dpv_accessible:
                st.error("❌ USPS DPV does NOT confirm this address. Treat as Incorrect – Address does not exist.")
            else:
                st.warning("⚠️ USPS ran but DPV was not accessible. Check ZIP/state formatting.")

        # ── Pin evidence ──────────────────────────────────────────────────
        st.markdown("#### 📍 Pin Evidence")
        st.caption(
            "Fill these in after checking the result pin on Google/Bing Maps. "
            "Leave as 'Unknown' if you haven't verified yet — the engine will flag it."
        )
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)

        def _tri(label: str, key: str):
            return st.selectbox(
                label, [None, True, False], index=0,
                format_func=lambda x: "Unknown" if x is None else ("Yes" if x else "No"),
                key=key,
            )

        with pc1: pin_boundary_identifiable = _tri("Boundary identifiable?",  f"pin_boundary_{idx}")
        with pc2: pin_same_property         = _tri("On correct property?",    f"pin_property_{idx}")
        with pc3: pin_same_block            = _tri("Same block / side?",       f"pin_block_{idx}")
        with pc4: pin_adjacent_property     = _tri("Adjacent property?",       f"pin_adjacent_{idx}")
        with pc5: pin_precise               = _tri("Precise location proven?", f"pin_precise_{idx}")

        result_ui_rows.append({
            "name": name, "address": address, "classification": classification,
            "result_type": result_type, "status": status,
            "mode": result_mode, "geocode_addr": result_geocode_addr,
            "lat": result_lat, "lon": result_lon,
            "official_name": official_name, "official_address": official_address,
            "usps": usps_data,
            "pin_boundary_identifiable": pin_boundary_identifiable,
            "pin_same_property": pin_same_property,
            "pin_same_block": pin_same_block,
            "pin_adjacent_property": pin_adjacent_property,
            "pin_precise": pin_precise,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Resolve coordinates
# ─────────────────────────────────────────────────────────────────────────────
resolved_vp_lat,   resolved_vp_lon,   resolved_vp_disp   = resolve_location(
    "viewport", vp_mode, vp_address, vp_lat, vp_lon)
resolved_user_lat, resolved_user_lon, resolved_user_disp = resolve_location(
    "user", user_mode, user_address, user_lat, user_lon)

# Viewport bbox (used for inside/outside check)
vp_bbox: Optional[dict] = None

resolved_results: list[dict] = []
for r in result_ui_rows:
    rr_lat, rr_lon, rr_disp = resolve_location(
        "result", r["mode"], r["geocode_addr"], r["lat"], r["lon"]
    )
    row = dict(r)
    row.update(resolved_lat=rr_lat, resolved_lon=rr_lon, resolved_disp=rr_disp)

    # Distance
    if rr_lat is not None and rr_lon is not None:
        if resolved_user_lat is not None:
            row["distance_to_user_km"] = haversine_km(
                resolved_user_lat, resolved_user_lon, rr_lat, rr_lon)
        else:
            row["distance_to_user_km"] = None

        if resolved_vp_lat is not None:
            row["distance_to_viewport_km"] = haversine_km(
                resolved_vp_lat, resolved_vp_lon, rr_lat, rr_lon)
        else:
            row["distance_to_viewport_km"] = None
    else:
        row["distance_to_user_km"]     = None
        row["distance_to_viewport_km"] = None

    row["inside_viewport_rect"] = None  # computed below after bbox is known
    resolved_results.append(row)


# ─────────────────────────────────────────────────────────────────────────────
# Resolved inputs summary
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Resolved Inputs")

r1, r2, r3, r4 = st.columns(4)
r1.markdown(f"**Query**\n\n`{query or '—'}`")
r2.markdown(f"**Viewport Age**\n\n`{viewport_age}`")
r3.markdown(f"**Locale**\n\n`{locale}`")
r4.markdown(f"**Country**\n\n`{country}`")

r5, r6 = st.columns(2)
r5.markdown(
    f"**Viewport**  \n`{resolved_vp_lat}, {resolved_vp_lon}`  \n"
    f"<span class='small-muted'>{resolved_vp_disp or '—'}</span>",
    unsafe_allow_html=True,
)
r6.markdown(
    f"**User**  \n`{resolved_user_lat}, {resolved_user_lon}`  \n"
    f"<span class='small-muted'>{resolved_user_disp or '—'}</span>",
    unsafe_allow_html=True,
)

rc1, rc2 = st.columns(2)
with rc1:
    render_location_links("Viewport", resolved_vp_lat, resolved_vp_lon, vp_address or resolved_vp_disp or "")
with rc2:
    render_location_links("User", resolved_user_lat, resolved_user_lon, user_address or resolved_user_disp or "")


# ─────────────────────────────────────────────────────────────────────────────
# Map
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Map")

has_any_coords = (
    resolved_vp_lat is not None
    or resolved_user_lat is not None
    or any(r.get("resolved_lat") is not None for r in resolved_results)
)

if render_map_btn or has_any_coords:
    all_lats = [x for x in [resolved_vp_lat, resolved_user_lat] if x is not None]
    all_lons = [x for x in [resolved_vp_lon, resolved_user_lon] if x is not None]
    for r in resolved_results:
        if r.get("resolved_lat") is not None:
            all_lats.append(r["resolved_lat"])
            all_lons.append(r["resolved_lon"])

    if not all_lats:
        st.info("No mappable coordinates yet.")
    else:
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)

        m = folium.Map(location=(center_lat, center_lon), zoom_start=11, tiles="CartoDB dark_matter")

        # Viewport rectangle
        if resolved_vp_lat is not None:
            vp_color = "#3b82f6" if viewport_age == "FRESH" else "#f59e0b"
            vp_bbox = add_viewport_rectangle(
                m, resolved_vp_lat, resolved_vp_lon,
                vp_width_m, vp_height_m, vp_color,
            )
            folium.Marker(
                [resolved_vp_lat, resolved_vp_lon],
                popup=f"Viewport ({resolved_vp_lat:.4f}, {resolved_vp_lon:.4f})",
                tooltip="📺 Viewport Center",
                icon=folium.Icon(
                    color="blue" if viewport_age == "FRESH" else "orange",
                    icon="tv", prefix="fa",
                ),
            ).add_to(m)

        # User
        if resolved_user_lat is not None:
            folium.Marker(
                [resolved_user_lat, resolved_user_lon],
                popup=f"User ({resolved_user_lat:.4f}, {resolved_user_lon:.4f})",
                tooltip="👤 User Location",
                icon=folium.Icon(color="green", icon="user", prefix="fa"),
            ).add_to(m)

        # Results + viewport inside check
        pin_colors = ["red", "purple", "darkred", "cadetblue", "darkblue", "pink"]
        for i, row in enumerate(resolved_results):
            if vp_bbox and row.get("resolved_lat") is not None:
                row["inside_viewport_rect"] = point_in_bbox(
                    row["resolved_lat"], row["resolved_lon"],
                    vp_bbox["south"], vp_bbox["north"],
                    vp_bbox["west"],  vp_bbox["east"],
                )

            if row.get("resolved_lat") is not None:
                closed_str = (
                    '<br><b style="color:red">⚠ CLOSED/DNE</b>'
                    if "clos" in row.get("status", "").lower() else ""
                )
                folium.Marker(
                    [row["resolved_lat"], row["resolved_lon"]],
                    popup=folium.Popup(
                        f"<b>{row.get('name') or f'Result {i+1}'}</b><br>"
                        f"{row.get('address','')}<br>"
                        f"<i>{row.get('classification','')}</i>{closed_str}",
                        max_width=200,
                    ),
                    tooltip=f"📍 Result {i+1}: {row.get('name') or 'unnamed'}",
                    icon=folium.Icon(
                        color=pin_colors[i % len(pin_colors)],
                        icon="map-marker", prefix="fa",
                    ),
                ).add_to(m)
                if resolved_user_lat is not None:
                    folium.PolyLine(
                        [[resolved_user_lat, resolved_user_lon],
                         [row["resolved_lat"], row["resolved_lon"]]],
                        color="#ef4444" if i == 0 else "#a78bfa",
                        weight=1.5, opacity=0.5, dash_array="5",
                    ).add_to(m)

        st_folium(m, width=None, height=480, returned_objects=[])


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────
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

        engine_results = [build_result_input_from_ui(r) for r in resolved_results]
        decisions      = [score_result(query_ctx, r, engine_results) for r in engine_results]

        # ── Query-level banner ─────────────────────────────────────────────
        if decisions:
            nav = decisions[0].has_navigational_result
            st.markdown(
                f"""
                <div style="border:1px solid #e2e8f0;border-radius:10px;
                            padding:12px 16px;background:#606060;margin-bottom:12px">
                    <b>Is there a navigational result for this query?</b>
                    <span class="code-ish" style="margin-left:12px">
                        {'✅ Yes' if nav else '❌ No'}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Distance ranking helper ────────────────────────────────────────
        dist_rows = [
            (i, r.get("name") or f"Result {i}", r.get("distance_to_user_km"))
            for i, r in enumerate(resolved_results, 1)
            if r.get("distance_to_user_km") is not None
        ]
        if dist_rows:
            dist_rows.sort(key=lambda x: x[2])
            st.markdown("#### Distance to User Ranking")
            for rank, (ri, nm, dkm) in enumerate(dist_rows, 1):
                st.write(f"#{rank} — Result {ri} ({nm}) — {dkm:.2f} km")

        # ── Per-result decisions ───────────────────────────────────────────
        st.markdown("#### Per-Result Decisions")

        for i, (ui_row, decision) in enumerate(zip(resolved_results, decisions), 1):
            with st.container():
                st.markdown(f"### Result {i}: {ui_row.get('name') or f'Result {i}'}")

                inside_rect = ui_row.get("inside_viewport_rect")
                st.write(f"**Inside viewport rectangle?** {format_bool(inside_rect)}")

                render_location_links(
                    f"Result {i}",
                    ui_row.get("resolved_lat"),
                    ui_row.get("resolved_lon"),
                    ui_row.get("address") or ui_row.get("resolved_disp") or "",
                )

                st.markdown("<div class='decision-box'>", unsafe_allow_html=True)

                # Rating summary row
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.markdown(
                    f"**Relevance**<br>{_relevance_badge(decision.relevance)}",
                    unsafe_allow_html=True,
                )
                sc2.write(f"**Name** {decision.name_rating}")
                sc3.write(f"**Address** {decision.address_rating}")
                sc4.write(f"**Pin** {decision.pin_rating}")

                # Flags row
                ff1, ff2, ff3 = st.columns(3)
                ff1.write(
                    f"**Unexpected language?** "
                    f"{'🚫 Yes' if decision.unexpected_language_or_script else 'No'}"
                )
                ff2.write(
                    f"**Closed / DNE?** "
                    f"{'⚠️ Yes' if decision.business_closed_or_dne else 'No'}"
                )
                ff3.write(
                    f"**Demotion:** "
                    f"{', '.join(decision.demotion_reasons) if decision.demotion_reasons else '—'}"
                )

                if decision.address_issues:
                    st.info(f"Address issue(s): {', '.join(decision.address_issues)}")
                if decision.relevance_notes:
                    with st.expander("Relevance reasoning", expanded=False):
                        for note in decision.relevance_notes:
                            st.write(note)

                st.markdown("</div>", unsafe_allow_html=True)

                # ── Assumption flags (the star of the show) ────────────────
                st.markdown("##### 🔍 Assumptions to Investigate")
                render_assumption_flags(decision.assumption_flags)

                # ── Generated blurb ────────────────────────────────────────
                blurb = decision_to_blurb(ui_row.get("name", ""), decision, query=query)
                st.text_area(
                    f"Generated Comment / Blurb — Result {i}",
                    value=blurb,
                    height=220,
                    key=f"result_blurb_{i}",
                )

                st.divider()
