#!/usr/bin/env python3
"""Orchestrator for MySQL processlist analysis.

Handles topology parsing, tool selection, parallel fetching, extraction,
diagnosis, cross-verification, and cross-layer correlation.

Cluster mode:
    python run_analysis.py --cluster <domain> [--raw-query "<question>"]

Single instance mode:
    python run_analysis.py --instance <ip:port> [--proxy] [--bk-cloud-id N] [--raw-query "<question>"]
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", ".storage/session"))
MCP_SERVER = os.environ.get("MCP_SERVER", "bkdbm-mcp-prod-mysql-query")


def _log(msg: str):
    print(msg, file=sys.stderr)


def _mcp_call(tool: str, body: dict, raw_query: str, out_file: Path) -> bool:
    cmd = [
        "dbm-mcp-cli",
        "call",
        f"{MCP_SERVER}.{tool}",
        f"body_param={json.dumps(body, ensure_ascii=False)}",
        "--raw-query",
        raw_query,
    ]
    try:
        with open(out_file, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError as e:
        _log(f"  ERROR {tool}: {e.stderr.decode().strip()}")
        return False


def _py(script: str, args: list, out_file: Path = None) -> bool:
    cmd = ["python3", str(SCRIPT_DIR / script)] + args
    try:
        if out_file:
            with open(out_file, "w") as f:
                subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        else:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError as e:
        _log(f"  ERROR {script}: {e.stderr.decode().strip()}")
        return False


def _addr_safe(addr: str) -> str:
    return addr.replace(".", "_").replace(":", "_")


def _load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _diag_json_to_tsv(json_path: Path, tsv_path: Path):
    """Convert a proxy diagnostic JSON file to TSV format."""
    data = _load(json_path)
    lines = []
    lines.append(f"#diag\ttotal={data.get('total',0)}\tactive={data.get('active',0)}\tidle={data.get('idle',0)}")
    for finding in data.get("findings", []):
        lines.append(f"#finding\t{finding['type']}\t{finding.get('severity','')}\t{finding.get('title','')}")
        if finding.get("detail"):
            lines.append(f"\t{finding['detail']}")
        if finding.get("evidence"):
            ev = finding["evidence"]
            cols = ev.get("columns", [])
            rows = ev.get("rows", [])
            if cols:
                lines.append("\t".join(str(c) for c in cols))
                for row in rows:
                    lines.append("\t".join(str(x) if x is not None else "" for x in row))
        if finding.get("by_user"):
            bu = finding["by_user"]
            cols = bu.get("columns", [])
            rows = bu.get("rows", [])
            if cols:
                lines.append(f"#by_user")
                lines.append("\t".join(str(c) for c in cols))
                for row in rows:
                    lines.append("\t".join(str(x) if x is not None else "" for x in row))
        if finding.get("actions"):
            for act in finding["actions"]:
                lines.append(f"#action\t{act}")
        lines.append("")
    with open(tsv_path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ──────────────────────────────────────────────────────────────
# Phase 1: Topology
# ──────────────────────────────────────────────────────────────


def fetch_topology(cluster_domain: str, raw_query: str, all_remotes: bool = False) -> dict | None:
    tmp = OUTPUT_DIR / "_topo.json"
    if not _mcp_call("mysql_query_mysql_cluster_topo", {"cluster_domain": cluster_domain}, raw_query, tmp):
        return None

    data = _load(tmp)["response_body"]["data"]
    tmp.unlink(missing_ok=True)

    cluster_type = data.get("cluster_type", "")
    bk_cloud_id = data.get("bk_cloud_id", 0)
    seen_addrs = set()
    instances = []

    _topo_fields = ("is_stand_by", "bk_idc_name", "bk_sub_zone", "phase", "status")

    all_sets = data.get("storage_instance_replicate_sets", [])
    total_shards = len(all_sets)
    if cluster_type == "tendbcluster" and not all_remotes and total_shards > 1:
        storage_sets = all_sets[:1]
        sampled_remotes = True
    else:
        storage_sets = all_sets
        sampled_remotes = False

    for rs in storage_sets:
        m = rs["master_instance"]
        if m["address"] not in seen_addrs:
            seen_addrs.add(m["address"])
            inst = {
                "address": m["address"],
                "role": m.get("instance_role", "backend_master"),
                "type": "mysql",
                "bk_cloud_id": bk_cloud_id,
            }
            for k in _topo_fields:
                if k in m:
                    inst[k] = m[k]
            instances.append(inst)
        for s in rs.get("slave_instances", []):
            if s["address"] not in seen_addrs:
                seen_addrs.add(s["address"])
                base_role = s.get("instance_role", "backend_slave")
                if cluster_type == "tendbha" and base_role == "backend_slave":
                    if s.get("is_stand_by"):
                        base_role = "backend_slave_standby"
                    else:
                        base_role = "backend_slave_readonly"
                inst = {
                    "address": s["address"],
                    "role": base_role,
                    "type": "mysql",
                    "bk_cloud_id": bk_cloud_id,
                }
                for k in _topo_fields:
                    if k in s:
                        inst[k] = s[k]
                instances.append(inst)

    for p in data.get("proxy_instances", []):
        if cluster_type == "tendbha":
            p_role = "proxy"
            p_type = "proxy"
        else:
            p_role = p.get("role", "spider")
            p_type = "mysql"
        inst = {
            "address": p["address"],
            "role": p_role,
            "type": p_type,
            "bk_cloud_id": bk_cloud_id,
        }
        for k in _topo_fields:
            if k in p:
                inst[k] = p[k]
        instances.append(inst)

    result = {
        "cluster_type": cluster_type,
        "bk_biz_id": data.get("bk_biz_id", 0),
        "bk_cloud_id": bk_cloud_id,
        "instances": instances,
    }
    if sampled_remotes:
        result["remote_sampling"] = {
            "total_shards": total_shards,
            "analyzed_shards": 1,
        }
    return result


# ──────────────────────────────────────────────────────────────
# Phase 2: Fetch → Extract → Diagnose (per instance, parallelizable)
# ──────────────────────────────────────────────────────────────


def process_instance(inst: dict, raw_query: str) -> dict:
    addr = inst["address"]
    safe = _addr_safe(addr)
    is_proxy = inst["type"] == "proxy"

    tool = "mysql_query_show_proxy_processlist" if is_proxy else "mysql_query_show_mysql_processlist"
    raw_file = OUTPUT_DIR / f"pl_raw_{safe}.json"
    pl_file = OUTPUT_DIR / f"pl_{safe}.json"
    diag_file = OUTPUT_DIR / f"diag_{safe}.json"

    if not _mcp_call(tool, {"bk_cloud_id": inst["bk_cloud_id"], "address": addr}, raw_query, raw_file):
        return {"address": addr, "role": inst.get("role", ""), "error": "fetch_failed"}

    if not _py("check_mcp_response.py", [str(raw_file), "--out", str(pl_file)]):
        return {"address": addr, "role": inst.get("role", ""), "error": "extract_failed"}

    if not _py("analyze_processlist.py", [str(pl_file), "--type", "diagnose"], diag_file):
        return {"address": addr, "role": inst.get("role", ""), "error": "diagnose_failed"}

    result = _load(diag_file)
    result["address"] = addr
    result["role"] = inst.get("role", "")
    for k in ("is_stand_by", "bk_idc_name", "bk_sub_zone"):
        if k in inst:
            result[k] = inst[k]
    result["_pl_file"] = str(pl_file)
    return result


# ──────────────────────────────────────────────────────────────
# Phase 3: Cross-verification (per MySQL instance with findings)
# ──────────────────────────────────────────────────────────────


def cross_verify(inst: dict, findings: list, raw_query: str) -> dict:
    addr = inst["address"]
    safe = _addr_safe(addr)
    bk_cloud_id = inst["bk_cloud_id"]
    result = {}

    types = {f["type"] for f in findings}
    need_trx = "suspect_uncommitted_txn" in types
    need_vars = "idle_bloat" in types or "auth_pressure" in types

    if not need_trx and not need_vars:
        return result

    if need_trx:
        f = OUTPUT_DIR / f"trx_{safe}.json"
        if _mcp_call("mysql_query_trx_long_running", {"bk_cloud_id": bk_cloud_id, "address": addr}, raw_query, f):
            result["trx_long_running"] = _load(f)["response_body"]["data"].get("long_running_trx", [])

    if need_vars:
        f = OUTPUT_DIR / f"vars_{safe}.json"
        if _mcp_call(
            "mysql_query_show_global_variables_with_names",
            {
                "bk_cloud_id": bk_cloud_id,
                "address": addr,
                "variable_names": ["max_connections", "wait_timeout", "interactive_timeout"],
            },
            raw_query,
            f,
        ):
            items = _load(f)["response_body"]["data"].get("runtime_variables", [])
            result["variables"] = {
                i.get("variable_name", i.get("Variable_name", "")): i.get("variable_value", i.get("Value", ""))
                for i in items
            }

        f = OUTPUT_DIR / f"status_{safe}.json"
        if _mcp_call(
            "mysql_query_show_global_status_with_names",
            {
                "bk_cloud_id": bk_cloud_id,
                "address": addr,
                "status_names": [
                    "Threads_connected",
                    "Threads_running",
                    "Max_used_connections",
                    "Aborted_connects",
                    "Aborted_clients",
                    "Connection_errors_max_connections",
                ],
            },
            raw_query,
            f,
        ):
            items = _load(f)["response_body"]["data"].get("runtime_status", [])
            result["status"] = {
                i.get("status_name", i.get("Variable_name", "")): i.get("status_value", i.get("Value", ""))
                for i in items
            }

    return result


# ──────────────────────────────────────────────────────────────
# Phase 4: Cross-layer correlation
# ──────────────────────────────────────────────────────────────

_DATA_PATH_MAP = {
    "spider_master": "read_write",
    "remote_master": "read_write",
    "backend_master": "read_write",
    "spider_slave": "read_offload",
    "remote_slave": "read_offload",
    "backend_slave_readonly": "read_offload",
    "backend_slave_standby": "ha_standby",
    "proxy": "read_write",
}


def _assign_data_path(results: list):
    for r in results:
        r["data_path"] = _DATA_PATH_MAP.get(r.get("role", ""), "unknown")


def _tendbcluster_path_analysis(results: list) -> dict:
    """Aggregate and compare metrics along read_write / read_offload paths."""
    paths = {}
    for r in results:
        if "error" in r:
            continue
        dp = r.get("data_path", "unknown")
        if dp not in paths:
            paths[dp] = {
                "instances": [],
                "total_conn": 0,
                "total_active": 0,
                "total_idle": 0,
                "finding_count": 0,
                "high_findings": 0,
            }
        p = paths[dp]
        p["instances"].append(
            {"address": r["address"], "role": r["role"], "total": r.get("total", 0), "active": r.get("active", 0)}
        )
        p["total_conn"] += r.get("total", 0)
        p["total_active"] += r.get("active", 0)
        p["total_idle"] += r.get("idle", 0)
        for f in r.get("findings", []):
            p["finding_count"] += 1
            if f.get("severity") == "high":
                p["high_findings"] += 1

    findings = []

    rw = paths.get("read_write", {})
    ro = paths.get("read_offload", {})
    if rw and ro:
        findings.append(
            {
                "type": "path_comparison",
                "title": "读写路径 vs 读分流路径对比",
                "read_write": {k: v for k, v in rw.items() if k != "instances"},
                "read_offload": {k: v for k, v in ro.items() if k != "instances"},
            }
        )

    for dp_name, dp in paths.items():
        insts = dp["instances"]
        if len(insts) < 2:
            continue
        spider_insts = [i for i in insts if "spider" in i["role"]]
        remote_insts = [i for i in insts if "remote" in i["role"]]

        for group_name, group in [("spider", spider_insts), ("remote", remote_insts)]:
            if len(group) < 2:
                continue
            conns = [i["total"] for i in group]
            if not conns or max(conns) == 0:
                continue
            ratio = max(conns) / max(min(conns), 1)
            if ratio >= 2.0:
                findings.append(
                    {
                        "type": "path_skew",
                        "severity": "medium",
                        "title": f"{dp_name} 路径 {group_name} 层连接分布不均（最大/最小={ratio:.1f}x）",
                        "data_path": dp_name,
                        "layer": group_name,
                        "instances": group,
                    }
                )

    return {"paths": paths, "findings": findings}


def cross_layer(results: list, cluster_type: str) -> dict:
    if cluster_type == "tendbcluster":
        return _tendbcluster_path_analysis(results)

    if cluster_type != "tendbha":
        return {}

    args = []
    for r in results:
        if "error" in r or "_pl_file" not in r:
            continue
        args.extend([r["address"], r["_pl_file"]])

    if len(args) < 4:
        return {}

    out = OUTPUT_DIR / "cross_layer.tsv"
    _py("cross_layer_analyze.py", args, out)
    return {}


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="MySQL processlist analysis orchestrator")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--cluster", help="Cluster domain")
    mode.add_argument("--instance", help="Instance address (ip:port)")
    parser.add_argument("--proxy", action="store_true", help="Instance is Proxy (single instance mode)")
    parser.add_argument("--bk-cloud-id", type=int, default=0)
    parser.add_argument("--raw-query", default="分析连接")
    parser.add_argument(
        "--all-remotes",
        action="store_true",
        help="TenDBCluster: analyze all remote shards (default: first shard only)",
    )
    parser.add_argument("-o", "--output", help="Output file (default: $OUTPUT_DIR/analysis_result.tsv)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output:
        out_path = Path(args.output)
    elif args.cluster:
        out_path = OUTPUT_DIR / "analysis_result.tsv"
    else:
        out_path = OUTPUT_DIR / "analysis_result.json"

    if args.cluster:
        _run_cluster(args.cluster, args.raw_query, out_path, args.all_remotes)
    else:
        _run_instance(args.instance, args.proxy, args.bk_cloud_id, args.raw_query, out_path)


def _run_cluster(domain: str, raw_query: str, out_path: Path, all_remotes: bool = False):
    _log(f"[1/4] Fetching topology for {domain}")
    topo = fetch_topology(domain, raw_query, all_remotes=all_remotes)
    if not topo:
        _log("FATAL: topology fetch failed")
        sys.exit(1)
    sampling = topo.get("remote_sampling")
    if sampling:
        _log(
            f"  cluster_type={topo['cluster_type']}  instances={len(topo['instances'])}  "
            f"(remote: 1/{sampling['total_shards']} shards, use --all-remotes for full)"
        )
    else:
        _log(f"  cluster_type={topo['cluster_type']}  instances={len(topo['instances'])}")

    _log(f"[2/4] Fetching & diagnosing {len(topo['instances'])} instances (parallel)")
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=len(topo["instances"])) as pool:
        futs = {pool.submit(process_instance, inst, raw_query): inst for inst in topo["instances"]}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            if "error" in r:
                errors.append(r["address"])

    role_order = {
        "backend_master": 0,
        "remote_master": 0,
        "backend_slave": 1,
        "backend_slave_standby": 1,
        "backend_slave_readonly": 1,
        "remote_slave": 1,
        "proxy": 2,
        "spider": 2,
        "spider_master": 2,
        "spider_slave": 3,
    }
    results.sort(key=lambda r: role_order.get(r.get("role", ""), 99))
    has_findings = sum(1 for r in results if r.get("findings"))
    _log(f"  done: {has_findings} with findings, {len(errors)} errors")

    cv = {}
    inst_map = {i["address"]: i for i in topo["instances"]}
    cv_candidates = [
        r
        for r in results
        if r.get("source_type") == "mysql"
        and "error" not in r
        and any(f.get("severity") in ("high", "medium") for f in r.get("findings", []))
    ]
    if cv_candidates:
        _log(f"[3/4] Cross-verifying {len(cv_candidates)} instances")
        for r in cv_candidates:
            inst = inst_map.get(r["address"])
            if inst:
                v = cross_verify(inst, r.get("findings", []), raw_query)
                if v:
                    cv[r["address"]] = v
        _log(f"  done: {len(cv)} verified")
    else:
        _log(f"[3/4] Cross-verification: skipped (no findings)")

    _assign_data_path(results)

    _log(f"[4/4] Cross-layer analysis")
    cl = cross_layer(results, topo["cluster_type"])
    cl_count = len(cl.get("findings", []))
    _log(f"  {'done: ' + str(cl_count) + ' findings' if cl_count else 'skipped'}")

    for r in results:
        r.pop("_pl_file", None)

    # Convert proxy diag files from JSON to TSV (no raw SQL in proxy)
    for r in results:
        if r.get("source_type") == "proxy" and "error" not in r:
            safe = _addr_safe(r["address"])
            json_path = OUTPUT_DIR / f"diag_{safe}.json"
            tsv_path = OUTPUT_DIR / f"diag_{safe}.tsv"
            if json_path.exists():
                _diag_json_to_tsv(json_path, tsv_path)
                json_path.unlink()

    # Write summary as TSV
    lines = []
    sampling_note = ""
    if sampling:
        sampling_note = f"\tremote_sampling={sampling['analyzed_shards']}/{sampling['total_shards']}"
    lines.append(f"#cluster\t{domain}\t{topo['cluster_type']}\tbk_biz_id={topo['bk_biz_id']}{sampling_note}")
    lines.append("")
    lines.append("address\trole\tdata_path\ttotal\tactive\tidle\tfinding_count\thigh_findings\tbk_idc_name")
    for r in results:
        finding_count = len(r.get("findings", []))
        high_findings = sum(1 for f in r.get("findings", []) if f.get("severity") == "high")
        lines.append(
            "\t".join(
                [
                    r["address"],
                    r.get("role", ""),
                    r.get("data_path", ""),
                    str(r.get("total", 0)),
                    str(r.get("active", 0)),
                    str(r.get("idle", 0)),
                    str(finding_count),
                    str(high_findings),
                    r.get("bk_idc_name", ""),
                ]
            )
        )

    out_path = out_path.with_suffix(".tsv")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    # Cross-verification as TSV (key-value pairs)
    for addr, v in cv.items():
        safe = _addr_safe(addr)
        cv_lines = [f"#cv\t{addr}"]
        if "trx_long_running" in v:
            cv_lines.append(f"trx_long_running\t{len(v['trx_long_running'])}")
        for section in ("variables", "status"):
            if section in v:
                for k, val in v[section].items():
                    cv_lines.append(f"{k}\t{val}")
        cv_file = OUTPUT_DIR / f"cv_{safe}.tsv"
        with open(cv_file, "w") as f:
            f.write("\n".join(cv_lines) + "\n")

    # Cross-layer: tendbha writes cross_layer.tsv directly via cross_layer_analyze.py;
    # tendbcluster computed in-memory, write as TSV
    if cl and topo["cluster_type"] != "tendbha":
        cl_file = OUTPUT_DIR / "cross_layer.tsv"
        cl_lines = []
        for p in cl.get("paths", []):
            cl_lines.append(f"#path\t{p['data_path']}\t{p['layer']}")
            for inst in p.get("instances", []):
                cl_lines.append(
                    f"\t{inst['address']}\trole={inst.get('role','')}\tactive={inst.get('active',0)}\tidle={inst.get('idle',0)}\ttotal={inst.get('total',0)}"
                )
        for f_item in cl.get("findings", []):
            cl_lines.append(f"#finding\t{f_item.get('type','')}\t{f_item.get('title','')}")
            if "detail" in f_item:
                cl_lines.append(f"\t{f_item['detail']}")
        with open(cl_file, "w") as f:
            f.write("\n".join(cl_lines) + "\n")

    _log(f"\nDone → {out_path}")
    _log(f"  diag/cv/cross_layer files in {OUTPUT_DIR}/")


def _run_instance(address: str, is_proxy: bool, bk_cloud_id: int, raw_query: str, out_path: Path):
    inst = {
        "address": address,
        "role": "proxy" if is_proxy else "unknown",
        "type": "proxy" if is_proxy else "mysql",
        "bk_cloud_id": bk_cloud_id,
    }

    _log(f"[1/2] Fetching & diagnosing {address}")
    r = process_instance(inst, raw_query)
    if "error" in r:
        _log(f"  ERROR: {r['error']}")
    else:
        _log(f"  done: {len(r.get('findings', []))} findings")

    cv = {}
    if r.get("source_type") == "mysql" and "error" not in r:
        findings = r.get("findings", [])
        if any(f.get("severity") in ("high", "medium") for f in findings):
            _log(f"[2/2] Cross-verifying")
            v = cross_verify(inst, findings, raw_query)
            if v:
                cv[address] = v
                _log(f"  done")

    r.pop("_pl_file", None)

    output = {
        "instance": address,
        "bk_biz_id": 0,
        "result": r,
        "cross_verification": cv,
    }

    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False)
    _log(f"\nDone → {out_path}")


if __name__ == "__main__":
    main()
