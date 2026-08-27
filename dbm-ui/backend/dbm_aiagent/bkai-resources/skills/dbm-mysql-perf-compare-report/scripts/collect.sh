#!/usr/bin/env bash
# collect.sh — 并发拉取慢查询 + 监控指标 + EXPLAIN
#
# 用法：
#   bash collect.sh <domains_file> <analysis_start> <analysis_end> <baseline_date>
#                   <metrics_start> <metrics_end>
#
#   domains_file: 每行一个域名，格式 "domain slowlog_role cluster_type"
#                 由 fetch_topo.py 输出 $OUTPUT_DIR/pcr_topo_all.json 提供
#
# 输出文件统一放 $OUTPUT_DIR/pcr_<domain>_*.json

set -euo pipefail

DOMAINS_FILE="$1"
ANA_START="$2"
ANA_END="$3"
BASE_DATE="$4"
MET_START="$5"
MET_END="$6"

OUTPUT_DIR="${OUTPUT_DIR:-/tmp}"

BASE_START="${BASE_DATE} 00:00:00"
BASE_END="${BASE_DATE} 23:59:59"

if [[ ! -f "$DOMAINS_FILE" ]]; then
  echo "ERROR: 域名文件不存在: $DOMAINS_FILE" >&2
  exit 1
fi

# ── 逐集群串行采集（串扰防护）─────────────────────────────────
while IFS=' ' read -r DOMAIN SLOWLOG_ROLE CLUSTER_TYPE; do
  [[ -z "$DOMAIN" || "$DOMAIN" == \#* ]] && continue

  echo "[collect] ${DOMAIN} start"

  # 慢查询（4 个 metric，分析时段 + 基准时段）
  for metric in query_time_max count_star rows_examined_max query_time_sum; do
    dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
      body_param="{\"cluster_domain\":\"${DOMAIN}\",\"instance_role\":\"${SLOWLOG_ROLE}\",\"start_time\":\"${ANA_START}\",\"end_time\":\"${ANA_END}\",\"metric_name\":\"${metric}\",\"limit\":500}" \
      > "${OUTPUT_DIR}/pcr_cur_${DOMAIN}_${metric}.json" 2>&1 &

    dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
      body_param="{\"cluster_domain\":\"${DOMAIN}\",\"instance_role\":\"${SLOWLOG_ROLE}\",\"start_time\":\"${BASE_START}\",\"end_time\":\"${BASE_END}\",\"metric_name\":\"${metric}\",\"limit\":500}" \
      > "${OUTPUT_DIR}/pcr_base_${DOMAIN}_${metric}.json" 2>&1 &
  done

  # 监控指标（CPU + QPS，分析时段 + 基准时段）
  # 基准时段与分析时段同小时区间，但日期换成 BASE_DATE
  MET_BASE_START="${BASE_DATE} ${MET_START#* }"
  MET_BASE_END="${BASE_DATE} ${MET_END#* }"

  for metric in cpu_summary qps_summary; do
    dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
      body_param="{\"cluster_domain\":\"${DOMAIN}\",\"cluster_type\":\"${CLUSTER_TYPE}\",\"start_time\":\"${MET_START}\",\"end_time\":\"${MET_END}\",\"metric_name\":\"${metric}\"}" \
      > "${OUTPUT_DIR}/pcr_metrics_cur_${DOMAIN}_${metric}.json" 2>&1 &

    dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
      body_param="{\"cluster_domain\":\"${DOMAIN}\",\"cluster_type\":\"${CLUSTER_TYPE}\",\"start_time\":\"${MET_BASE_START}\",\"end_time\":\"${MET_BASE_END}\",\"metric_name\":\"${metric}\"}" \
      > "${OUTPUT_DIR}/pcr_metrics_base_${DOMAIN}_${metric}.json" 2>&1 &
  done

  # 等待本集群所有采集完成
  wait
  echo "[collect] ${DOMAIN} done"

  # ── EXPLAIN 采集（仅对新增慢查询 + Top20）─────────────────
  python3 << PYEOF
import json, glob, re, subprocess, os

def normalize_sql(sql):
    sql = re.sub(r'(\b\w+)_\?\+?', r'\g<1>_0', sql)
    sql = re.sub(r'IN\s*\([?\s,\+]+\)', 'IN (1,2,3)', sql, flags=re.IGNORECASE)
    sql = re.sub(r'VALUES\s*\([?\s,\+]+\)', 'VALUES (1,2,3)', sql, flags=re.IGNORECASE)
    sql = sql.replace("?+", "1").replace("?", "1")
    sql = re.sub(r'\bSELECT\b(.*?)\bINTO\b\s+(?!OUTFILE|DUMPFILE)[\w\s,]+\bFROM\b',
                 r'SELECT\1FROM', sql, flags=re.IGNORECASE | re.DOTALL)
    sql = re.sub(r'(\bWHERE\b|\bAND\b|\bOR\b)(\s+`?\w+`?\s*)=\s*1\b',
                 r'\1\2 >= 0', sql, flags=re.IGNORECASE)
    if not re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
        sql = sql.rstrip('; \t\n') + ' LIMIT 1'
    return sql

DOMAIN = "${DOMAIN}"
OUTPUT_DIR = "${OUTPUT_DIR:-/tmp}"
SKIP_TYPES = {"truncate", "call", "load"}

def load_digests(pattern):
    rows = {}
    for fpath in sorted(glob.glob(pattern)):
        try:
            logs = json.load(open(fpath)).get("response_body",{}).get("data",{}).get("slow_logs",[])
            for row in logs:
                k = row.get("query_digest_md5","").upper()[:8]
                if k and k not in rows:
                    rows[k] = row
        except: pass
    return rows

today = load_digests(f"{OUTPUT_DIR}/pcr_cur_{DOMAIN}_*.json")
yest  = load_digests(f"{OUTPUT_DIR}/pcr_base_{DOMAIN}_*.json")
new   = {k: v for k, v in today.items() if k not in yest}

# new 全量 + today Top20（qt_sum）+ today Top20（cnt）三组合并去重
top_sum = sorted(today.values(), key=lambda r: -(r.get("query_time_sum") or 0))[:20]
top_cnt = sorted(today.values(), key=lambda r: -(r.get("count_star") or 0))[:20]
seen_ex = set(); explain_targets = {}
for row in list(new.values()) + top_sum + top_cnt:
    k2 = row.get("query_digest_md5","").upper()[:8]
    if k2 and k2 not in seen_ex:
        seen_ex.add(k2)
        explain_targets[k2] = row

for k, row in explain_targets.items():
    db  = row.get("query_db_name", "")
    sql = row.get("query_digest_text") or row.get("query_string") or ""
    cmd = (row.get("query_command") or re.match(r"(\w+)", sql.lower()).group(1) if re.match(r"(\w+)", sql.lower()) else "").lower()
    if cmd in SKIP_TYPES or not db or not sql:
        continue
    out = f"{OUTPUT_DIR}/pcr_explain_{DOMAIN}_{k}.json"
    if os.path.exists(out):
        continue
    body = json.dumps({"cluster_domain": DOMAIN, "query_sql": normalize_sql(sql), "db_name": db})
    result = subprocess.run(
        ["dbm-mcp-cli", "call", "bkdbm-mcp-prod-mysql-query.mysql_query_explain_sql",
         f"body_param={body}"],
        capture_output=True, text=True, timeout=30
    )
    with open(out, "w") as f:
        f.write(result.stdout or '{"response_body":{"result":false}}')
    print(f"[explain] {k} -> {out}")
PYEOF

done < "$DOMAINS_FILE"

echo "[collect] all done"
