import random
import safety_core as sc

# Row counts
assert len(sc.build_rows("I", "BF")) == 1 + 4 + 6 + 6 + 2
assert len(sc.build_rows("II", "none")) == 4          # touch NC x2 + SFC neutral open x2
assert len(sc.build_rows("I", "B")) == 1 + 4 + 6 + 6  # no mains-on-applied-part for type B
assert len({r["id"] for r in sc.build_rows("I", "CF")}) == len(sc.build_rows("I", "CF"))

# Limits
by = {r["id"]: r for r in sc.build_rows("I", "CF")}
assert by["pe_NA_NCC"]["limit"] == 0.2
assert by["pat_NC_NCC"]["limit"] == 10 and by["pat_SFC_NOC"]["limit"] == 50
assert by["map_SFC_NCC"]["limit"] == 50
assert {r["limit"] for r in sc.build_rows("I", "BF") if r["kind"] == "map"} == {5000}

# Healthy device passes everything, every other preset fails something (BF and CF)
rng = random.Random(1)
for ap in ("B", "BF", "CF"):
    for cls in ("I", "II"):
        rows = sc.build_rows(cls, ap)
        rd = {r["id"]: sc.virtual_reading(r, "Healthy device", ap, rng) for r in rows}
        assert sc.summarize(rows, rd)["verdict"] == "pass", (cls, ap, sc.summarize(rows, rd))
        for name in ("Worn insulation", "Failed applied part"):
            rd = {r["id"]: sc.virtual_reading(r, name, ap, rng) for r in rows}
            if name == "Failed applied part" and ap == "B":
                continue          # type B has no mains-on-applied-part test
            if name == "Worn insulation" and cls == "II":
                continue          # shows up as earth leakage, which Class II does not have
            assert sc.summarize(rows, rd)["verdict"] == "fail", (name, cls, ap)
rows = sc.build_rows("I", "BF")
rd = {r["id"]: sc.virtual_reading(r, "Damaged earth lead", "BF", rng) for r in rows}
s = sc.summarize(rows, rd)
assert s["verdict"] == "fail" and s["failed"] == 1 and s["worst"][0]["kind"] == "pe"

# Partial and empty
assert sc.summarize(rows, {})["verdict"] == "none"
assert sc.summarize(rows, {rows[0]["id"]: 0.05})["verdict"] == "progress"
assert sc.is_pass(rows[0], 0.2) and not sc.is_pass(rows[0], 0.201)

# Report and diagram build for every test
txt = sc.report_text({"name": "Monitor"}, "I", "BF", rows, rd)
assert "Overall: FAIL" in txt and txt.count("\n") > len(rows)
for cls in ("I", "II"):
    for ap in ("none", "B", "BF", "CF"):
        for r in sc.build_rows(cls, ap):
            dot = sc.circuit_dot(r, cls, ap)
            assert dot.startswith("digraph") and dot.rstrip().endswith("}")
print("ALL CORE TESTS PASSED")
