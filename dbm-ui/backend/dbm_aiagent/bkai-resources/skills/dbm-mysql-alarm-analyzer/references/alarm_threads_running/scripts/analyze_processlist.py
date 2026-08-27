#!/usr/bin/env python3
"""MySQL Processlist Analyzer

Analyze MySQL processlist data from a JSON file using various aggregation dimensions.
Output is always JSON, intended to be read and formatted by an LLM.

Usage:
    python analyze_processlist.py <input_json_file> [--type <aggregate_type>]

Aggregate types:
    summary              - Overview + top users/IPs/fingerprints/DBs + longest + lock_wait (default)
    all                  - All dimensions including state breakdown
    group_by_fingerprint - Top SQL fingerprints
    group_by_state       - State breakdown
    group_by_user        - Top users
    group_by_client_host - Top client IPs
    group_by_db          - Top databases
    lock_wait            - Lock-waiting connections
    longest_top_5        - Longest running queries
    sample               - Active connections sample (max 30) for LLM free-form analysis
"""

import argparse
import json
import sys

import pandas as pd

SYSTEM_USERS = {"repl", "system user", "MONITOR"}
IGNORED_COMMANDS = {"Sleep", "Binlog Dump"}
TOP_N = 5
LOCK_WAIT_KEYWORDS = [
    "waiting for table metadata lock",
    "waiting for lock",
    "waiting for handler commit",
    "waiting for table flush",
]


def load_processlist(input_file: str) -> list:
    """Load processlist data from a JSON file."""
    with open(input_file, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("Error: JSON file must contain a list of processlist entries.", file=sys.stderr)
        sys.exit(1)
    return data


def extract_ip(source_host: str) -> str:
    """Extract IP from source_host (ip:port format)."""
    if not source_host:
        return ""
    parts = source_host.rsplit(":", 1)
    return parts[0] if parts else source_host


def analyze(processlist: list, aggregate_type: str) -> dict:
    """Analyze processlist, return structured JSON result."""
    if not processlist:
        return {}

    df = pd.DataFrame(processlist)

    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)

    results = {}

    total = len(df)

    # --- overview (summary / all) ---
    if aggregate_type in ("summary", "all"):
        cmd_counts = df["command"].value_counts()
        results["overview"] = {
            "total": total,
            "by_command": {
                cmd: {"count": int(cnt), "pct": round(cnt / total * 100, 1)} for cmd, cnt in cmd_counts.items()
            },
        }

    # --- top N fingerprints ---
    if aggregate_type in ("group_by_fingerprint", "summary", "all"):
        results["top_fingerprints"] = (
            df.groupby("fingerprint")
            .agg(count=("fingerprint", "size"), avg_time=("time", "mean"))
            .nlargest(TOP_N, "count")
            .reset_index()
            .to_dict(orient="records")
        )

    # --- state breakdown ---
    if aggregate_type in ("group_by_state", "all"):
        results["by_state"] = df["state"].value_counts().to_dict()

    # --- top N users ---
    if aggregate_type in ("group_by_user", "summary", "all"):
        user_counts = df["user"].value_counts().head(TOP_N)
        results["top_users"] = [
            {"user": user, "count": int(cnt), "pct": round(cnt / total * 100, 1)} for user, cnt in user_counts.items()
        ]

    # --- top N client IPs ---
    if aggregate_type in ("group_by_client_host", "summary", "all"):
        df["client_ip"] = df["source_host"].apply(extract_ip)
        ip_counts = df["client_ip"].value_counts().head(TOP_N)
        results["top_client_ips"] = [
            {"ip": ip, "count": int(cnt), "pct": round(cnt / total * 100, 1)} for ip, cnt in ip_counts.items()
        ]

    # --- longest top N (excluding sleep / system users) ---
    if aggregate_type in ("longest_top_5", "summary", "all"):
        filtered = df[(~df["command"].isin(IGNORED_COMMANDS)) & (df["time"] > 0) & (~df["user"].isin(SYSTEM_USERS))]
        top5 = filtered.nlargest(TOP_N, "time")[
            ["id", "user", "db", "command", "fingerprint", "info", "time", "state", "source_host"]
        ].to_dict(orient="records")
        results["longest_queries"] = top5

    # --- top N databases ---
    if aggregate_type in ("group_by_db", "summary", "all"):
        db_col = df["db"].fillna("未指定").replace("", "未指定")
        db_counts = db_col.value_counts().head(TOP_N)
        results["top_dbs"] = [
            {"db": db, "count": int(cnt), "pct": round(cnt / total * 100, 1)} for db, cnt in db_counts.items()
        ]

    # --- lock wait detection ---
    if aggregate_type in ("lock_wait", "summary", "all"):
        pattern = "|".join(LOCK_WAIT_KEYWORDS)
        mask = df["state"].str.lower().str.contains(pattern, na=False)
        locked = df[mask]
        results["lock_wait"] = {
            "count": int(len(locked)),
            "connections": locked[["id", "user", "source_host", "db", "time", "state", "info"]].to_dict(
                orient="records"
            )
            if len(locked) > 0
            else [],
        }

    return results


SAMPLE_LIMIT = 30
SAMPLE_FIELDS = ["id", "user", "source_host", "db", "command", "time", "state", "fingerprint", "info"]


def sample_active(processlist: list) -> dict:
    """Return a sample of active connections for LLM free-form analysis."""
    if not processlist:
        return {"total": 0, "sampled": 0, "connections": []}

    df = pd.DataFrame(processlist)
    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)

    active = df[(~df["command"].isin(IGNORED_COMMANDS)) & (~df["user"].isin(SYSTEM_USERS))].copy()

    active = active.sort_values("time", ascending=False)

    cols = [c for c in SAMPLE_FIELDS if c in active.columns]
    sampled = active.head(SAMPLE_LIMIT)[cols]

    return {
        "total": len(df),
        "active_total": len(active),
        "sampled": len(sampled),
        "connections": sampled.to_dict(orient="records"),
    }


def main():
    parser = argparse.ArgumentParser(description="MySQL Processlist Analyzer")
    parser.add_argument("input_file", help="Path to JSON file containing processlist data")
    parser.add_argument(
        "--type",
        dest="aggregate_type",
        default="summary",
        choices=[
            "summary",
            "all",
            "group_by_fingerprint",
            "group_by_state",
            "group_by_user",
            "group_by_client_host",
            "group_by_db",
            "lock_wait",
            "longest_top_5",
            "sample",
        ],
        help="Aggregation type (default: summary)",
    )
    args = parser.parse_args()

    processlist = load_processlist(args.input_file)
    if args.aggregate_type == "sample":
        results = sample_active(processlist)
    else:
        results = analyze(processlist, args.aggregate_type)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
