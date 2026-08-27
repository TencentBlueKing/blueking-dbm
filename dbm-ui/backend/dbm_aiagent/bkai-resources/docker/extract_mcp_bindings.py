#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 config.py 的 BK_APIGW_STAGE_MCP_SERVERS 提取 name / target_app_codes。

仅收集字符串字面量；``env.APP_CODE`` 等非字面量直接跳过（不是智能体 code）。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


def _str_const(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_servers(config_path: Path) -> list[dict]:
    tree = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    servers_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "BK_APIGW_STAGE_MCP_SERVERS":
                    servers_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "BK_APIGW_STAGE_MCP_SERVERS":
                servers_node = node.value

    if not isinstance(servers_node, ast.List):
        raise RuntimeError("BK_APIGW_STAGE_MCP_SERVERS 未找到或不是 list")

    servers = []
    for item in servers_node.elts:
        if not isinstance(item, ast.Dict):
            continue
        name, codes = None, []
        for k, v in zip(item.keys, item.values):
            key = _str_const(k)
            if key == "name":
                name = _str_const(v)
            elif key == "target_app_codes" and isinstance(v, (ast.List, ast.Tuple)):
                codes = [c for c in (_str_const(x) for x in v.elts) if c]
        if name:
            servers.append({"name": name, "target_app_codes": codes})
    return servers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    servers = extract_servers(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"servers": servers}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"extracted {len(servers)} mcp servers -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
