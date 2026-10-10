#!/usr/bin/env python3
"""TenDBHA cross-layer processlist correlation.

Correlates MySQL and Proxy processlist data to trace connections across layers.
Auto-detects MySQL vs Proxy from data structure.

Usage:
    python cross_layer_analyze.py <addr1> <file1> <addr2> <file2> ...

Example:
    python cross_layer_analyze.py \
      192.168.139.161:20000 pl_mysql.json \
      192.168.154.80:10000 pl_proxy1.json \
      192.168.146.68:10000 pl_proxy2.json
"""

import argparse
import json
import sys

import pandas as pd

SYSTEM_USERS = {"repl", "system user", "MONITOR"}
MYSQL_AUTH_USERS = {"unauthenticated user"}
MYSQL_AUTH_STATES = {"login"}
PROXY_AUTH_STATES = {"CON_STATE_READ_HANDSHAKE", "CON_STATE_READ_AUTH_RESULT"}
PROXY_IDLE_STATES = {"CON_STATE_READ_QUERY"}
MYSQL_INTERNAL_COMMANDS = {"Binlog Dump", "Binlog Dump GTID"}
IDLE_THRESHOLD_SECONDS = 600
TOP_N = 10


def _extract_ip(host: str) -> str:
    if not host:
        return ""
    return host.rsplit(":", 1)[0]


def _fmt_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds / 86400:.1f}天"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}小时"
    if seconds >= 60:
        return f"{seconds / 60:.1f}分钟"
    return f"{seconds}秒"


def _detect_source_type(df: pd.DataFrame) -> str:
    if "destination_host" in df.columns and "command" not in df.columns:
        return "proxy"
    return "mysql"


def _load_instance(address: str, filepath: str) -> dict:
    with open(filepath) as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"Error: {filepath} must contain a JSON array", file=sys.stderr)
        sys.exit(1)
    df = pd.DataFrame(data)
    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)
    return {
        "address": address,
        "ip": _extract_ip(address),
        "type": _detect_source_type(df),
        "df": df,
    }


def _top_ips(series: pd.Series, n: int = TOP_N) -> list:
    counts = series.value_counts().head(n)
    return [{"ip": str(ip), "count": int(cnt)} for ip, cnt in counts.items()]


def _correlate_auth(mysql_instances, proxy_map) -> list:
    """Trace MySQL auth connections through Proxy to real client IPs."""
    findings = []
    for inst in mysql_instances:
        mdf = inst["df"]
        if "source_host" not in mdf.columns:
            continue

        auth_mask = mdf["user"].isin(MYSQL_AUTH_USERS)
        if "state" in mdf.columns:
            auth_mask = auth_mask | mdf["state"].str.lower().isin(MYSQL_AUTH_STATES)
        auth_df = mdf[auth_mask]
        if len(auth_df) == 0:
            continue

        auth_df = auth_df.copy()
        auth_df["source_ip"] = auth_df["source_host"].apply(_extract_ip)
        from_proxies = []

        for source_ip, group in auth_df.groupby("source_ip"):
            if source_ip not in proxy_map:
                continue
            proxy_inst = proxy_map[source_ip]
            pdf = proxy_inst["df"]

            proxy_auth_mask = (
                pdf["state"].isin(PROXY_AUTH_STATES) if "state" in pdf.columns else pd.Series(False, index=pdf.index)
            )
            proxy_auth_to_mysql = proxy_auth_mask
            if "destination_host" in pdf.columns:
                proxy_auth_to_mysql = proxy_auth_mask & (pdf["destination_host"] == inst["address"])

            proxy_auth_all = pdf[proxy_auth_mask]
            real_clients = []
            if len(proxy_auth_all) > 0 and "source_host" in pdf.columns:
                real_clients = _top_ips(proxy_auth_all["source_host"].apply(_extract_ip))

            from_proxies.append(
                {
                    "proxy": proxy_inst["address"],
                    "mysql_auth_from_this_proxy": int(len(group)),
                    "proxy_total_auth": int(len(proxy_auth_all)),
                    "proxy_auth_to_this_mysql": int(proxy_auth_to_mysql.sum()),
                    "real_client_ips": real_clients,
                }
            )

        if from_proxies:
            total = int(len(auth_df))
            from_proxy_total = sum(p["mysql_auth_from_this_proxy"] for p in from_proxies)
            findings.append(
                {
                    "type": "auth_pressure_traced",
                    "mysql_instance": inst["address"],
                    "total_auth_connections": total,
                    "from_proxy_count": from_proxy_total,
                    "from_proxies": from_proxies,
                    "title": f"MySQL {inst['address']} 的 {total} 个鉴权连接中 {from_proxy_total} 个来自 Proxy，已追溯到真实客户端",
                }
            )
    return findings


def _correlate_idle(mysql_instances, proxy_map) -> list:
    """Trace MySQL long-idle connections through Proxy to real client IPs."""
    findings = []
    for inst in mysql_instances:
        mdf = inst["df"]
        if "command" not in mdf.columns or "source_host" not in mdf.columns:
            continue

        idle_mask = (
            (mdf["command"] == "Sleep") & (mdf["time"] > IDLE_THRESHOLD_SECONDS) & (~mdf["user"].isin(SYSTEM_USERS))
        )
        idle_df = mdf[idle_mask].copy()
        if len(idle_df) == 0:
            continue

        idle_df["source_ip"] = idle_df["source_host"].apply(_extract_ip)
        user_counts = idle_df["user"].value_counts().head(TOP_N)
        traced_rows = []

        for user, cnt in user_counts.items():
            user_idle = idle_df[idle_df["user"] == user]
            user_source_ips = user_idle["source_ip"].value_counts()
            all_real_ips = {}

            for source_ip, src_cnt in user_source_ips.items():
                if source_ip not in proxy_map:
                    continue
                proxy_inst = proxy_map[source_ip]
                pdf = proxy_inst["df"]

                proxy_user_mask = pdf["user"] == user
                if "destination_host" in pdf.columns:
                    proxy_user_mask = proxy_user_mask & (pdf["destination_host"] == inst["address"])
                proxy_user_conns = pdf[proxy_user_mask]

                if len(proxy_user_conns) > 0 and "source_host" in pdf.columns:
                    for ip_entry in _top_ips(proxy_user_conns["source_host"].apply(_extract_ip)):
                        all_real_ips[ip_entry["ip"]] = all_real_ips.get(ip_entry["ip"], 0) + ip_entry["count"]

            if all_real_ips:
                top_real = sorted(all_real_ips.items(), key=lambda x: -x[1])[:5]
                top_real_str = ", ".join(f"{ip}({c})" for ip, c in top_real)
                traced_rows.append([user, int(cnt), top_real_str])

        if traced_rows:
            findings.append(
                {
                    "type": "idle_traced",
                    "mysql_instance": inst["address"],
                    "title": f"MySQL {inst['address']} 长 Sleep 连接追溯到真实客户端 IP",
                    "traced_users": {
                        "columns": ["user", "mysql_idle_count", "top_real_client_ips"],
                        "rows": traced_rows,
                    },
                }
            )
    return findings


def _correlate_stale(mysql_instances, proxy_instances) -> list:
    """Verify Proxy stale connections against MySQL side."""
    mysql_map = {m["address"]: m for m in mysql_instances}
    findings = []

    for proxy_inst in proxy_instances:
        pdf = proxy_inst["df"]
        if "state" not in pdf.columns or "destination_host" not in pdf.columns or "time" not in pdf.columns:
            continue

        stale_mask = (~pdf["state"].isin(PROXY_IDLE_STATES)) & (pdf["time"] > 10) & (~pdf["user"].isin(SYSTEM_USERS))
        stale_df = pdf[stale_mask]
        if len(stale_df) == 0:
            continue

        verif_cols = [
            "user",
            "source_host",
            "destination_host",
            "proxy_state",
            "proxy_time_human",
            "mysql_status",
            "mysql_command",
            "mysql_time_human",
        ]
        verif_rows = []
        for _, row in stale_df.iterrows():
            dest = row.get("destination_host", "")
            mysql_inst = mysql_map.get(dest)
            mysql_status = "no_data"
            mysql_cmd = None
            mysql_time = None

            if mysql_inst is not None:
                mdf = mysql_inst["df"]
                if "source_host" in mdf.columns:
                    mdf_ip = mdf["source_host"].apply(_extract_ip)
                    match_mask = (mdf_ip == proxy_inst["ip"]) & (mdf["user"] == row["user"])
                    if "command" in mdf.columns:
                        match_mask = match_mask & (~mdf["command"].isin(MYSQL_INTERNAL_COMMANDS))
                    matches = mdf[match_mask]
                    if len(matches) > 0:
                        best = matches.sort_values("time", ascending=False).iloc[0]
                        mysql_cmd = best.get("command", "") if "command" in mdf.columns else None
                        mysql_time = int(best.get("time", 0))
                        if mysql_cmd == "Sleep":
                            mysql_status = "idle_on_mysql"
                        elif mysql_cmd == "Query":
                            mysql_status = "active_on_mysql"
                        else:
                            mysql_status = f"other_{mysql_cmd}"
                    else:
                        mysql_status = "ghost"

            verif_rows.append(
                [
                    row["user"],
                    row.get("source_host", ""),
                    dest,
                    row["state"],
                    _fmt_duration(int(row["time"])),
                    mysql_status,
                    mysql_cmd,
                    _fmt_duration(mysql_time) if mysql_time else None,
                ]
            )

        ghost = sum(1 for r in verif_rows if r[5] == "ghost")
        idle = sum(1 for r in verif_rows if r[5] == "idle_on_mysql")
        active = sum(1 for r in verif_rows if r[5] == "active_on_mysql")

        parts = []
        if idle:
            parts.append(f"{idle} 个 Proxy 连接泄漏（MySQL 侧已空闲但 Proxy 未释放）")
        if ghost:
            parts.append(f"{ghost} 个幽灵连接（MySQL 侧无对应连接）")
        if active:
            parts.append(f"{active} 个真正慢查询（MySQL 侧确实在执行）")

        findings.append(
            {
                "type": "stale_verified",
                "proxy_instance": proxy_inst["address"],
                "total": len(verif_rows),
                "ghost_count": ghost,
                "idle_leak_count": idle,
                "active_count": active,
                "title": f"Proxy {proxy_inst['address']} 的 {len(verif_rows)} 个滞留连接验证",
                "summary": "；".join(parts) if parts else "全部状态正常",
                "verifications": {"columns": verif_cols, "rows": verif_rows[:20]},
            }
        )

    return findings


def _check_consistency(mysql_instances, proxy_instances) -> list:
    """Compare connection counts between MySQL and Proxy layers."""
    findings = []
    for mysql_inst in mysql_instances:
        mdf = mysql_inst["df"]
        if "source_host" not in mdf.columns:
            continue
        mdf_ips = mdf["source_host"].apply(_extract_ip)

        checks = []
        has_anomaly = False
        for proxy_inst in proxy_instances:
            pdf = proxy_inst["df"]
            mysql_sees = int((mdf_ips == proxy_inst["ip"]).sum())
            proxy_sees = -1
            if "destination_host" in pdf.columns:
                proxy_sees = int((pdf["destination_host"] == mysql_inst["address"]).sum())

            diff = abs(mysql_sees - proxy_sees) if proxy_sees >= 0 else 0
            threshold = max(10, int(max(mysql_sees, proxy_sees) * 0.1))

            if proxy_sees >= 0 and diff > threshold:
                if proxy_sees > mysql_sees:
                    status = "proxy_more"
                    note = f"Proxy 侧多 {proxy_sees - mysql_sees} 个连接，可能存在幽灵连接"
                else:
                    status = "mysql_more"
                    note = f"MySQL 侧多 {mysql_sees - proxy_sees} 个连接，可能有绕过 Proxy 的直连"
                has_anomaly = True
            else:
                status = "consistent"
                note = "一致"

            checks.append(
                {
                    "proxy": proxy_inst["address"],
                    "mysql_sees_from_proxy": mysql_sees,
                    "proxy_sees_to_mysql": proxy_sees,
                    "diff": diff,
                    "status": status,
                    "note": note,
                }
            )

        if checks:
            findings.append(
                {
                    "type": "connection_consistency",
                    "mysql_instance": mysql_inst["address"],
                    "has_anomaly": has_anomaly,
                    "title": f"MySQL {mysql_inst['address']} 与 Proxy 连接数一致性校验",
                    "checks": checks,
                }
            )

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="TenDBHA cross-layer processlist correlation",
        usage="%(prog)s <addr1> <file1> <addr2> <file2> ...",
    )
    parser.add_argument("pairs", nargs="+", metavar="ADDR_OR_FILE", help="Alternating pairs: <ip:port> <json_file>")
    args = parser.parse_args()

    if len(args.pairs) % 2 != 0:
        print("Error: arguments must be <address> <file> pairs", file=sys.stderr)
        sys.exit(1)

    mysql_instances = []
    proxy_instances = []
    for i in range(0, len(args.pairs), 2):
        inst = _load_instance(args.pairs[i], args.pairs[i + 1])
        if inst["type"] == "mysql":
            mysql_instances.append(inst)
        else:
            proxy_instances.append(inst)

    if not mysql_instances or not proxy_instances:
        print("# no cross-layer data (need both MySQL and Proxy)")
        sys.exit(0)

    proxy_map = {p["ip"]: p for p in proxy_instances}

    all_findings = []
    all_findings.extend(_correlate_auth(mysql_instances, proxy_map))
    all_findings.extend(_correlate_idle(mysql_instances, proxy_map))
    all_findings.extend(_correlate_stale(mysql_instances, proxy_instances))
    all_findings.extend(_check_consistency(mysql_instances, proxy_instances))

    _print_tsv(all_findings)


def _print_tsv(findings: list):
    """Output findings as TSV."""
    for f in findings:
        ftype = f.get("type", "")
        if ftype == "idle_traced":
            print(f"#idle_traced\t{f['mysql_instance']}\t{f['title']}")
            tu = f["traced_users"]
            print("\t".join(tu["columns"]))
            for row in tu["rows"]:
                print("\t".join(str(x) for x in row))
            print()
        elif ftype == "stale_verified":
            print(f"#stale_verified\t{f['proxy_instance']}\t{f['title']}")
            print(
                f"total={f['total']}\tghost={f['ghost_count']}\tleak={f['idle_leak_count']}\tactive={f['active_count']}"
            )
            print(f"summary\t{f['summary']}")
            v = f["verifications"]
            print("\t".join(v["columns"]))
            for row in v["rows"]:
                print("\t".join(str(x) if x is not None else "" for x in row))
            print()
        elif ftype == "connection_consistency":
            print(f"#connection_consistency\t{f['mysql_instance']}\t{f['title']}")
            print("proxy\tproxy_sees_to_mysql\tmysql_sees_from_proxy\tdelta\tstatus")
            for c in f.get("checks", []):
                print(
                    f"{c['proxy']}\t{c['proxy_sees_to_mysql']}\t{c['mysql_sees_from_proxy']}\t{c.get('delta', 0)}\t{c['status']}"
                )
            print()
        elif ftype == "auth_pressure_traced":
            print(f"#auth_pressure_traced\t{f['mysql_instance']}\t{f['title']}")
            print(f"auth_count\t{f.get('auth_count', 0)}")
            if f.get("traced_sources"):
                print("proxy\treal_client_ips")
                for src in f["traced_sources"]:
                    ips = ", ".join(f"{e['ip']}({e['count']})" for e in src.get("real_client_ips", []))
                    print(f"{src['proxy']}\t{ips}")
            print()


if __name__ == "__main__":
    main()
