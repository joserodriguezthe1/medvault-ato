#!/usr/bin/env python3
"""
evidence-to-oscal.py

Transforms SARIF output from Checkov and Trivy into an OSCAL Assessment
Results document. This is the bridge from raw scanner output to
machine-readable compliance evidence.

Usage:
    python evidence-to-oscal.py \
        --checkov-sarif checkov-results/results_sarif.sarif \
        --trivy-sarif trivy-results.sarif \
        --commit abc123 \
        --run-id 12345 \
        --output oscal/assessment-results/run-12345.json
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------------
# Mapping: scanner rule -> NIST 800-53 controls
# ----------------------------------------------------------------------------

CHECKOV_TO_CONTROLS: dict[str, list[str]] = {
    # KMS / encryption -> SC-13
    "CKV_AWS_7":   ["sc-12", "sc-13"],
    "CKV_AWS_19":  ["sc-13", "sc-28"],
    "CKV_AWS_145": ["sc-13"],
    "CKV2_AWS_64": ["sc-13"],
    # Public access blocks -> CM-6 + AC-3
    "CKV_AWS_53":  ["cm-6", "ac-3"],
    "CKV_AWS_54":  ["cm-6", "ac-3"],
    "CKV_AWS_55":  ["cm-6", "ac-3"],
    "CKV_AWS_56":  ["cm-6", "ac-3"],
    # Logging rules -> AU-2
    "CKV_AWS_18":  ["au-2"],
    "CKV_AWS_35":  ["au-2"],
    # Versioning + lifecycle
    "CKV_AWS_21":  ["cm-6"],
    "CKV2_AWS_61": ["au-11"],
    # Replication -> CP-9
    "CKV_AWS_144": ["cp-9"],
    # Event notifications -> SI-4
    "CKV2_AWS_62": ["si-4"],
}

TRIVY_CONTROLS = ["ra-5", "si-2"]
DEFAULT_CONTROLS = ["cm-6"]

SEVERITY_MAP = {
    "error":   "high",
    "warning": "medium",
    "note":    "low",
    "none":    "low",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_uuid() -> str:
    return str(uuid.uuid4())


def load_sarif(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"runs": []}
    return json.loads(path.read_text())


def controls_for_rule(rule_id: str, source: str) -> list[str]:
    if source == "trivy":
        return TRIVY_CONTROLS
    return CHECKOV_TO_CONTROLS.get(rule_id, DEFAULT_CONTROLS)


def sarif_to_observations_and_findings(
    sarif: dict[str, Any], source: str
) -> tuple[list[dict], list[dict]]:
    observations: list[dict] = []
    findings: list[dict] = []

    for run in sarif.get("runs", []):
        tool_name = run.get("tool", {}).get("driver", {}).get("name", source)

        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")
            level = result.get("level", "warning")
            message = result.get("message", {}).get("text", "")
            location = ""
            locs = result.get("locations", [])
            if locs:
                location = (
                    locs[0]
                    .get("physicalLocation", {})
                    .get("artifactLocation", {})
                    .get("uri", "")
                )

            control_ids = controls_for_rule(rule_id, source)

            obs_uuid = new_uuid()
            observations.append({
                "uuid": obs_uuid,
                "title": f"{tool_name}: {rule_id}",
                "description": message,
                "methods": ["TEST-AUTOMATED"],
                "types": ["finding"],
                "origins": [{
                    "actors": [{
                        "type": "tool",
                        "actor-uuid": new_uuid(),
                    }],
                }],
                "props": [
                    {"name": "tool", "value": tool_name},
                    {"name": "rule-id", "value": rule_id},
                    {"name": "location", "value": location},
                ],
                "collected": now_utc(),
            })

            for control_id in control_ids:
                findings.append({
                    "uuid": new_uuid(),
                    "title": f"{rule_id} affects {control_id.upper()}",
                    "description": (
                        f"{tool_name} reported '{rule_id}' against {location}. "
                        f"This is mapped to control {control_id.upper()}."
                    ),
                    "target": {
                        "type": "objective-id",
                        "target-id": f"{control_id}_obj",
                        "status": {"state": "not-satisfied"},
                    },
                    "related-observations": [{"observation-uuid": obs_uuid}],
                    "props": [
                        {"name": "severity", "value": SEVERITY_MAP.get(level, "medium")},
                        {"name": "control-id", "value": control_id},
                    ],
                })

    return observations, findings


def build_assessment_results(
    commit: str,
    run_id: str,
    checkov_path: Path | None,
    trivy_path: Path | None,
) -> dict[str, Any]:

    checkov_sarif = load_sarif(checkov_path)
    trivy_sarif = load_sarif(trivy_path)

    obs_a, find_a = sarif_to_observations_and_findings(checkov_sarif, "checkov")
    obs_b, find_b = sarif_to_observations_and_findings(trivy_sarif, "trivy")

    all_observations = obs_a + obs_b
    all_findings = find_a + find_b

    reviewed_controls = sorted({
        p["value"]
        for f in all_findings
        for p in f["props"]
        if p["name"] == "control-id"
    })

    return {
        "assessment-results": {
            "uuid": new_uuid(),
            "metadata": {
                "title": f"MedVault CI Assessment - Run {run_id}",
                "last-modified": now_utc(),
                "version": "0.1.0",
                "oscal-version": "1.1.2",
                "props": [
                    {"name": "commit-sha", "value": commit},
                    {"name": "ci-run-id", "value": run_id},
                ],
            },
            "import-ap": {
                "href": "../assessment-plans/medvault-ap.json",
            },
            "results": [{
                "uuid": new_uuid(),
                "title": f"Pipeline assessment for commit {commit[:7]}",
                "description": (
                    "Automated control assessment generated from "
                    "Checkov (IaC) and Trivy (container) SARIF output."
                ),
                "start": now_utc(),
                "end": now_utc(),
                "reviewed-controls": {
                    "control-selections": [{
                        "include-controls": [
                            {"control-id": c} for c in reviewed_controls
                        ],
                    }],
                },
                "observations": all_observations,
                "findings": all_findings,
            }],
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkov-sarif", type=Path, default=None)
    parser.add_argument("--trivy-sarif", type=Path, default=None)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    doc = build_assessment_results(
        commit=args.commit,
        run_id=args.run_id,
        checkov_path=args.checkov_sarif,
        trivy_path=args.trivy_sarif,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2))

    n_obs = len(doc["assessment-results"]["results"][0]["observations"])
    n_find = len(doc["assessment-results"]["results"][0]["findings"])
    print(f"[ok] wrote {args.output}")
    print(f"[ok] {n_obs} observations, {n_find} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())