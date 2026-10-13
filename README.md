# Electrical Safety Analyzer Lab

A Streamlit app for the lab experiment on testing a medical electrical device with an electrical safety analyzer. You record earth resistance and leakage current readings, and the app checks each one against the IEC 60601-1 general limits and gives an overall pass or fail.

## What it does

- Builds the list of tests for the device's protection class (I or II) and applied part type (none, B, BF or CF).
- Lets you type the reading from your analyzer into each row and shows pass or fail, the percentage of the limit used, and an overall verdict.
- Includes a **virtual device** with four practice presets, so you can rehearse the experiment without hardware.
- Draws the test circuit for any selected test, with the measuring path highlighted.
- Produces a report you can download as text, and the readings as CSV.
- Has the aim, theory, procedure, precautions and viva questions in an Experiment guide tab.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | The Streamlit interface |
| `safety_core.py` | Test list, limits, virtual device, verdict logic, report text and circuit diagram source. No Streamlit code, so it can be tested on its own. |
| `test_core.py` | Automated checks for `safety_core.py` |
| `requirements.txt` | Python packages needed |

## Install and run

You need Python 3.9 or newer.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens the app in your browser, usually at `http://localhost:8501`.

To run the checks on the test logic (these do not need Streamlit):

```bash
python test_core.py
```

## How to use it

1. In the sidebar, enter the device details, then choose the protection class and applied part type. The test matrix rebuilds to match.
2. In the **Test matrix** tab, enter each reading from your analyzer in the Reading column. Units are Ω for earth resistance, mA for earth leakage and µA for everything else.
3. Read the Results table and the summary at the top. Any value above its limit shows as a failure.
4. Open the **Circuit** tab to see how a selected test is connected and what it measures.
5. Open the **Report** tab and download the report or the CSV for your lab record.

To practise first, pick a preset under **Virtual device** in the sidebar and press **Measure all (virtual)**. The app starts with a sample run from the healthy device, so press **Clear all** before you enter real readings.

### Virtual device presets

| Preset | What it simulates | Expected outcome |
| --- | --- | --- |
| Healthy device | Typical good readings | Pass |
| Worn insulation | High earth leakage | Fail (Class I) |
| Damaged earth lead | High protective earth resistance | Fail on PE resistance only |
| Failed applied part | High patient leakage and mains-on-applied-part current | Fail |

Readings include a small random variation, so they change slightly each time.

## Limits used

These are the general IEC 60601-1 values. Check them against the edition of the standard and the test sheet your lab uses before relying on them.

| Test | Normal condition (NC) | Single fault condition (SFC) |
| --- | --- | --- |
| Protective earth resistance (Class I) | 0.2 Ω | not applicable |
| Earth leakage (Class I) | 5 mA | 10 mA |
| Touch (enclosure) leakage | 100 µA | 500 µA |
| Patient leakage, type B and BF | 100 µA | 500 µA |
| Patient leakage, type CF | 10 µA | 50 µA |
| Mains on applied part, type BF | not applicable | 5000 µA |
| Mains on applied part, type CF | not applicable | 50 µA |

Notes:

- Single fault conditions are open neutral, and for Class I devices also open earth (touch and patient leakage only).
- Every NC and SFC test is repeated with normal and reversed supply polarity.
- The 0.2 Ω earth resistance limit assumes a detachable mains cord.
- Not covered: patient auxiliary current and insulation resistance tests.

## Safety

This app records and judges readings. It does not control any equipment.

- Never touch the enclosure or applied parts while a test is running.
- Create open earth, open neutral and reversed polarity only with the analyzer's own switches.
- Do not connect a patient or other equipment during testing.
- If any test fails, take the device out of service and report it. Repair it and repeat the full set of tests.
- The virtual device is for practice only. Record the values your analyzer shows.
