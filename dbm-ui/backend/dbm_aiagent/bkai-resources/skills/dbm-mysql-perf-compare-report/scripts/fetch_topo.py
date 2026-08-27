#!/usr/bin/env python3
"""
fetch_topo.py — 并发获取集群拓扑信息

用法：
  python3 fetch_topo.py <domain1,domain2,...>
  python3 fetch_topo.py <domains_file>
  cat domains.txt | python3 fetch_topo.py

输出：$OUTPUT_DIR/pcr_topo_all.json（默认 /tmp）

输出格式：
{
  "domains": ["domain1", ...],
  "topo": {
    "domain1": {
      "cluster_type": "tendbha|tendbcluster|tendbsingle",
      "slowlog_role": "backend_master|spider_master|orphan",
      "proxy_role": "proxy|spider_master|—",
      "master_role": "backend_master|remote_master|orphan",
      "slave_role": "backend_slave|remote_slave|—"
    }
  }
}
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROLE_MAP = {
    "tendbha": {
        "slowlog_role": "backend_master",
        "proxy_role": "proxy",
        "master_role": "backend_master",
        "slave_role": "backend_slave",
    },
    "tendbcluster": {
        "slowlog_role": "spider_master",
        "proxy_role": "spider_master",
        "master_role": "remote_master",
        "slave_role": "remote_slave",
    },
    "tendbsingle": {
        "slowlog_role": "orphan",
        "proxy_role": "—",
        "master_role": "orphan",
        "slave_role": "—",
    },
}


def fetch_topo(domain: str) -> tuple:
    """返回 (domain, cluster_type) 或 (domain, None)"""
    try:
        result = subprocess.run(
            [
                "dbm-mcp-cli",
                "call",
                "bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo",
                f"body_param={json.dumps({'cluster_domain': domain})}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        cluster_type = data.get("response_body", {}).get("data", {}).get("cluster_type", "")
        return (domain, cluster_type)
    except Exception as e:
        return (domain, None)


def main():
    domains = []
    if len(sys.argv) > 1:
        raw = sys.argv[1]
        if os.path.isfile(raw):
            with open(raw) as f:
                for line in f:
                    domains.extend(d.strip() for d in line.replace(",", "\n").split("\n") if d.strip())
        else:
            domains = [d.strip() for d in raw.replace(",", "\n").split("\n") if d.strip()]
    else:
        for line in sys.stdin:
            domains.extend(d.strip() for d in line.replace(",", "\n").split("\n") if d.strip())

    if not domains:
        print("ERROR: 未提供域名列表", file=sys.stderr)
        sys.exit(1)

    seen = set()
    domains = [d for d in domains if not (d in seen or seen.add(d))]

    topo = {}
    errors = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_topo, d): d for d in domains}
        for future in as_completed(futures):
            domain = futures[future]
            try:
                d, ct = future.result()
                if ct:
                    roles = ROLE_MAP.get(ct)
                    if roles:
                        topo[d] = {
                            "cluster_type": ct,
                            **roles,
                        }
                    else:
                        errors.append(f"{d}: 未知 cluster_type={ct}")
                else:
                    errors.append(f"{d}: 获取拓扑失败")
            except Exception as e:
                errors.append(f"{d}: {e}")

    output = {
        "domains": list(topo.keys()),
        "topo": topo,
    }
    if errors:
        output["errors"] = errors

    out_dir = os.environ.get("OUTPUT_DIR", "/tmp")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "pcr_topo_all.json"), "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"成功获取 {len(topo)}/{len(domains)} 个集群拓扑")
    if errors:
        for e in errors:
            print(f"  ⚠️  {e}", file=sys.stderr)

    if not topo:
        sys.exit(1)


if __name__ == "__main__":
    main()
