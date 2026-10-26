#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load agents/*.yaml → 按 bindings 填充 spec.mcps → dump 覆盖。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def mcps_for(agent_code: str, servers: list, gateway: str, stage: str) -> list[dict]:
    return [
        {"type": "apigw", "code": f"{gateway}-{stage}-{s['name']}"}
        for s in servers
        if agent_code in (s.get("target_app_codes") or [])
    ]


def render(package: Path, bindings: Path, gateway: str, stage: str) -> None:
    servers = json.loads(bindings.read_text(encoding="utf-8"))["servers"]
    for path in sorted(package.joinpath("agents").glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        agent_code = data["metadata"]["code"]
        mcps = mcps_for(agent_code, servers, gateway, stage)
        data.setdefault("spec", {})["mcps"] = mcps
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        print(f"rendered {path.name}: agent_code={agent_code}, mcps={len(mcps)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--bindings", type=Path, required=True)
    p.add_argument("--gateway", required=True)
    p.add_argument("--stage", required=True)
    args = p.parse_args()
    try:
        render(args.package, args.bindings, args.gateway, args.stage)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
