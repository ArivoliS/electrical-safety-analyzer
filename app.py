"""Electrical Safety Analyzer Lab: a Streamlit app for the IEC 60601-1 safety test experiment.

Run with:  streamlit run app.py
"""
import datetime

import pandas as pd
import streamlit as st

import safety_core as sc

st.set_page_config(page_title="Electrical Safety Analyzer Lab", page_icon="⚡", layout="wide")


def stretch(fn, *args, **kwargs):
    """Call a Streamlit element full width on both old and new Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


# ---------- sidebar: device under test ----------
with st.sidebar:
    st.header("Device under test")
    info = {
        "name": st.text_input("Equipment", placeholder="e.g. Patient monitor"),
        "model": st.text_input("Make and model", placeholder="e.g. Acme PM-200"),
        "serial": st.text_input("Serial number", placeholder="e.g. SN 48213"),
        "operator": st.text_input("Operator", placeholder="Your name"),
        "date": str(st.date_input("Date", value=datetime.date.today())),
        "mains": st.number_input("Mains voltage (V)", min_value=0.0, value=230.0, step=1.0),
    }
    cls = st.selectbox("Protection class", list(sc.CLASS_LABELS), format_func=sc.CLASS_LABELS.get)
    ap = st.selectbox("Applied part type", list(sc.AP_LABELS), index=2, format_func=sc.AP_LABELS.get)
    st.caption("Class and applied part type decide which tests apply and which limits are used.")
    st.divider()
    st.subheader("Virtual device")
    preset = st.selectbox("Practice with", list(sc.PRESETS))
    st.caption("Fills readings the way a real analyzer might. Clear them before you record real values.")

rows = sc.build_rows(cls, ap)
ids = [r["id"] for r in rows]

# ---------- state ----------
if "readings" not in st.session_state:
    st.session_state["readings"] = {}
    st.session_state["ver"] = 0
    st.session_state["seeded"] = False
    st.session_state["note"] = ""
readings = st.session_state["readings"]


def fill_all():
    for r in rows:
        readings[r["id"]] = sc.virtual_reading(r, preset, ap)
    st.session_state["ver"] += 1
    st.session_state["note"] = f"Readings were produced by the virtual device ({preset})."


if not st.session_state["seeded"]:
    st.session_state["seeded"] = True
    fill_all()

# ---------- header ----------
st.title("⚡ Electrical Safety Analyzer Lab")
st.write(
    "Test a medical electrical device for earth resistance and leakage currents. "
    "Record each reading from your analyzer and see at once whether it is inside the IEC 60601-1 limit."
)
summary_box = st.container()

b1, b2, _ = st.columns([1, 1, 3])
if b1.button("Measure all (virtual)", type="primary"):
    fill_all()
    st.rerun()
if b2.button("Clear all"):
    readings.clear()
    st.session_state["ver"] += 1
    st.session_state["note"] = ""
    st.rerun()

tab_matrix, tab_circuit, tab_report, tab_guide = st.tabs(["Test matrix", "Circuit", "Report", "Experiment guide"])

# ---------- test matrix ----------
with tab_matrix:
    df = pd.DataFrame({
        "Test": [sc.KINDS[r["kind"]]["short"] for r in rows],
        "Mode": ["—" if r["mode"] == "NA" else r["mode"] for r in rows],
        "Polarity": ["Reverse" if r["pol"] == "R" else "Normal" for r in rows],
        "Earth": ["Open" if r["earth"] == "O" else "Closed" for r in rows],
        "Neutral": ["Open" if r["neut"] == "O" else "Closed" for r in rows],
        "Limit": [sc.limit_text(r) for r in rows],
        "Reading": [readings.get(r["id"]) for r in rows],
    })
    editor_key = f"ed_{st.session_state['ver']}_{cls}_{ap}"
    edited = stretch(
        st.data_editor, df,
        key=editor_key, hide_index=True,
        disabled=[c for c in df.columns if c != "Reading"],
        column_config={"Reading": st.column_config.NumberColumn(
            "Reading (analyzer units)", min_value=0.0, format="%.3f",
            help="Type the value shown on your analyzer. Units: Ω for earth resistance, mA for earth leakage, µA for the rest.")},
    )
    # Save what was typed back to the readings, keyed by test id.
    for rid, val in zip(ids, edited["Reading"].tolist()):
        if val is None or pd.isna(val):
            readings.pop(rid, None)
        else:
            readings[rid] = float(val)

    result = pd.DataFrame({
        "Test": [sc.row_label(r) for r in rows],
        "Limit": [sc.limit_text(r) for r in rows],
        "Reading": [
            f"{readings[r['id']]:g} {sc.KINDS[r['kind']]['unit']}" if r["id"] in readings else "—" for r in rows],
        "% of limit": [round(sc.percent_of_limit(r, readings[r["id"]])) if r["id"] in readings else None for r in rows],
        "Result": [
            ("Pass" if sc.is_pass(r, readings[r["id"]]) else "FAIL") if r["id"] in readings else "—" for r in rows],
    })
    st.subheader("Results against limit")

    def colour(val):
        if val == "FAIL":
            return "color: #B3261E; font-weight: 700"
        if val == "Pass":
            return "color: #1B7F45; font-weight: 600"
        return ""

    try:
        styled = result.style.map(colour, subset=["Result"])
    except AttributeError:      # pandas older than 2.1
        styled = result.style.applymap(colour, subset=["Result"])
    stretch(st.dataframe, styled, hide_index=True)
    if st.session_state["note"]:
        st.caption(st.session_state["note"])
    st.caption(
        "NC = normal condition. SFC = single fault condition (open earth, open neutral, or mains on the applied part). "
        "Limits are the general IEC 60601-1 values: check them against the edition and test sheet your lab uses. "
        "Protective earth resistance uses 0.2 Ω, which assumes a detachable mains cord."
    )

# ---------- summary (filled after the editor so it reflects the latest edits) ----------
s = sc.summarize(rows, readings)
with summary_box:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests", s["total"])
    c2.metric("Recorded", s["tested"])
    c3.metric("Passed", s["passed"])
    c4.metric("Failed", s["failed"])
    if s["verdict"] == "none":
        st.info("No readings yet. Enter a value in the test matrix or use the virtual device.")
    elif s["verdict"] == "fail":
        st.error(f"FAIL: {s['failed']} of {s['tested']} recorded tests are outside the limit. "
                 "Take the device out of service until it is repaired and the full set of tests is repeated.")
    elif s["verdict"] == "progress":
        st.warning(f"In progress: {s['tested']} of {s['total']} tests recorded, none failed so far.")
    else:
        st.success(f"PASS: all {s['total']} tests are inside their limits for this class and applied part type.")
    if s["worst"]:
        st.caption(f"Closest to its limit: {sc.row_label(s['worst'][0])} at {round(s['worst'][1])}% of the limit.")

# ---------- circuit ----------
with tab_circuit:
    labels = {r["id"]: f"{i + 1}. {sc.row_label(r)}" for i, r in enumerate(rows)}
    pick = st.selectbox("Test", ids, format_func=labels.get)
    row = next(r for r in rows if r["id"] == pick)
    left, right = st.columns([3, 2])
    with left:
        st.graphviz_chart(sc.circuit_dot(row, cls, ap))
    with right:
        st.subheader(sc.KINDS[row["kind"]]["title"])
        st.write(sc.EXPLAIN[row["kind"]])
        conds = []
        if row["pol"] == "R":
            conds.append("supply polarity reversed")
        if row["earth"] == "O":
            conds.append("protective earth open")
        if row["neut"] == "O":
            conds.append("neutral open")
        if conds:
            st.write("**Conditions applied:** " + ", ".join(conds) + ".")
        st.write(f"**Limit:** {sc.limit_text(row)}")
        if pick in readings:
            v = readings[pick]
            st.metric("Recorded reading", f"{v:g} {sc.KINDS[row['kind']]['unit']}",
                      delta=f"{round(sc.percent_of_limit(row, v))}% of limit", delta_color="off")
        if st.button("Measure this test (virtual)"):
            readings[pick] = sc.virtual_reading(row, preset, ap)
            st.session_state["ver"] += 1
            st.session_state["note"] = f"Readings were produced by the virtual device ({preset})."
            st.rerun()

# ---------- report ----------
with tab_report:
    text = sc.report_text(info, cls, ap, rows, readings)
    st.code(text, language=None)
    d1, d2 = st.columns(2)
    d1.download_button("Download report (.txt)", text, file_name="safety_report.txt", mime="text/plain")
    csv = pd.DataFrame({
        "test": [sc.KINDS[r["kind"]]["short"] for r in rows],
        "mode": [r["mode"] for r in rows],
        "polarity": [r["pol"] for r in rows],
        "earth": [r["earth"] for r in rows],
        "neutral": [r["neut"] for r in rows],
        "limit": [r["limit"] for r in rows],
        "unit": [sc.KINDS[r["kind"]]["unit"] for r in rows],
        "reading": [readings.get(r["id"]) for r in rows],
    }).to_csv(index=False)
    d2.download_button("Download readings (.csv)", csv, file_name="safety_readings.csv", mime="text/csv")

# ---------- guide ----------
with tab_guide:
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("""
**Aim**
To measure protective earth resistance and leakage currents of a medical electrical device with an electrical safety analyzer, and to judge the device against IEC 60601-1 limits.

**Apparatus**
- Electrical safety analyzer with test socket and applied part terminals
- Device under test with its mains cord
- Applied part leads or adapter (for BF and CF parts)
- Mains supply protected by an RCD

**Theory**
- **Earth leakage** flows along the protective earth conductor back to the supply.
- **Touch (enclosure) leakage** would flow through a person touching the enclosure.
- **Patient leakage** would flow from the applied part, through the patient, to earth.
- **Mains on applied part** checks what happens if mains voltage reaches an F-type applied part.
- The **measuring device (MD)** is a 1 kΩ resistor in series with a 10 kΩ resistor and 0.015 µF capacitor in parallel. It makes the reading follow the way the body responds to current at different frequencies.
- Type B parts are body-referenced, BF are floating, and CF are floating with the tightest limits because they may touch the heart.
""")
    with g2:
        st.markdown("""
**Procedure**
1. Inspect the device, cord and plug, then fill in the device details in the sidebar.
2. Plug the device into the analyzer test socket and connect the applied part leads.
3. For Class I devices, measure protective earth resistance first.
4. Work down the matrix. For each row, set the analyzer to that polarity and fault, wait for the reading to settle, then enter it.
5. Check the result column. Any value above its limit is a failure.
6. If any test fails, stop, tag the device out of service and report it. Repair it and repeat the full set.
7. Download the report for your lab record.

**Precautions**
- Never touch the enclosure or applied parts while a test is running.
- Create open earth, open neutral and reversed polarity only with the analyzer's own switches.
- Do not connect a patient or any other equipment during testing.
- The virtual device is for practice. On the real experiment, record the values your analyzer shows.

**Viva questions**
- Why are the limits higher in single fault condition?
- Why is the CF limit lower than BF?
- What does opening the earth do to touch current?
- Why is the measuring device not a plain resistor?
""")
