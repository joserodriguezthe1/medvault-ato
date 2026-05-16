"""MedVault Continuous Monitoring Dashboard"""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE / "oscal" / "assessment-results"
POAM_FILE = BASE / "oscal" / "poam" / "medvault-poam.json"

CONTROL_FAMILIES = {
    "ac": "Access Control", "au": "Audit & Accountability",
    "ca": "Assessment, Authorization & Monitoring", "cm": "Configuration Management",
    "cp": "Contingency Planning", "ia": "Identification & Authentication",
    "ra": "Risk Assessment", "sa": "System & Services Acquisition",
    "sc": "System & Communications Protection", "si": "System & Information Integrity",
    "sr": "Supply Chain Risk Management",
}


@st.cache_data(ttl=30)
def load_assessment_results():
    if not RESULTS_DIR.exists():
        return []
    docs = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
            doc["_source_file"] = path.name
            docs.append(doc)
        except json.JSONDecodeError:
            pass
    return docs


@st.cache_data(ttl=30)
def load_poam():
    if not POAM_FILE.exists():
        return None
    try:
        return json.loads(POAM_FILE.read_text())
    except json.JSONDecodeError:
        return None


def prop(item, name, default=""):
    return next((p["value"] for p in item.get("props", []) if p["name"] == name), default)


def aging_bucket(due_str, status):
    if status == "risk-accepted":
        return "Risk Accepted"
    if not due_str:
        return "No due date"
    try:
        due = datetime.strptime(due_str, "%Y-%m-%d").date()
    except ValueError:
        return "No due date"
    days = (due - date.today()).days
    if days < 0:
        return f"Overdue ({-days}d)"
    if days <= 30:
        return f"Due <=30d ({days}d)"
    if days <= 90:
        return f"Due <=90d ({days}d)"
    return f"Due >90d ({days}d)"


st.set_page_config(page_title="MedVault ConMon", layout="wide")
st.title("MedVault Continuous Monitoring")
st.caption("FedRAMP Moderate | NIST 800-53 Rev 5 | OSCAL-native | RMF Step 6")

tab_posture, tab_poam = st.tabs(["Control Posture", "POA&M"])

with tab_posture:
    docs = load_assessment_results()
    if not docs:
        st.info("No Assessment Results yet.")
    else:
        latest = max(docs, key=lambda d: d["assessment-results"]["metadata"]["last-modified"])
        result = latest["assessment-results"]["results"][0]
        reviewed = {c["control-id"] for c in result["reviewed-controls"]["control-selections"][0]["include-controls"]}
        by_control = defaultdict(lambda: {"high": 0, "medium": 0, "low": 0})
        for f in result.get("findings", []):
            cid = prop(f, "control-id")
            sev = prop(f, "severity", "medium")
            if cid:
                by_control[cid][sev] += 1
        rows = []
        for cid in sorted(reviewed):
            counts = by_control.get(cid, {"high": 0, "medium": 0, "low": 0})
            status = "Not Satisfied" if counts["high"] else ("Partial" if counts["medium"] or counts["low"] else "Satisfied")
            rows.append({
                "Control": cid.upper(),
                "Family": CONTROL_FAMILIES.get(cid.split("-")[0], cid.upper()),
                "Status": status,
                "High": counts["high"], "Medium": counts["medium"], "Low": counts["low"],
            })
        posture_df = pd.DataFrame(rows)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Assessment Runs", len(docs))
        c2.metric("Satisfied", int((posture_df["Status"] == "Satisfied").sum()))
        c3.metric("Partial", int((posture_df["Status"] == "Partial").sum()))
        c4.metric("Not Satisfied", int((posture_df["Status"] == "Not Satisfied").sum()))
        st.caption(f"Latest run: {latest['_source_file']}")
        st.markdown("### Control Status")
        st.dataframe(posture_df, use_container_width=True, hide_index=True)

with tab_poam:
    poam = load_poam()
    if not poam:
        st.info("No POA&M found.")
    else:
        rows = []
        for item in poam["plan-of-action-and-milestones"]["poam-items"]:
            status = prop(item, "status", "open")
            due = prop(item, "scheduled-completion-date", "")
            rows.append({
                "ID": item["title"].split(":")[0] if ":" in item["title"] else item["uuid"][:8],
                "Title": item["title"].split(":", 1)[1].strip() if ":" in item["title"] else item["title"],
                "Severity": prop(item, "severity"),
                "Control": prop(item, "control-id").upper(),
                "Status": status,
                "Aging": aging_bucket(due, status),
                "Due": due or "-",
                "Source": prop(item, "weakness-source"),
            })
        poam_df = pd.DataFrame(rows)
        total = len(poam_df)
        overdue = sum(1 for a in poam_df["Aging"] if a.startswith("Overdue"))
        risk_accepted = int((poam_df["Status"] == "risk-accepted").sum())
        open_high = int(((poam_df["Status"] == "open") & (poam_df["Severity"] == "high")).sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Items", total)
        c2.metric("Overdue", overdue)
        c3.metric("Open High-Sev", open_high)
        c4.metric("Risk Accepted", risk_accepted)
        st.markdown("### Aging")
        st.bar_chart(poam_df["Aging"].apply(lambda a: a.split(" (")[0]).value_counts())
        st.markdown("### POA&M Items")
        st.dataframe(poam_df, use_container_width=True, hide_index=True)