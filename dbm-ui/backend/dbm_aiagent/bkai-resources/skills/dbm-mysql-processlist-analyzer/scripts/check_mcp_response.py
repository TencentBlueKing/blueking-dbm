#!/usr/bin/env python3
"""check_mcp_response.py

Validate the raw JSON output from dbm-mcp-cli and extract the processlist array
into a separate file for downstream analysis.

Usage:
    python3 check_mcp_response.py <raw_json_file> [--out <output_file>]

Exit codes:
    0  success — processlist extracted and written to output file
    1  error   — validation failed, details printed to stderr
"""

import argparse
import json
import os
import sys


def load_raw(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_and_extract(data: dict) -> list:
    # Check top-level MCP response code
    code = data.get("response_body", {}).get("code")
    if code is None:
        print("ERROR: missing response_body.code — unexpected response structure", file=sys.stderr)
        print(f"       keys found: {list(data.keys())}", file=sys.stderr)
        sys.exit(1)

    if code != 0:
        msg = data.get("response_body", {}).get("message", "(no message)")
        print(f"ERROR: MCP returned error code {code}: {msg}", file=sys.stderr)
        sys.exit(1)

    # Extract processlist
    try:
        processlist = data["response_body"]["data"]["processlist"]
    except KeyError as e:
        print(f"ERROR: missing expected field {e} in response", file=sys.stderr)
        sys.exit(1)

    if not isinstance(processlist, list):
        print(f"ERROR: processlist is not a list (got {type(processlist).__name__})", file=sys.stderr)
        sys.exit(1)

    return processlist


def main():
    parser = argparse.ArgumentParser(description="Validate dbm-mcp-cli output and extract processlist")
    parser.add_argument("raw_file", help="Raw JSON file from dbm-mcp-cli")
    default_out = os.path.join(os.environ.get("OUTPUT_DIR", "/app/.storage/session"), "processlist.json")
    parser.add_argument("--out", default=default_out, help="Output processlist JSON file")
    args = parser.parse_args()

    data = load_raw(args.raw_file)
    processlist = validate_and_extract(data)

    with open(args.out, "w") as f:
        json.dump(processlist, f)

    print(f"OK: extracted {len(processlist)} connections -> {args.out}")


if __name__ == "__main__":
    main()
