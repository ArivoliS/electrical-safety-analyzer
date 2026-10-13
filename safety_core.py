"""Test logic for the Electrical Safety Analyzer lab (IEC 60601-1 general limits).

No Streamlit imports here, so the logic can be unit-tested on its own.
"""
import random

KINDS = {
    "pe":    {"title": "Protective earth resistance",              "short": "PE resistance",         "unit": "Ω",  "dec": 3},
    "el":    {"title": "Earth leakage current",                    "short": "Earth leakage",         "unit": "mA", "dec": 2},
    "touch": {"title": "Touch (enclosure) leakage current",        "short": "Touch current",         "unit": "µA", "dec": 1},
    "pat":   {"title": "Patient leakage current",                  "short": "Patient leakage",       "unit": "µA", "dec": 1},
    "map":   {"title": "Patient leakage, mains on applied part",   "short": "Mains on applied part", "unit": "µA", "dec": 0},
}

EXPLAIN = {
    "pe": "A test current is driven through the earth path, from the mains plug earth pin to the exposed metal of the device. The analyzer reports the resistance of that path.",
    "el": "Current that flows along the protective earth conductor back to the supply. The measuring device (MD) sits in the earth lead.",
    "touch": "Current that would pass through a person touching the enclosure while standing on earth. The MD joins the enclosure to earth.",
    "pat": "Current that would flow from the applied part, through the patient, to earth. The MD joins the applied part to earth.",
    "map": "A source at 110% of mains voltage is connected to the applied part. The MD measures the current that would flow through the patient to earth.",
}

# Virtual devices for practice: typical readings per test type.
PRESETS = {
    "Healthy device":      {"pe": 0.07, "el": 0.25, "touch": 14, "pat": 10, "map": {"BF": 620,  "CF": 18}},
    "Worn insulation":     {"pe": 0.09, "el": 4.6,  "touch": 65, "pat": 40, "map": {"BF": 900,  "CF": 22}},
    "Damaged earth lead":  {"pe": 0.58, "el": 0.35, "touch": 22, "pat": 12, "map": {"BF": 650,  "CF": 19}},
    "Failed applied part": {"pe": 0.08, "el": 0.3,  "touch": 15, "pat": 70, "map": {"BF": 5400, "CF": 55}},
}

AP_LABELS = {"none": "No applied part", "B": "Type B", "BF": "Type BF", "CF": "Type CF"}
CLASS_LABELS = {"I": "Class I (protective earth)", "II": "Class II (double insulated)"}


def build_rows(cls, ap):
    """Return the list of tests for a protection class and applied part type."""
    rows = []

    def add(kind, mode, pol, earth, neut, limit):
        rows.append({"id": f"{kind}_{mode}_{pol}{earth}{neut}", "kind": kind, "mode": mode,
                     "pol": pol, "earth": earth, "neut": neut, "limit": limit})

    if cls == "I":
        add("pe", "NA", "N", "C", "C", 0.2)
        add("el", "NC", "N", "C", "C", 5)
        add("el", "NC", "R", "C", "C", 5)
        add("el", "SFC", "N", "C", "O", 10)
        add("el", "SFC", "R", "C", "O", 10)

    def leak(kind, nc_limit, sfc_limit):
        add(kind, "NC", "N", "C", "C", nc_limit)
        add(kind, "NC", "R", "C", "C", nc_limit)
        if cls == "I":
            add(kind, "SFC", "N", "O", "C", sfc_limit)
            add(kind, "SFC", "R", "O", "C", sfc_limit)
        add(kind, "SFC", "N", "C", "O", sfc_limit)
        add(kind, "SFC", "R", "C", "O", sfc_limit)

    leak("touch", 100, 500)
    if ap != "none":
        leak("pat", 10 if ap == "CF" else 100, 50 if ap == "CF" else 500)
        if ap != "B":
            limit = 50 if ap == "CF" else 5000
            add("map", "SFC", "N", "C", "C", limit)
            add("map", "SFC", "R", "C", "C", limit)
    return rows


def limit_text(row):
    return f"≤ {row['limit']} {KINDS[row['kind']]['unit']}"


def row_label(row):
    s = KINDS[row["kind"]]["short"]
    if row["mode"] != "NA":
        s += f", {row['mode']}"
    s += ", reverse polarity" if row["pol"] == "R" else ", normal polarity"
    if row["earth"] == "O":
        s += ", earth open"
    if row["neut"] == "O":
        s += ", neutral open"
    return s


def is_pass(row, value):
    return value <= row["limit"]


def percent_of_limit(row, value):
    return value / row["limit"] * 100


def virtual_reading(row, preset_name, ap, rng=random):
    """A simulated analyzer reading for one test, with about ±1.5% noise."""
    p = PRESETS[preset_name]
    f = 1.1 if row["pol"] == "R" else 1.0
    kind = row["kind"]
    if kind == "pe":
        v = p["pe"]
    elif kind == "el":
        v = p["el"] * f * (2.1 if row["neut"] == "O" else 1)
    elif kind == "touch":
        v = p["touch"] * f
        if row["earth"] == "O":
            v *= 9
        if row["neut"] == "O":
            v *= 1.8
    elif kind == "pat":
        v = p["pat"] * f * (0.12 if ap == "CF" else 1)
        if row["earth"] == "O":
            v *= 7
        if row["neut"] == "O":
            v *= 1.7
    else:
        v = p["map"]["CF" if ap == "CF" else "BF"] * f
    v *= 1 + (rng.random() - 0.5) * 0.03
    return round(v, KINDS[kind]["dec"])


def summarize(rows, readings):
    """Counts, closest-to-limit test and overall verdict for the recorded readings."""
    tested = passed = failed = 0
    worst = None
    for r in rows:
        v = readings.get(r["id"])
        if v is None:
            continue
        tested += 1
        if is_pass(r, v):
            passed += 1
        else:
            failed += 1
        pc = percent_of_limit(r, v)
        if worst is None or pc > worst[1]:
            worst = (r, pc)
    if tested == 0:
        verdict = "none"
    elif failed:
        verdict = "fail"
    elif tested < len(rows):
        verdict = "progress"
    else:
        verdict = "pass"
    return {"total": len(rows), "tested": tested, "passed": passed, "failed": failed,
            "worst": worst, "verdict": verdict}


def report_text(info, cls, ap, rows, readings):
    def v(key):
        val = info.get(key)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return str(val if val is not None else "").strip() or "—"
    s = summarize(rows, readings)
    lines = [
        "ELECTRICAL SAFETY ANALYZER REPORT",
        f"Equipment: {v('name')} | Make and model: {v('model')} | Serial: {v('serial')}",
        f"Class: {cls} | Applied part: {AP_LABELS[ap]} | Mains: {v('mains')} V",
        f"Operator: {v('operator')} | Date: {v('date')}",
        "Limits: IEC 60601-1 general values",
        "",
        "Test | Mode | Polarity | Earth | Neutral | Limit | Reading | Result",
    ]
    for r in rows:
        K = KINDS[r["kind"]]
        x = readings.get(r["id"])
        lines.append(" | ".join([
            K["short"], "-" if r["mode"] == "NA" else r["mode"],
            "Reverse" if r["pol"] == "R" else "Normal",
            "Open" if r["earth"] == "O" else "Closed",
            "Open" if r["neut"] == "O" else "Closed",
            limit_text(r),
            f"{x} {K['unit']}" if x is not None else "not recorded",
            ("Pass" if is_pass(r, x) else "Fail") if x is not None else "-",
        ]))
    lines += ["", f"Overall: {s['verdict'].upper()} ({s['tested']} of {s['total']} recorded, {s['failed']} outside limit)"]
    return "\n".join(lines)


def circuit_dot(row, cls, ap):
    """Graphviz DOT source for the circuit of one test, with the active path in red."""
    kind = row["kind"]
    rev, eo, no = row["pol"] == "R", row["earth"] == "O", row["neut"] == "O"
    hot = "#D9462B"
    out = [
        "digraph G { rankdir=LR; bgcolor=transparent; nodesep=0.5; ranksep=0.9;",
        'node [shape=box, style="rounded,filled", fillcolor="#F7F8F9", color="#14181B", fontcolor="#14181B", fontname="Helvetica", fontsize=11];',
        'edge [color="#14181B", fontcolor="#14181B", fontname="Helvetica", fontsize=10, arrowhead=none];',
        f'L [label="Mains L"]; N [label="Mains N"];',
    ]
    pol_note = "polarity reversed" if rev else "polarity normal"
    l_label = "to N terminal (reversed)" if rev else "L"
    n_label = "to L terminal (reversed)" if rev else "N"
    l_style = f'color="{hot}", fontcolor="{hot}"' if rev else ""
    out.append(f'L -> DUT [label="{l_label}", {l_style}];')
    if no:
        out.append(f'N -> DUT [label="NEUTRAL OPEN", style=dashed, color="{hot}", fontcolor="{hot}"];')
    else:
        out.append(f'N -> DUT [label="{n_label}", {l_style}];')
    if cls == "I":
        out.append('PE [label="Mains PE"];')
        if eo:
            out.append(f'PE -> DUT [label="EARTH OPEN", style=dashed, color="{hot}", fontcolor="{hot}"];')
        else:
            out.append('PE -> DUT [label="PE"];')
    out.append(f'DUT [label="Device under test\\n{pol_note}", shape=box, width=2, height=1.4, fillcolor="#FFFFFF"];')
    out.append('EARTH [label="Earth", shape=plain, style="", fontcolor="#14181B"];')
    hl = f'color="{hot}", penwidth=3'
    if kind in ("pe", "el") and cls == "I":
        label = "Ω meter" if kind == "pe" else "MD"
        out.append(f'MD [label="{label}", shape=circle, color="{hot}", penwidth=3];')
        out.append(f'DUT -> MD [label="PE terminal", {hl}]; MD -> EARTH [{hl}];')
    elif kind == "touch":
        out.append('ENC [label="Enclosure", shape=plaintext];')
        out.append(f'MD [label="MD", shape=circle, color="{hot}", penwidth=3];')
        out.append(f'DUT -> ENC [style=dotted]; ENC -> MD [{hl}]; MD -> EARTH [{hl}];')
    elif kind in ("pat", "map") and ap != "none":
        out.append(f'APART [label="Applied part {ap}", shape=plaintext];')
        out.append(f'MD [label="MD", shape=circle, color="{hot}", penwidth=3];')
        out.append('DUT -> APART [style=dotted];')
        if kind == "map":
            out.append(f'SRC [label="110% mains\\nsource", color="{hot}", fontcolor="{hot}"];')
            out.append(f'SRC -> APART [{hl}];')
        out.append(f'APART -> MD [{hl}]; MD -> EARTH [{hl}];')
    out.append("}")
    return "\n".join(out)
