from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from usps_api import USPSApiError, lookup_address


st.set_page_config(page_title="USPS Address Lookup", layout="wide")
st.title("USPS Address Lookup")

st.caption("Uses USPS Developer API, not browser automation.")

if "results" not in st.session_state:
    st.session_state.results = []

cont_form = st.container()
cont_results = st.container()

k_addr = "key_addr"
st.session_state.setdefault(k_addr, "")
with cont_form:
    with st.form("lookup_form", clear_on_submit=False):
        cont_fields = st.container()
        cont_buttons = st.container()
        with cont_buttons:
            clear = st.button(
                "clear",
                on_click=lambda: 
                    st.session_state.update({
                        k_addr: None
                    })
            )
            submitted = st.form_submit_button("Lookup")
        with cont_fields:
        
            c1, c2 = st.columns(2)
            with c1:
                street = st.text_input("Street Address", key=k_addr)
                city = st.text_input("City")
            with c2:
                state = st.text_input("State", max_chars=2)
                zip_code = st.text_input("ZIP Code")
            secondary = st.text_input("Apt / Suite / Other")

with cont_results:
    if submitted:
        if not street or not city or not state:
            st.error("Street, city, and state are required.")
        else:
            try:
                result = lookup_address(
                    street=street,
                    city=city,
                    state=state,
                    zip_code=zip_code or None,
                    secondary_address=secondary or None,
                )
                st.session_state.results.append(asdict(result))
            except USPSApiError as e:
                st.error(str(e))
            except Exception as e:
                st.exception(e)

    st.subheader("Results")

    if st.session_state.results:
        df = pd.DataFrame([
            {
                "input_street": r["input_street"],
                "input_city": r["input_city"],
                "input_state": r["input_state"],
                "input_zip": r["input_zip"],
                "exists": r["exists"],
                "standardized_street": r["standardized_street"],
                "standardized_city": r["standardized_city"],
                "standardized_state": r["standardized_state"],
                "zip5": r["zip5"],
                "zip4": r["zip4"],
                "delivery_point_zip": r["delivery_point_zip"],
                "dpv_accessible": r["dpv_accessible"],
                "dpv_value": r["dpv_value"],
                "dpv_field_path": r["dpv_field_path"],
                "error": r["error"],
            }
            for r in st.session_state.results
        ])
        st.dataframe(df, use_container_width=True)

        with st.expander("Latest raw USPS response"):
            st.json(st.session_state.results[-1]["raw_response"])

if st.button("Clear Results"):
	st.session_state.results = []
	st.rerun()
else:
    st.info("No lookups yet.")