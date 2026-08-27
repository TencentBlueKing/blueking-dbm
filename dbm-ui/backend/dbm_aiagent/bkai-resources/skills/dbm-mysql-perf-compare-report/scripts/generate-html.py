#!/usr/bin/env python3
"""
generate-html.py — 生成内嵌 Chart.js 的 HTML 性能对比分析报告
用法：
  python3 generate-html.py \
    --domains "gamedb.account.dnf.db,gamedb.sz1login.dnf.db" \
    --analysis-start "2026-06-11 08:00:00" \
    --analysis-end   "2026-06-11 10:00:00" \
    --baseline-date  "2026-06-10" \
    --metrics-start  "2026-06-11 08:00:00" \
    --metrics-end    "2026-06-11 09:00:00" \
    --metrics-baseline-start "2026-06-10 08:00:00" \
    --metrics-baseline-end   "2026-06-10 09:00:00" \
    [--cluster-types "spider.xxx.dnf.db:tendbcluster,..."] \
    [--output $OUTPUT_DIR/perf_report_YYYYMMDD.html]
"""

import argparse
import glob
import json
import os
import re
from datetime import datetime

DATA_DIR = os.environ.get("OUTPUT_DIR", "/tmp")

# ── CLI ──────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("--domains", required=True)
ap.add_argument("--analysis-start", required=True)
ap.add_argument("--analysis-end", required=True)
ap.add_argument("--baseline-date", required=True)
ap.add_argument("--metrics-start", required=True)
ap.add_argument("--metrics-end", required=True)
ap.add_argument("--metrics-baseline-start", required=True)
ap.add_argument("--metrics-baseline-end", required=True)
ap.add_argument("--cluster-types", default="")
ap.add_argument("--output", default="")
args = ap.parse_args()

DOMAINS = [d.strip() for d in args.domains.replace("\n", ",").split(",") if d.strip()]
CTYPE_MAP = {}
for item in args.cluster_types.split(","):
    if ":" in item:
        d, t = item.strip().split(":", 1)
        CTYPE_MAP[d.strip()] = t.strip()

ts_tag = datetime.now().strftime("%Y%m%d%H%M%S")
OUTPUT = args.output or os.path.join(DATA_DIR, f"perf_compare_report_{ts_tag}.html")

# ── 工具函数 ──────────────────────────────────────────────────────────
def get_roles(domain):
    ct = CTYPE_MAP.get(domain, "tendbha")
    if ct == "tendbcluster":
        return {"proxy": "spider_master", "master": "remote_master", "remote": "remote_slave"}
    if ct == "tendbsingle":
        return {"proxy": None, "master": "orphan", "remote": None}
    return {"proxy": "proxy", "master": "backend_master", "remote": "backend_slave"}


def load_digests(pattern):
    rows = {}
    for fpath in sorted(glob.glob(pattern)):
        try:
            logs = (
                json.load(open(fpath, encoding="utf-8")).get("response_body", {}).get("data", {}).get("slow_logs", [])
            )
            for row in logs:
                k = row.get("query_digest_md5", "").upper()[:8]
                sql = (row.get("query_digest_text") or "").upper()
                if k and k not in rows and "SQL_NO_CACHE" not in sql:
                    rows[k] = row
        except Exception:
            pass
    return rows


def classify(row):
    cmd = (row.get("query_command") or "").lower().strip()
    text = (row.get("query_digest_text") or row.get("query_string") or "").strip().lower()
    if not cmd:
        m = re.match(r"(\w+)", text)
        cmd = m.group(1) if m else "unknown"
    if cmd == "select":
        return "SELECT INTO OUTFILE" if "into outfile" in text else "SELECT"
    return {
        "update": "UPDATE",
        "insert": "INSERT",
        "delete": "DELETE",
        "replace": "REPLACE",
        "truncate": "TRUNCATE",
        "call": "CALL",
        "load": "LOAD DATA",
    }.get(cmd, cmd.upper())


def get_stat(filepath, role):
    if role is None:
        return None, None
    try:
        for s in (
            json.load(open(filepath, encoding="utf-8")).get("response_body", {}).get("data", {}).get("series", [])
        ):
            if s.get("dimensions", {}).get("instance_role") == role:
                stat = s.get("stat", {})
                avg = stat.get("avg", [0, 0])
                maxv = stat.get("max", [0, 0])
                return (
                    round(avg[1] if isinstance(avg, list) else avg, 2),
                    round(maxv[1] if isinstance(maxv, list) else maxv, 2),
                )
    except Exception:
        pass
    return None, None


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cpu_flag(delta):
    if delta > 3:
        return ("↑", "up")
    if delta < -3:
        return ("↓", "dn")
    return ("≈", "ok")


def qps_flag(delta, baseline):
    pct = (delta / baseline * 100) if baseline else 0
    if pct > 20:
        return (f"↑ +{pct:.1f}%", "up")
    if pct < -20:
        return (f"↓ {pct:.1f}%", "dn")
    return (f"≈ {pct:+.1f}%", "ok")


def chg_span(text, kind):
    return f'<span class="chg-{kind}">{text}</span>'


def badge(text, kind):
    return f'<span class="badge badge-{kind}">{text}</span>'


# ── EXPLAIN 相关 ──────────────────────────────────────────────────────
import subprocess

SKIP_EXPLAIN_SQL = {"TRUNCATE", "CALL", "SELECT INTO OUTFILE", "OTHER", "LOAD DATA"}
INSERT_VALUES_RE = re.compile(r"^\s*INSERT\s+(?:IGNORE\s+)?INTO\s+\S+\s*\(", re.IGNORECASE)


def is_insert_values(sql):
    """INSERT ... VALUES 形式，接口拒绝 EXPLAIN"""
    if not INSERT_VALUES_RE.match(sql):
        return False
    return bool(re.search(r"VALUES\s*\(", sql, re.IGNORECASE))


def normalize_sql(sql):
    """normalize digest SQL: replace ? -> range condition to avoid MySQL const-folding short-circuit"""
    sql = re.sub(r"(\b\w+)_\?\+?", r"\g<1>_0", sql)  # table suffix _?/_?+ -> _0
    sql = re.sub(r"IN\s*\([?\s,\+]+\)", "IN (1,2,3)", sql, flags=re.IGNORECASE)
    sql = re.sub(r"VALUES\s*\([?\s,\+]+\)", "VALUES (1,2,3)", sql, flags=re.IGNORECASE)
    sql = sql.replace("?+", "1").replace("?", "1")
    # strip stored-proc SELECT ... INTO vars FROM
    sql = re.sub(
        r"\bSELECT\b(.*?)\bINTO\b\s+(?!OUTFILE|DUMPFILE)[\w\s,]+\bFROM\b",
        r"SELECT\1FROM",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # replace WHERE/AND/OR col=1 with col>=0 (range scan) to avoid const-folding when row m_id=1 not exist
    sql = re.sub(r"(\bWHERE\b|\bAND\b|\bOR\b)(\s+`?\w+`?\s*)=\s*1\b", r"\1\2 >= 0", sql, flags=re.IGNORECASE)
    # add LIMIT 1 if no LIMIT exists
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = sql.rstrip("; \t\n") + " LIMIT 1"
    return sql


def load_explain(domain, digest):
    fpath = os.path.join(DATA_DIR, f"pcr_explain_{domain}_{digest}.json")
    try:
        d = json.load(open(fpath, encoding="utf-8"))
        rb = d.get("response_body", {})
        if rb.get("result"):
            ex_raw = rb["data"].get("explain_result", {})
            # explain_result 可能为数组，取第一个元素
            if isinstance(ex_raw, list):
                ex = ex_raw[0] if ex_raw else {}
            else:
                ex = ex_raw
            # rewritten=true: 接口将占位符替换为具体值后执行 EXPLAIN，结果仍可参考
            if rb["data"].get("rewritten"):
                pass  # 继续解析 EXPLAIN 结果
            return ex, "ok"
        msg = rb.get("message", "")
        if "VALUES" in msg or "no meaningful" in msg:
            return None, "insert_values"
        if "1064" in msg or "syntax" in msg.lower():
            return None, "syntax_err"
        return None, f"err:{msg[:40]}"
    except Exception:
        pass
    return None, "no_file"


_schema_cache = {}


def call_show_create_table(domain, db, table):
    """调用 MCP 获取建表语句，返回 create_sql 字符串或 None"""
    cache_key = f"{domain}|{db}|{table}"
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]
    body = json.dumps({"cluster_domain": domain, "db_name": db, "table_name": table})
    try:
        r = subprocess.run(
            ["dbm-mcp-cli", "call", "bkdbm-mcp-prod-mysql-query.mysql_query_show_create_table", f"body_param={body}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        resp = json.loads(r.stdout or "{}")
        if resp.get("response_body", {}).get("result"):
            result = resp["response_body"]["data"].get("create_sql", "")
            _schema_cache[cache_key] = result
            return result
    except Exception:
        pass
    _schema_cache[cache_key] = None
    return None
    return None


def call_show_create_table_like(domain, db, table_prefix):
    """
    表名不确定时，逐级尝试获取建表语句：
    1. 直接用 table_prefix（如 member_play_info）
    2. 加 _0/_1/_2 后缀（如 member_play_info_0）
    3. 剥掉所有尾部 _数字 段，查逻辑基础表名（如 auction_history_65 -> auction_history）
    """
    # 1. 直接尝试 prefix 本身 + _0/_1/_2
    for suffix in ["", "_0", "_1", "_2"]:
        candidate = table_prefix + suffix
        create_sql = call_show_create_table(domain, db, candidate)
        if create_sql:
            return create_sql, candidate
    # 2. 逐级剥掉尾部 _数字 段，尝试逻辑基础表名
    base = table_prefix
    for _ in range(3):
        new_base = re.sub(r"_\d+$", "", base).rstrip("_")
        if not new_base or new_base == base:
            break
        base = new_base
        create_sql = call_show_create_table(domain, db, base)
        if create_sql:
            return create_sql, base
    return None, None


def parse_indexes_from_create(create_sql):
    """
    从 CREATE TABLE 语句中解析索引信息。
    返回 dict: { index_name: [col1, col2, ...] }
    """
    indexes = {}
    if not create_sql:
        return indexes
    # PRIMARY KEY
    m = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", create_sql, re.IGNORECASE)
    if m:
        cols = [c.strip().strip("`") for c in m.group(1).split(",")]
        indexes["PRIMARY"] = cols
    # KEY / UNIQUE KEY / INDEX
    for m in re.finditer(r"(?:UNIQUE\s+)?(?:KEY|INDEX)\s+`?(\w+)`?\s*\(([^)]+)\)", create_sql, re.IGNORECASE):
        name = m.group(1)
        cols = [c.strip().strip("`").split("(")[0] for c in m.group(2).split(",")]
        indexes[name] = cols
    return indexes


def extract_table_name(sql):
    """从 SQL 指纹中提取主表名（去掉分表后缀数字）"""
    # INSERT INTO tbl / UPDATE tbl / DELETE FROM tbl / SELECT ... FROM tbl
    m = (
        re.search(r"INSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?", sql, re.IGNORECASE)
        or re.search(r"UPDATE\s+`?(\w+)`?", sql, re.IGNORECASE)
        or re.search(r"DELETE\s+FROM\s+`?(\w+)`?", sql, re.IGNORECASE)
        or re.search(r"FROM\s+`?(\w+)`?", sql, re.IGNORECASE)
    )
    if not m:
        return None
    tbl = m.group(1)
    # 去掉分表数字后缀 e.g. member_play_info_0 -> member_play_info
    tbl = re.sub(r"_\d+$", "", tbl)
    tbl = tbl.rstrip("_")  # 去掉尾部多余下划线（如 member_play_info_）
    return tbl


def extract_where_cols(sql):
    """从 WHERE 子句中提取条件字段名"""
    m = re.search(r"WHERE(.+?)(?:ORDER|GROUP|LIMIT|HAVING|$)", sql, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    where = m.group(1)
    return [
        c.strip("`") for c in re.findall(r"`?(\w+)`?\s*(?:=|IN|LIKE|>|<|>=|<=|<>|!=|BETWEEN)", where, re.IGNORECASE)
    ]


def extract_orderby_cols(sql):
    """从 ORDER BY 子句中提取字段名"""
    m = re.search(r"ORDER\s+BY\s+(.+?)(?:LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    return [c.strip().strip("`").split()[0] for c in m.group(1).split(",")]


def analyze_with_schema(domain, db, sql, ex_status):
    """
    EXPLAIN 失败或结果不可靠时，通过 SHOW CREATE TABLE 分析索引并给建议。
    返回 (advice_lines, schema_info)
    """
    table = extract_table_name(sql)
    if not table or not db:
        return [f"无法解析表名，跳过索引分析"], None

    create_sql = call_show_create_table(domain, db, table)
    if not create_sql:
        create_sql, matched = call_show_create_table_like(domain, db, table)
        if matched and matched != table:
            table = matched  # 用实际找到的表名
    if not create_sql:
        return [f"获取表结构失败（{table}），无法分析索引"], None

    indexes = parse_indexes_from_create(create_sql)
    where_cols = extract_where_cols(sql)
    orderby_cols = extract_orderby_cols(sql)
    all_indexed = set()
    for cols in indexes.values():
        for c in cols:
            all_indexed.add(c.lower())

    advice = []
    schema_info = f"表 `{table}` 索引：" + (
        "、".join(f"{n}({','.join(c)})" for n, c in indexes.items()) if indexes else "无索引"
    )

    missing_where = [c for c in where_cols if c.lower() not in all_indexed]
    missing_order = [c for c in orderby_cols if c.lower() not in all_indexed]

    if missing_where:
        advice.append(f"WHERE 字段 {missing_where} 未在索引中，建议添加索引")
    if missing_order:
        advice.append(f"ORDER BY 字段 {missing_order} 未在索引中，建议添加索引")
    if where_cols and not missing_where:
        advice.append(f"WHERE 字段 {where_cols} 已有索引覆盖，请确认选择性")
    if is_insert_values(sql):
        advice.append("INSERT VALUES 写操作，关注是否存在唯一键冲突或锁等待")
    if not advice:
        advice.append("表结构已分析，暂未发现明显索引缺失")

    return advice, schema_info


def explain_issues(ex, rows_examined_max=0):
    """分析 EXPLAIN 结果，返回 (issues, suggestions)

    ⚠️ 误报排除优先级最高，满足以下任一条件直接返回空（索引正常）：
      1. Extra 含 'no matching row in const table'：MySQL 已用索引定位，行不存在短路，非问题
      2. EXPLAIN rows 远大于 rows_examined_max：rows 为估算值，以实际扫描行数为准
    """
    if not ex:
        return [], []
    issues, suggestions = [], []
    t = (ex.get("type") or "").lower()
    key = ex.get("key")
    extra = ex.get("Extra") or ""
    rows = ex.get("rows")
    try:
        rows_int = int(rows) if rows else 0
    except Exception:
        rows_int = 0
    try:
        rows_ex_int = int(rows_examined_max) if rows_examined_max else 0
    except Exception:
        rows_ex_int = 0

    # ── 误报排除 1：no matching row in const table ──
    if "no matching row in const table" in extra:
        return [], ["type=const, key=PRIMARY（主键等值查询，行不存在短路，索引正常）"]  # 索引已命中，master 无数据短路，非性能问题

    # ── 误报排除 2：EXPLAIN rows 远大于实际 rows_examined_max ──
    if rows_int > 10000 and rows_ex_int > 0 and rows_ex_int <= rows_int * 0.01:
        # 实际扫描行数不足估算的 1%，说明索引有效，EXPLAIN rows 为统计估算偏大
        # 继续做其他检查（type/key/extra），但不基于 rows 报警
        rows_int = 0  # 清零，后续 rows 相关判断不触发

    if not t:
        return ["常量优化，EXPLAIN 结果不具参考意义（将通过表结构分析）"], []
    if t == "all":
        issues.append("全表扫描 (type=ALL)")
        suggestions.append("在 WHERE/JOIN 条件字段上添加索引")
    elif t == "index":
        # type=index 需结合实际扫描行数判断，仅 rows_examined_max 也大时才报警
        if rows_ex_int > 10000:
            issues.append(f"全索引扫描 (type=index)，实际扫描 {rows_ex_int:,} 行")
            suggestions.append("考虑覆盖索引优化，减少扫描行数")
    if key is None and t not in ("", "null"):
        issues.append("未命中任何索引 (key=NULL)")
        suggestions.append("检查 WHERE 条件字段是否建立索引")
    if "Using filesort" in extra:
        issues.append("文件排序 (Using filesort)")
        suggestions.append("在 ORDER BY 字段上添加复合索引")
    if "Using temporary" in extra:
        issues.append("使用临时表 (Using temporary)")
        suggestions.append("优化 GROUP BY / ORDER BY，避免临时表")
    # rows 大只在 ALL/index 场景报警（已在上面处理），其他 type 不单独报 rows
    return issues, suggestions


def has_real_issue(row, explain_data, domain):
    """判断该条慢查询是否存在真实索引/性能问题，用于排序“有问题的提前”。
    返回 (has_issue: bool, priority: int)，priority 越小越靠前。
    """
    k = (row.get("query_digest_md5") or "").upper()[:8]
    rex = int(row.get("rows_examined_max") or 0)
    ex_r, ex_s, _, _ = (explain_data.get(domain) or {}).get(k, (None, "no_file", [], None))
    t = (ex_r.get("type") or "").lower() if ex_r else ""
    key = ex_r.get("key") if ex_r else None
    extra = (ex_r.get("Extra") or "") if ex_r else ""

    # 真实全表扫描： type=ALL 且实际扫描行数大
    if t == "all" and rex > 100:
        return True, 10
    # 真实全索引扫描： type=index 且实际扫描行数大
    if t == "index" and rex > 10000:
        return True, 20
    # 未命中索引（排除 no matching row 误报）
    if key is None and t not in ("", "null") and "no matching row" not in extra:
        return True, 30
    # rows_examined_max 自身就大
    if rex > 10000:
        return True, 40
    return False, 100


# ── 数据采集 ──────────────────────────────────────────────────────────
# ── 数据采集 ──────────────────────────────────────────────────────────
slowlog_data = {}
metrics_data = {}
ROLE_LABELS = [("proxy", "Proxy/Spider"), ("master", "Master/Remote-M"), ("remote", "Slave/Remote-S")]

for domain in DOMAINS:
    roles = get_roles(domain)
    today = load_digests(os.path.join(DATA_DIR, f"pcr_cur_{domain}_*.json"))
    yest = load_digests(os.path.join(DATA_DIR, f"pcr_base_{domain}_*.json"))
    new = {k: v for k, v in today.items() if k not in yest}
    groups = {}
    for k, row in new.items():
        cat = classify(row)
        groups.setdefault(cat, []).append((k, row))
    slowlog_data[domain] = {"today": today, "yest": yest, "new": new, "groups": groups}

    metrics_data[domain] = {}
    for rk in ("proxy", "master", "remote"):
        ar = roles[rk]
        metrics_data[domain][rk] = {
            "actual": ar,
            "cpu_cur": get_stat(os.path.join(DATA_DIR, f"pcr_metrics_cur_{domain}_cpu_summary.json"), ar),
            "cpu_base": get_stat(os.path.join(DATA_DIR, f"pcr_metrics_base_{domain}_cpu_summary.json"), ar),
            "qps_cur": get_stat(os.path.join(DATA_DIR, f"pcr_metrics_cur_{domain}_qps_summary.json"), ar),
            "qps_base": get_stat(os.path.join(DATA_DIR, f"pcr_metrics_base_{domain}_qps_summary.json"), ar),
        }

# ── EXPLAIN 数据加载 ──────────────────────────────────────────────────
# explain_data: {domain: {digest: (result_or_None, status, schema_advice, schema_info)}}
explain_data = {}
for domain in DOMAINS:
    explain_data[domain] = {}
    # 遍历 today 全量（不只是新增），确保存量 SQL 也能加载 EXPLAIN
    for k, row in slowlog_data[domain]["today"].items():
        sql = row.get("query_digest_text") or row.get("query_string") or ""
        db = row.get("query_db_name", "")
        cat = classify(row)
        if cat in SKIP_EXPLAIN_SQL:
            explain_data[domain][k] = (None, "skip_type", [], None)
            continue
        if not db:
            explain_data[domain][k] = (None, "no_db", [], None)
            continue
        if is_insert_values(sql):
            explain_data[domain][k] = (None, "insert_values", [], None)
            continue
        ex_result, ex_status = load_explain(domain, k)
        is_new_digest = k in slowlog_data[domain]["new"]
        needs_schema = False  # schema查询已禁用
        adv, sch = [], None
        explain_data[domain][k] = (ex_result, ex_status, adv, sch)

# ── 综合结论 ──────────────────────────────────────────────────────────
conclusions = []
for domain in DOMAINS:
    sl = slowlog_data[domain]
    new_cnt = len(sl["new"])
    max_cpu_delta = 0
    max_cpu_max_delta = 0
    max_qps_pct = 0
    risk_count = 0
    for rk in ("proxy", "master", "remote"):
        r = metrics_data[domain][rk]
        ta, tm = r["cpu_cur"]
        ya, ym = r["cpu_base"]
        if ta and ya:
            d = ta - ya
            if abs(d) > abs(max_cpu_delta):
                max_cpu_delta = d
        if tm and ym:
            d = tm - ym
            if abs(d) > abs(max_cpu_max_delta):
                max_cpu_max_delta = d
        ta, _ = r["qps_cur"]
        ya, _ = r["qps_base"]
        if ta and ya and ya > 0:
            p = (ta - ya) / ya * 100
            if abs(p) > abs(max_qps_pct):
                max_qps_pct = p
    # 统计风险数量
    for k, row in sl["today"].items():
        is_issue, _ = has_real_issue(row, explain_data, domain)
        if is_issue:
            risk_count += 1
    issues = []
    if new_cnt > 0:
        issues.append(f"新增 {new_cnt} 条慢查询")
    if max_cpu_delta > 5:
        issues.append(f"CPU avg 升高 {max_cpu_delta:+.1f}%")
    if max_cpu_max_delta > 5:
        issues.append(f"CPU max 升高 {max_cpu_max_delta:+.1f}%")
    if max_qps_pct > 50:
        issues.append(f"QPS 暴增 {max_qps_pct:+.0f}%")
    if max_qps_pct < -30:
        issues.append(f"QPS 大幅下跌 {max_qps_pct:+.0f}%")
    if risk_count > 0:
        issues.append(f"风险 SQL {risk_count} 条")
    conclusions.append(
        {
            "domain": domain,
            "new_cnt": new_cnt,
            "risk_count": risk_count,
            "cpu_delta": max_cpu_delta,
            "cpu_max_delta": max_cpu_max_delta,
            "qps_pct": max_qps_pct,
            "issues": issues,
            "status": "warn" if issues else "ok",
        }
    )

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── Chart.js 数据 ─────────────────────────────────────────────────────
short_labels = [d.split(".")[0] + "." + d.split(".")[1] for d in DOMAINS]
cpu_proxy_cur = [metrics_data[d]["proxy"]["cpu_cur"][0] or 0 for d in DOMAINS]
cpu_proxy_base = [metrics_data[d]["proxy"]["cpu_base"][0] or 0 for d in DOMAINS]
cpu_master_cur = [metrics_data[d]["master"]["cpu_cur"][0] or 0 for d in DOMAINS]
cpu_master_base = [metrics_data[d]["master"]["cpu_base"][0] or 0 for d in DOMAINS]
qps_master_cur = [
    (metrics_data[d]["master"]["qps_cur"][0] or metrics_data[d]["proxy"]["qps_cur"][0] or 0) for d in DOMAINS
]
qps_master_base = [
    (metrics_data[d]["master"]["qps_base"][0] or metrics_data[d]["proxy"]["qps_base"][0] or 0) for d in DOMAINS
]
new_counts = [len(slowlog_data[d]["new"]) for d in DOMAINS]


def js_arr(lst):
    return "[" + ",".join(str(x) for x in lst) + "]"


def js_strarr(lst):
    return "[" + ",".join(f'"{esc(x)}"' for x in lst) + "]"


# ══════════════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════════════
HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>性能对比分析报告 · {args.analysis_start[:10]}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
     background:#f0f2f5;color:#1a1a2e;font-size:14px;line-height:1.6}}
.page{{max-width:1280px;margin:0 auto;padding:24px 16px}}
.header{{background:linear-gradient(135deg,#1e3a5f 0%,#2563a8 100%);
        border-radius:14px;padding:28px 32px;color:#fff;margin-bottom:22px;
        box-shadow:0 6px 24px rgba(30,58,95,.35)}}
.header h1{{font-size:22px;font-weight:700;margin-bottom:14px;letter-spacing:.4px}}
.header h1 span{{opacity:.7;font-size:15px;font-weight:400;margin-left:10px}}
.meta-grid{{display:flex;flex-wrap:wrap;gap:10px 28px}}
.meta-item .lbl{{opacity:.6;font-size:12px;margin-right:4px}}
.meta-item .val{{font-weight:600;font-size:13px}}
.nav{{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}}
.nav a{{background:#fff;padding:7px 16px;border-radius:8px;font-size:13px;font-weight:500;
       color:#2563a8;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;transition:all .15s;
       text-decoration:none;display:inline-block}}
.nav a:hover{{background:#2563a8;color:#fff;box-shadow:0 2px 8px rgba(37,99,168,.3)}}
.section{{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;
         box-shadow:0 2px 10px rgba(0,0,0,.06)}}
.sec-title{{font-size:16px;font-weight:700;color:#1e3a5f;margin-bottom:18px;
           padding-bottom:10px;border-bottom:2px solid #e8f0fe;
           display:flex;align-items:center;gap:8px}}
.sec-title .ico{{font-size:18px}}
.charts-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:4px}}
.chart-box{{background:#f8faff;border-radius:10px;padding:16px}}
.chart-box h3{{font-size:13px;font-weight:600;color:#2563a8;margin-bottom:12px;text-align:center}}
.chart-wrap{{position:relative;height:260px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.card{{border-radius:10px;padding:15px 16px;border-left:4px solid #e0e7ff;
      background:#fafbff;transition:transform .15s,box-shadow .15s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.1)}}
.card.warn{{border-left-color:#e74c3c;background:#fff8f8}}
.card.ok{{border-left-color:#27ae60;background:#f7fdf9}}
.card-domain{{font-size:11px;color:#666;margin-bottom:5px;font-family:monospace}}
.card-status{{font-size:14px;font-weight:700;margin-bottom:6px}}
.card-issues{{font-size:12px;color:#555}}
.card-metrics{{display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:#555;margin-bottom:6px}}
.card-metrics span{{background:#f0f0f0;padding:2px 6px;border-radius:4px;white-space:nowrap}}
.card-issues li{{list-style:none;padding-left:14px;position:relative;margin-top:2px}}
.card-issues li::before{{content:"·";position:absolute;left:0;color:#e74c3c;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#f0f4ff;color:#2563a8;font-weight:600;padding:10px 12px;
   text-align:left;border-bottom:2px solid #dce8fb;white-space:nowrap}}
td{{padding:9px 12px;border-bottom:1px solid #f0f2f8;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#f8faff}}
.num{{text-align:right;font-variant-numeric:tabular-nums;
     font-family:'SF Mono',Consolas,monospace}}
.domain-td{{font-weight:600;color:#1e3a5f;white-space:nowrap}}
.role-td{{color:#888;font-size:12px;padding-left:20px !important}}
.sql-fp{{font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#c0392b;
         background:#fdf2f2;padding:2px 6px;border-radius:4px;
         word-break:break-all;display:block}}
code{{font-family:'SF Mono',Consolas,monospace;font-size:12px;
     background:#f1f3f9;padding:1px 5px;border-radius:3px;color:#2563a8}}
.badge{{display:inline-flex;align-items:center;gap:3px;padding:2px 9px;
       border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}}
.badge-warn{{background:#ffeaea;color:#c0392b}}
.badge-ok{{background:#e8f8ef;color:#1a7a45}}
.chg-up{{color:#e67e22;font-weight:700}}
.chg-dn{{color:#2980b9;font-weight:600}}
.chg-ok{{color:#27ae60}}
.chg-alert{{color:#e74c3c;font-weight:700}}
.cluster-block{{margin-bottom:28px;padding-bottom:20px;border-bottom:1px dashed #e8ecf4}}
.cluster-block:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.cluster-hd{{font-size:14px;font-weight:700;color:#1e3a5f;margin-bottom:12px;
            background:#f4f7ff;padding:8px 14px;border-radius:8px;
            border-left:4px solid #2563a8}}
.sl-cat-hd{{display:inline-block;font-size:12px;font-weight:700;color:#2563a8;
           background:#eef3ff;padding:4px 10px;border-radius:6px;margin:10px 0 8px}}
.conc-warn{{color:#e74c3c;font-weight:700}}
.conc-ok{{color:#27ae60;font-weight:600}}
.warn-text{{color:#e74c3c;font-weight:700}}
.ex-issue{{font-size:11px;color:#e74c3c}}
.ex-suggest{{font-size:11px;color:#2563a8}}
.ex-ok{{font-size:11px;color:#27ae60}}
.ex-extra{{font-size:10px;color:#999;margin-top:2px}}
.analysis-toolbar{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  padding:8px 12px;background:#f4f7ff;border-radius:6px;margin-bottom:10px;
  border:1px solid #dce8fb;font-size:12px}}
.ex-na{{font-size:11px;color:#aaa}}
.ex-type{{white-space:nowrap;font-family:'SF Mono',Consolas,monospace;font-size:12px}}
.ex-key{{white-space:nowrap;font-family:'SF Mono',Consolas,monospace;font-size:12px;max-width:100px;overflow:hidden;text-overflow:ellipsis;display:inline-block;vertical-align:middle}}
.ex-advice{{min-width:220px;line-height:1.7}}
.footer{{text-align:center;color:#aaa;font-size:12px;padding:20px 0 8px}}
@media(max-width:768px){{.charts-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="page">

<div class="header">
  <h1>⚡ 性能对比分析报告 <span>mysql-perf-compare-report</span></h1>
  <div class="meta-grid">
    <div class="meta-item"><span class="lbl">生成时间</span><span class="val">{now}</span></div>
    <div class="meta-item"><span class="lbl">分析时段</span><span class="val">{esc(args.analysis_start)} ~ {esc(args.analysis_end)}</span></div>
    <div class="meta-item"><span class="lbl">慢查询基准</span><span class="val">{esc(args.baseline_date)} 全天</span></div>
    <div class="meta-item"><span class="lbl">负载基准</span><span class="val">{esc(args.metrics_baseline_start)} ~ {esc(args.metrics_baseline_end)}</span></div>
    <div class="meta-item"><span class="lbl">集群数量</span><span class="val">{len(DOMAINS)} 个</span></div>
  </div>
</div>

<div class="nav">
  <a onclick="document.getElementById('overview').scrollIntoView({{behavior:'smooth'}})"> 概览</a>
  <a onclick="document.getElementById('conclusion').scrollIntoView({{behavior:'smooth'}})"> 结论</a>
  <a onclick="document.getElementById('charts').scrollIntoView({{behavior:'smooth'}})"> 图表</a>
  <a onclick="document.getElementById('slowlog').scrollIntoView({{behavior:'smooth'}})"> 慢查询</a>
  <a onclick="document.getElementById('slowlog-detail').scrollIntoView({{behavior:'smooth'}})"> 慢查询明细</a>
  <a onclick="document.getElementById('cpu').scrollIntoView({{behavior:'smooth'}})">️ CPU</a>
  <a onclick="document.getElementById('qps').scrollIntoView({{behavior:'smooth'}})"> QPS</a>
  <a onclick="document.getElementById('slowlog-analysis').scrollIntoView({{behavior:'smooth'}})"> 慢查询分析</a>
</div>
"""

# ── 概览卡片 ──────────────────────────────────────────────────────────
HTML += """<div class="section" id="overview">
  <div class="sec-title"><span class="ico"></span>综合概览</div>
  <div class="cards">
"""
for c in conclusions:
    scls = "warn" if c["status"] == "warn" else "ok"
    icon = "⚠️" if c["status"] == "warn" else "✅"
    label = "需关注" if c["status"] == "warn" else "正常"
    issues_html = (
        (
            '<ul class="card-issues">'
            + "".join(f"<li>{esc(i)}</li>" for i in c["issues"] if "CPU" not in i and "风险" not in i)
            + "</ul>"
        )
        if c["issues"]
        else '<div class="card-issues" style="color:#27ae60;font-size:12px">无异常</div>'
    )
    HTML += f"""    <div class="card {scls}">
      <div class="card-domain">{esc(c['domain'])}</div>
      <div class="card-status">{icon} {label}</div>
      <div class="card-metrics">
        <span>CPU avg: {c['cpu_delta']:+.1f}%</span>
        <span>CPU max: {c['cpu_max_delta']:+.1f}%</span>
        <span>风险: {c['risk_count']} 条</span>
      </div>
      {issues_html}
    </div>\n"""
HTML += """ </div>
</div>

"""


# ── 六、综合结论 ──────────────────────────────────────────────────────
HTML += """<div class="section" id="conclusion">
  <div class="sec-title"><span class="ico"></span>六、综合结论</div>
  <table>
    <thead><tr>
      <th>集群</th><th>慢查询</th><th>CPU avg 变化</th><th>CPU max 变化</th><th>QPS 变化</th><th>风险</th><th>结论</th>
    </tr></thead><tbody>
"""
for c in conclusions:
    sl_b = badge(f"⚠️ 新增 {c['new_cnt']} 条", "warn") if c["new_cnt"] > 0 else badge("✅ 无新增", "ok")
    cpu_sym, cpu_cls = cpu_flag(c["cpu_delta"])
    cpu_s = chg_span(f"{cpu_sym} {c['cpu_delta']:+.1f}%", "alert" if abs(c["cpu_delta"]) > 5 else cpu_cls)
    cpu_max_sym, cpu_max_cls = cpu_flag(c["cpu_max_delta"])
    cpu_max_s = chg_span(
        f"{cpu_max_sym} {c['cpu_max_delta']:+.1f}%", "alert" if abs(c["cpu_max_delta"]) > 5 else cpu_max_cls
    )
    qps_pct_str = f"{'+' if c['qps_pct'] >= 0 else ''}{c['qps_pct']:.0f}%"
    qps_sym = "↑" if c["qps_pct"] > 20 else ("↓" if c["qps_pct"] < -20 else "≈")
    qps_cls = (
        "alert" if abs(c["qps_pct"]) > 50 else ("up" if c["qps_pct"] > 20 else ("dn" if c["qps_pct"] < -20 else "ok"))
    )
    qps_s = chg_span(f"{qps_sym} {qps_pct_str}", qps_cls)
    risk_b = badge(f"⚠️ {c['risk_count']} 条", "warn") if c["risk_count"] > 0 else badge("✅ 0 条", "ok")
    if c["issues"]:
        conc = '<span class="conc-warn">⚠️ ' + "、".join(esc(i) for i in c["issues"]) + "</span>"
    else:
        conc = '<span class="conc-ok">✅ 正常</span>'
    HTML += (
        f'    <tr><td class="domain-td">{esc(c["domain"])}</td>'
        f"<td>{sl_b}</td><td>{cpu_s}</td><td>{cpu_max_s}</td><td>{qps_s}</td><td>{risk_b}</td><td>{conc}</td></tr>\n"
    )
HTML += " </tbody></table>\n</div>\n\n"

# ── 图表区 ────────────────────────────────────────────────────────────
HTML += f"""<div class="section" id="charts">
  <div class="sec-title"><span class="ico"></span>监控图表对比</div>
  <div class="charts-grid">
    <div class="chart-box">
      <h3>️ CPU avg — Proxy/Spider (%)</h3>
      <div class="chart-wrap"><canvas id="chartCpuProxy"></canvas></div>
    </div>
    <div class="chart-box">
      <h3>️ CPU avg — Master/Remote-M (%)</h3>
      <div class="chart-wrap"><canvas id="chartCpuMaster"></canvas></div>
    </div>
    <div class="chart-box">
      <h3> QPS avg — Master/Spider</h3>
      <div class="chart-wrap"><canvas id="chartQps"></canvas></div>
    </div>
    <div class="chart-box">
      <h3> 新增慢查询数量</h3>
      <div class="chart-wrap"><canvas id="chartSlowlog"></canvas></div>
    </div>
  </div>
</div>

"""

# ── 一、新增慢查询汇总 ─────────────────────────────────────────────────
HTML += """<div class="section" id="slowlog">
  <div class="sec-title"><span class="ico"></span>一、新增慢查询汇总（完全匹配模式）</div>
  <table>
    <thead><tr>
      <th>集群</th>
      <th class="num">本次 digest</th>
      <th class="num">基准 digest</th>
      <th class="num">新增</th>
      <th>状态</th>
    </tr></thead><tbody>
"""
for domain in DOMAINS:
    r = slowlog_data[domain]
    n = len(r["new"])
    b = badge(f"⚠️ +{n}", "warn") if n > 0 else badge("✅ 无新增", "ok")
    new_td = f"<b>{n}</b>" if n > 0 else "0"
    HTML += f'      <tr><td class="domain-td">{esc(domain)}</td><td class="num">{len(r["today"])}</td><td class="num">{len(r["yest"])}</td><td class="num">{new_td}</td><td>{b}</td></tr>\n'
HTML += " </tbody></table>\n</div>\n\n"

# ── 二、新增慢查询明细（含 EXPLAIN 索引分析） ────────────────────────────
HTML += '<div class="section" id="slowlog-detail">\n'
HTML += ' <div class="sec-title"><span class="ico"></span>二、新增慢查询明细（含索引分析）</div>\n'
has_new = any(slowlog_data[d]["new"] for d in DOMAINS)
if not has_new:
    HTML += '  <p style="color:#27ae60;font-weight:600;padding:8px 0">✅ 所有集群均无新增慢查询</p>\n'
else:
    for domain in DOMAINS:
        groups = slowlog_data[domain]["groups"]
        if not groups:
            continue
        total = sum(len(v) for v in groups.values())
        HTML += f'  <div class="cluster-block">\n    <div class="cluster-hd">{esc(domain)}（新增 {total} 条）</div>\n'
        for cat in sorted(groups):
            items = groups[cat]
            HTML += f'    <div class="sl-cat-hd">[{esc(cat)}] {len(items)} 条</div>\n'
            HTML += """    <table><thead><tr>
      <th>digest</th><th>db</th><th>SQL 指纹</th>
      <th class="num">cnt</th><th class="num">rows_examined</th><th class="num">qt_max(s)</th>
      <th>标记</th><th>type</th><th>key</th><th>索引分析与建议</th>
    </tr></thead><tbody>\n"""
            for k, row in sorted(
                items,
                key=lambda x: (
                    0 if has_real_issue(x[1], explain_data, domain)[0] else 1,
                    has_real_issue(x[1], explain_data, domain)[1],
                    -(x[1].get("query_time_max") or 0),
                ),
            ):
                db = esc(row.get("query_db_name", ""))
                cnt = row.get("count_star", 0)
                qt = row.get("query_time_max", 0)
                rex = row.get("rows_examined_max", 0)
                sql_raw = row.get("query_digest_text") or row.get("query_string") or ""
                sql_fp_short = esc(sql_raw[:400])
                sql_fp_full = esc(sql_raw)
                sql_fp = f'<span title="{sql_fp_full}">{sql_fp_short}{"…" if len(sql_raw)>400 else ""}</span>'
                ex_result, ex_status, schema_adv, schema_info = explain_data.get(domain, {}).get(
                    k, (None, "no_file", [], None)
                )
                if ex_result is not None:
                    extra_val = ex_result.get("Extra") or ""
                    _is_no_match = "no matching row" in extra_val
                    if _is_no_match:
                        ex_type = "const"
                        ex_key = "PRIMARY"
                    else:
                        ex_type = esc(ex_result.get("type") or "N/A")
                        ex_key = esc(ex_result.get("key") or "NULL")
                    ex_rows = esc(str(ex_result.get("rows") or "N/A"))
                    ex_extra = extra_val
                    issues, suggestions = explain_issues(ex_result, rex)
                    # type=ALL/index 标红需结合 rows_examined_max：实际扫描行数小时不标红
                    _t_lower = (ex_result.get("type") or "").lower()
                    _rex_int = int(rex) if rex else 0
                    _is_real_warn = _t_lower in ("all", "index") and _rex_int > 100
                    type_cls = "warn-text" if _is_real_warn else ""
                    key_cls = (
                        "warn-text"
                        if (ex_result.get("key") is None and _t_lower not in ("", "null") and not _is_no_match)
                        else ""
                    )
                    # 通用建议（与慢查询总体分析保持一致）
                    adv_parts = []
                    if rex and int(rex) > 10000:
                        adv_parts.append(f'<div class="ex-issue">⚠️ rows_examined={int(rex):,}，扫描行数多，检查索引覆盖</div>')
                    if qt and float(qt) > 1:
                        rex_int = int(rex) if rex else 0
                        if rex_int <= 1:
                            adv_parts.append(
                                f'<div class="ex-ok">✅ 单次最慢 {qt}s，rows_examined={rex_int} 索引正常，慢在等待（行锁/proxy排队/IO抖动），非 SQL 问题</div>'
                            )
                        elif rex_int <= 100:
                            adv_parts.append(
                                f'<div class="ex-ok">✅ 单次最慢 {qt}s，rows_examined={rex_int}，扫描行数少，慢在等待而非全表扫描</div>'
                            )
                        else:
                            adv_parts.append(
                                f'<div class="ex-issue">⚠️ 单次最慢 {qt}s，rows_examined={rex_int}，关注索引覆盖</div>'
                            )
                    if cnt and int(cnt) > 1000:
                        adv_parts.append(f'<div class="ex-suggest"> 执行 {int(cnt):,} 次，高频 SQL，优先优化</div>')
                    # EXPLAIN 分析建议
                    for s in suggestions:
                        adv_parts.append(f'<div class="ex-suggest"> {esc(s)}</div>')
                    for i in issues:
                        adv_parts.append(f'<div class="ex-issue">⚠️ {esc(i)}</div>')
                    if ex_extra:
                        adv_parts.append(f'<div class="ex-extra">Extra: {esc(ex_extra)}</div>')
                    # 追加 schema 分析建议
                    if schema_adv:
                        if schema_info:
                            adv_parts.append(f'<div class="ex-extra"> {esc(schema_info)}</div>')
                        for a in schema_adv:
                            adv_parts.append(f'<div class="ex-suggest"> {esc(a)}</div>')
                    if not adv_parts:
                        adv_parts.append('<div class="ex-ok">✅ 索引使用正常</div>')
                    advice = "".join(adv_parts)
                    ex_type_td = f'<span class="{type_cls}">{ex_type}</span>' if type_cls else ex_type
                    ex_key_td = f'<span class="{key_cls}">{ex_key}</span>' if key_cls else ex_key
                elif ex_status == "insert_values":
                    ex_type_td = ex_key_td = ex_rows = "—"
                    adv_lines = schema_adv or ["INSERT VALUES 写操作，无索引扫描路径"]
                    advice = "".join(f'<div class="ex-suggest"> {esc(a)}</div>' for a in adv_lines)
                    if schema_info:
                        advice = f'<div class="ex-extra"> {esc(schema_info)}</div>' + advice
                elif ex_status == "skip_type":
                    ex_type_td = ex_key_td = ex_rows = "—"
                    advice = '<div class="ex-na">该类型不适用 EXPLAIN</div>'
                elif ex_status == "no_db":
                    ex_type_td = ex_key_td = ex_rows = "—"
                    adv_lines = schema_adv or ["db 字段为空，无法执行 EXPLAIN"]
                    advice = "".join(f'<div class="ex-suggest"> {esc(a)}</div>' for a in adv_lines)
                else:
                    ex_type_td = ex_key_td = ex_rows = "—"
                    adv_lines = schema_adv or [f"EXPLAIN 未执行 ({ex_status})"]
                    advice = "".join(f'<div class="ex-suggest"> {esc(a)}</div>' for a in adv_lines)
                    if schema_info:
                        advice = f'<div class="ex-extra"> {esc(schema_info)}</div>' + advice
                _has_issue, _ = has_real_issue(row, explain_data, domain)
                _new_badge = badge("⚠️ 有风险", "warn") if _has_issue else badge("✅ 无风险", "ok")
                _row_cls = ""
                HTML += (
                    f"      <tr{_row_cls}><td><code>{k}</code></td><td>{db}</td>"
                    f'<td class="sql-fp">{sql_fp}</td>'
                    f'<td class="num">{cnt}</td><td class="num">{rex:,}</td><td class="num">{qt}s</td>'
                    f"<td>{_new_badge}</td>"
                    f'<td class="ex-type">{ex_type_td}</td>'
                    f'<td class="ex-key">{ex_key_td}</td>'
                    f'<td class="ex-advice">{advice}</td></tr>\n'
                )
            HTML += "    </tbody></table>\n"
        HTML += "  </div>\n"
HTML += "</div>\n\n"

# ── 三、CPU 对比 ──────────────────────────────────────────────────────
HTML += f"""<div class="section" id="cpu">
  <div class="sec-title"><span class="ico">️</span>三、CPU 对比（单位 %）
    <span style="font-size:12px;font-weight:400;color:#888;margin-left:8px">基准：{esc(args.metrics_baseline_start)} ~ {esc(args.metrics_baseline_end)}</span>
  </div>
  <table>
    <thead><tr>
      <th>集群</th><th>角色</th>
      <th class="num">本次 avg</th><th class="num">本次 max</th>
      <th class="num">基准 avg</th><th class="num">基准 max</th>
      <th>avg 变化</th><th>max 变化</th>
    </tr></thead><tbody>
"""
for domain in DOMAINS:
    first = True
    for rk, rl in ROLE_LABELS:
        r = metrics_data[domain][rk]
        ta, tm = r["cpu_cur"]
        ya, ym = r["cpu_base"]
        if ta is None and ya is None:
            continue
        dname = f'<span class="domain-td">{esc(domain)}</span>' if first else ""
        first = False
        if ta is not None and ya is not None:
            delta = ta - ya
            sym, cls = cpu_flag(delta)
            chg = chg_span(f"{sym} {delta:+.2f}%", "alert" if abs(delta) > 5 else cls)
        elif ta is not None:
            chg = chg_span("基准无数据", "ok")
        else:
            chg = chg_span("本次无数据", "ok")
        if tm is not None and ym is not None:
            max_delta = tm - ym
            sym_m, cls_m = cpu_flag(max_delta)
            chg_max = chg_span(f"{sym_m} {max_delta:+.2f}%", "alert" if abs(max_delta) > 5 else cls_m)
        elif tm is not None:
            chg_max = chg_span("基准无数据", "ok")
        else:
            chg_max = chg_span("本次无数据", "ok")
        HTML += (
            f'    <tr><td>{dname}</td><td class="role-td">{esc(rl)}</td>'
            f'<td class="num">{"N/A" if ta is None else f"{ta:.2f}%"}</td>'
            f'<td class="num">{"N/A" if tm is None else f"{tm:.2f}%"}</td>'
            f'<td class="num">{"N/A" if ya is None else f"{ya:.2f}%"}</td>'
            f'<td class="num">{"N/A" if ym is None else f"{ym:.2f}%"}</td>'
            f"<td>{chg}</td><td>{chg_max}</td></tr>\n"
        )
HTML += " </tbody></table>\n</div>\n\n"

# ── 四、QPS 对比 ──────────────────────────────────────────────────────
HTML += f"""<div class="section" id="qps">
  <div class="sec-title"><span class="ico"></span>四、QPS 对比
    <span style="font-size:12px;font-weight:400;color:#888;margin-left:8px">基准：{esc(args.metrics_baseline_start)} ~ {esc(args.metrics_baseline_end)}</span>
  </div>
  <table>
    <thead><tr>
      <th>集群</th><th>角色</th>
      <th class="num">本次 avg</th><th class="num">本次 max</th>
      <th class="num">基准 avg</th><th class="num">基准 max</th>
      <th>avg 变化</th><th>max 变化</th>
    </tr></thead><tbody>
"""
for domain in DOMAINS:
    first = True
    for rk, rl in ROLE_LABELS:
        r = metrics_data[domain][rk]
        ta, tm = r["qps_cur"]
        ya, ym = r["qps_base"]
        if ta is None and ya is None:
            continue
        dname = f'<span class="domain-td">{esc(domain)}</span>' if first else ""
        first = False
        if ta is not None and ya is not None:
            delta = ta - ya
            chg_txt, cls = qps_flag(delta, ya)
            pct_val = abs((delta / ya * 100)) if ya else 0
            chg = chg_span(chg_txt, "alert" if pct_val > 50 else cls)
        elif ta is not None:
            chg = chg_span("基准无数据", "ok")
        else:
            chg = chg_span("本次无数据", "ok")
        if tm is not None and ym is not None:
            max_delta = tm - ym
            max_pct = abs((max_delta / ym * 100)) if ym else 0
            chg_txt_m, cls_m = qps_flag(max_delta, ym)
            chg_max = chg_span(chg_txt_m, "alert" if max_pct > 50 else cls_m)
        elif tm is not None:
            chg_max = chg_span("基准无数据", "ok")
        else:
            chg_max = chg_span("本次无数据", "ok")
        HTML += (
            f'    <tr><td>{dname}</td><td class="role-td">{esc(rl)}</td>'
            f'<td class="num">{"N/A" if ta is None else f"{ta:.1f}"}</td>'
            f'<td class="num">{"N/A" if tm is None else f"{tm:.1f}"}</td>'
            f'<td class="num">{"N/A" if ya is None else f"{ya:.1f}"}</td>'
            f'<td class="num">{"N/A" if ym is None else f"{ym:.1f}"}</td>'
            f"<td>{chg}</td><td>{chg_max}</td></tr>\n"
        )
HTML += " </tbody></table>\n</div>\n\n"

# ── 五、集群慢查询总体分析与优化建议 ─────────────────────────────────────
HTML += '<div class="section" id="slowlog-analysis">\n'
HTML += ' <div class="sec-title"><span class="ico"></span>五、集群慢查询总体分析与优化建议</div>\n'

DEFAULT_TOPN = 20

for domain in DOMAINS:
    today = slowlog_data[domain]["today"]
    domain_safe = re.sub(r"[^a-zA-Z0-9]", "_", domain)
    if not today:
        HTML += f'  <div class="cluster-hd" style="color:#888;margin-bottom:12px">{esc(domain)}：本时段无慢查询记录</div>\n'
        continue

    # 全量写入所有 digest（TopN 逻辑由前端按用户输入的 N 动态计算）
    top_merged = sorted(
        today.values(),
        key=lambda r: (
            0 if has_real_issue(r, explain_data, domain)[0] else 1,
            has_real_issue(r, explain_data, domain)[1],
            -(r.get("query_time_sum") or 0),
        ),
    )

    # 构建每行数据（同时序列化为 JSON 供前端筛选/导出用）
    import json as _json

    rows_data = []
    rows_html_parts = []
    for row in top_merged:
        k = row.get("query_digest_md5", "").upper()[:8]
        db = row.get("query_db_name", "")
        cnt = row.get("count_star", 0)
        qt = row.get("query_time_max", 0)
        qs = round(row.get("query_time_sum") or 0, 2)
        rex = row.get("rows_examined_max", 0)
        sql_raw = row.get("query_digest_text") or row.get("query_string") or ""
        is_new = k in slowlog_data[domain]["new"]
        is_issue, issue_pri = has_real_issue(row, explain_data, domain)

        ex_r, ex_s, ex_adv, ex_sch = explain_data.get(domain, {}).get(k, (None, "no_file", [], None))

        # advice
        advices = []
        if rex and int(rex) > 10000:
            advices.append(f"rows_examined={int(rex):,}，扫描行数多，检查索引覆盖")
        if qt and float(qt) > 1:
            rex_int = int(rex) if rex else 0
            if rex_int <= 1:
                advices.append(f"单次最慢 {qt}s，rows_examined={rex_int} 索引正常，慢在等待（行锁/proxy排队/IO抖动），非 SQL 问题")
            elif rex_int <= 100:
                advices.append(f"单次最慢 {qt}s，rows_examined={rex_int}，扫描行数少，慢在等待而非全表扫描")
            else:
                advices.append(f"单次最慢 {qt}s，rows_examined={rex_int}，关注索引覆盖")
        if cnt and int(cnt) > 1000:
            advices.append(f"执行 {int(cnt):,} 次，高频 SQL，优先优化")
        if ex_r is not None:
            _, es = explain_issues(ex_r, rex)
            for s in es:
                if s not in advices:
                    advices.append(s)
        for a in ex_adv or []:
            if a not in advices:
                advices.append(a)
        if ex_s in ("no_file", "syntax_err") or ex_r is None:
            pass  # schema查询已禁用
        if not advices:
            advices.append("暂无明显异常，持续观察")
        if ex_sch:
            advices.insert(0, f" {ex_sch}")

        # EXPLAIN 字段
        _t_lower = (ex_r.get("type") or "").lower() if ex_r else ""
        _rex_int = int(rex) if rex else 0
        _is_real_warn = _t_lower in ("all", "index") and _rex_int > 100
        _is_no_match = ex_r and "no matching row" in (ex_r.get("Extra") or "")
        if _is_no_match:
            ex_type_val = "const"
            ex_key_val = "PRIMARY"
        else:
            ex_type_val = (ex_r.get("type") or "—") if ex_r else "—"
            ex_key_val = (ex_r.get("key") or "NULL") if ex_r else "—"
        ex_rows_val = str(ex_r.get("rows") or "—") if ex_r else "—"
        type_cls = "warn-text" if _is_real_warn else ""
        key_cls = "warn-text" if (ex_r and ex_r.get("key") is None and not _is_no_match) else ""
        ex_type_td = f'<span class="{type_cls}">{esc(ex_type_val)}</span>' if type_cls else esc(ex_type_val)
        ex_key_td = f'<span class="{key_cls}">{esc(ex_key_val)}</span>' if key_cls else esc(ex_key_val)

        new_badge = badge("⚠️ 有风险", "warn") if is_issue else badge("✅ 无风险", "ok")
        advice_html = "".join(f'<div style="font-size:11px">• {esc(a)}</div>' for a in advices)
        sql_fp_full = esc(sql_raw)
        sql_fp_short = esc(sql_raw[:400]) + ("…" if len(sql_raw) > 400 else "")
        row_cls = ""

        rows_html_parts.append(
            f'      <tr{row_cls} data-issue="{1 if is_issue else 0}">\n'
            f"        <td><code>{k}</code></td><td>{esc(db)}</td>\n"
            f'        <td class="sql-fp"><span title="{sql_fp_full}">{sql_fp_short}</span></td>\n'
            f'        <td class="num">{cnt}</td><td class="num">{rex:,}</td><td class="num">{qt}s</td>\n'
            f"        <td>{new_badge}</td>"
            f'<td class="ex-type">{ex_type_td}</td><td class="ex-key">{ex_key_td}</td>\n'
            f'        <td class="ex-advice">{advice_html}</td>\n'
            f"      </tr>\n"
        )
        rows_data.append(
            {
                "digest": k,
                "db": db,
                "sql": sql_raw,
                "cnt": int(cnt or 0),
                "qt_max": float(qt or 0),
                "qt_sum": qs,
                "rows_ex": int(rex or 0),
                "is_new": is_new,
                "is_issue": is_issue,
                "issue_pri": issue_pri,
                "ex_type": ex_type_val,
                "ex_key": ex_key_val,
                "ex_rows": ex_rows_val,
                "advice": " | ".join(advices),
            }
        )

    rows_json = _json.dumps(rows_data, ensure_ascii=False)
    total_rows = len(rows_html_parts)

    HTML += f'  <div class="cluster-block" id="block_{domain_safe}">\n'
    HTML += f'    <div class="cluster-hd" id="hd_{domain_safe}">{esc(domain)}（共 {len(today)} 条 digest，默认 Top{DEFAULT_TOPN} 显示 <span id="hd_sub_{domain_safe}"></span>）</div>\n'
    HTML += (
        f'    <script>window.__saData=window.__saData||{{}};window.__saData["{domain_safe}"]={rows_json};</script>\n'
    )
    HTML += f"""
    <div class="analysis-toolbar">
      <label style="font-size:12px">Top N：<input type="number" id="topn_{domain_safe}" min="1" max="9999" value="{DEFAULT_TOPN}"
        style="width:55px;padding:3px 6px;border:1px solid #dce8fb;border-radius:4px;font-size:12px">
      </label>
      <select id="risk_{domain_safe}"
        style="padding:3px 8px;border:1px solid #dce8fb;border-radius:4px;font-size:12px">
        <option value="all">全部风险</option>
        <option value="issue">仅有风险</option>
        <option value="ok">仅无风险</option>
      </select>
      <button onclick="saQuery('{domain_safe}')"
        style="padding:3px 14px;background:#2563a8;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer"> 查询</button>
      <button onclick="saExport('{domain_safe}','{domain}')"
        style="padding:3px 12px;background:#27ae60;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer">⬇ 导出 Excel</button>
      <span id="count_{domain_safe}" style="font-size:12px;color:#888;margin-left:4px">共 {total_rows} 条</span>
    </div>
    <div id="tbl_wrap_{domain_safe}">
    <table id="tbl_{domain_safe}"><thead><tr>
      <th>digest</th><th>db</th><th>SQL 指纹</th>
      <th class="num">cnt</th><th class="num">rows_examined</th><th class="num">qt_max(s)</th><th>标记</th><th>type</th><th>key</th><th>优化建议（含索引分析）</th>
    </tr></thead><tbody>\n"""
    HTML += "".join(rows_html_parts)
    HTML += "    </tbody></table>\n    </div>\n  </div>\n"

HTML += "</div>\n\n"
HTML += """\n<script>\n"""
HTML += "// ── 慢查询总体分析：筛选（前端 display）+ 导出 Excel ──\nfunction saQuery(ds) {\n try {\n var topn = parseInt(document.getElementById('topn_' + ds).value) || 20;\n var risk = document.getElementById('risk_' + ds).value;\n var allData = (window.__saData || {})[ds] || [];\n var tbl = document.getElementById('tbl_' + ds);\n var countEl = document.getElementById('count_' + ds);\n var hdSub = document.getElementById('hd_sub_' + ds);\n if (!tbl) return;\n\n // 按用户输入 N 计算 topSet：qt_sum TopN + cnt TopN 去重\n var bySum = allData.slice().sort(function(a,b){return b.qt_sum - a.qt_sum;}).slice(0, topn).map(function(r){return r.digest;});\n var byCnt = allData.slice().sort(function(a,b){return b.cnt - a.cnt; }).slice(0, topn).map(function(r){return r.digest;});\n var topSet = {};\n bySum.concat(byCnt).forEach(function(d){ topSet[d] = 1; });\n var topCount = Object.keys(topSet).length;\n\n // 遍历行，按 topSet + 风险筛选决定显示/隐藏\n var rows = tbl.querySelectorAll('tbody tr');\n var shown = 0;\n rows.forEach(function(tr) {\n var code = tr.querySelector('code');\n var digest = code ? code.textContent.trim() : '';\n var issue = tr.getAttribute('data-issue') === '1';\n var inTop = !!topSet[digest];\n var matchRisk = (risk === 'all') ||\n (risk === 'issue' && issue) ||\n (risk === 'ok' && !issue);\n if (inTop && matchRisk) { tr.style.display = ''; shown++; }\n else { tr.style.display = 'none'; }\n });\n\n if (countEl) countEl.textContent = '当前显示 ' + shown + ' 条（qt_sum Top' + topn + ' + cnt Top' + topn + ' 去重 ' + topCount + ' 条）';\n if (hdSub) hdSub.textContent = '· qt_sum Top' + topn + ' + cnt Top' + topn + ' 去重 ' + topCount + ' 条，当前显示 ' + shown + ' 条';\n } catch(e) { console.error('saQuery error:', e); }\n}\n// ── 导出 CSV ──\nfunction saExport(ds, domainName) {\n var tbl = document.getElementById('tbl_' + ds);\n if (!tbl) return;\n var visibleRows = [];\n tbl.querySelectorAll('tbody tr').forEach(function(tr) {\n if (tr.style.display !== 'none') visibleRows.push(tr);\n });\n if (!visibleRows.length) { alert('当前无可见数据'); return; }\n var cols = [];\n tbl.querySelectorAll('thead th').forEach(function(th) {\n cols.push(th.textContent.replace(/\\s+/g,' ').trim());\n });\n function csvCell(s) {\n s = String(s || '').replace(/\\r?\\n/g,' ');\n if (s.indexOf(',')>=0||s.indexOf('\"')>=0) s='\"'+s.replace(/\"/g,'\"\"')+'\"';\n return s;\n }\n var lines = [cols.map(csvCell).join(',')];\n visibleRows.forEach(function(tr) {\n var cells = [];\n tr.querySelectorAll('td').forEach(function(td){ cells.push(csvCell(td.innerText||td.textContent)); });\n lines.push(cells.join(','));\n });\n var csv = '\\uFEFF' + lines.join('\\r\\n');\n var blob = new Blob([csv], {type:'text/csv;charset=utf-8'});\n var url = URL.createObjectURL(blob);\n var a = document.createElement('a');\n var date = new Date().toISOString().slice(0,10).replace(/-/g,'');\n a.href=url; a.download='slowlog_'+(domainName||ds)+'_'+date+'.csv';\n document.body.appendChild(a); a.click();\n document.body.removeChild(a);\n URL.revokeObjectURL(url);\n}\n\n// ── 列宽拖拽 ──\nfunction makeResizable(tableId) {\n var table = document.getElementById(tableId);\n if (!table) return;\n var ths = table.querySelectorAll('thead th');\n ths.forEach(function(th) {\n th.style.position = 'relative';\n var handle = document.createElement('div');\n handle.style.cssText = 'position:absolute;right:0;top:0;width:5px;height:100%;cursor:col-resize;user-select:none;z-index:1';\n handle.addEventListener('mousedown', function(e) {\n e.preventDefault();\n var startX = e.pageX, startW = th.offsetWidth;\n function onMove(e) { th.style.width = Math.max(40, startW + e.pageX - startX) + 'px'; }\n function onUp() { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); }\n document.addEventListener('mousemove', onMove);\n document.addEventListener('mouseup', onUp);\n });\n th.appendChild(handle);\n });\n}\n\n// ── 初始化 ──\nfunction saInitAll() {\n var data = window.__saData || {};\n var keys = Object.keys(data);\n if (!keys.length) { setTimeout(saInitAll, 50); return; }\n keys.forEach(function(ds) {\n var wrap = document.getElementById('tbl_wrap_' + ds);\n if (wrap) { saQuery(ds); makeResizable('tbl_' + ds); }\n else { setTimeout(function(){ saQuery(ds); makeResizable('tbl_' + ds); }, 100); }\n });\n}\n\nif (document.readyState === 'loading') {\n document.addEventListener('DOMContentLoaded', saInitAll);\n} else {\n saInitAll();\n}\n"
HTML += """</script>\n"""
HTML += f"""
<div class="footer">mysql-perf-compare-report &nbsp;·&nbsp; 生成于 {now}</div>
</div>

<script>
CHARTJS_PLACEHOLDER"""
HTML += f"""
;(function(){{
  try {{
  var labels    = {js_strarr(short_labels)};
  var baseColor  = 'rgba(37,99,168,0.75)';
  var curColor   = 'rgba(231,76,60,0.80)';
  var baseBorder = 'rgba(37,99,168,1)';
  var curBorder  = 'rgba(231,76,60,1)';

  function makeBar(id, label1, data1, label2, data2, yLabel){{
    var el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {{
      type: 'bar',
      data: {{
        labels: labels,
        datasets: [
          {{label: label1, data: data1, backgroundColor: baseColor, borderColor: baseBorder, borderWidth:1.5, borderRadius:4}},
          {{label: label2, data: data2, backgroundColor: curColor,  borderColor: curBorder,  borderWidth:1.5, borderRadius:4}}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
          legend: {{position:'top', labels:{{font:{{size:12}}}}}},
          tooltip: {{callbacks: {{label: function(c) {{ return c.dataset.label + ': ' + c.parsed.y.toFixed(2) + (yLabel||''); }}}}}}
        }},
        scales: {{
          x: {{ticks:{{font:{{size:10}},maxRotation:30}}}},
          y: {{beginAtZero:true, ticks:{{font:{{size:11}}}}}}
        }}
      }}
    }});
  }}

  function makeSlowBar(id, data){{
    var el = document.getElementById(id);
    if (!el) return;
    var colors  = data.map(function(v){{ return v > 0 ? 'rgba(231,76,60,0.8)' : 'rgba(39,174,96,0.7)'; }});
    var borders = data.map(function(v){{ return v > 0 ? 'rgba(231,76,60,1)'   : 'rgba(39,174,96,1)'; }});
    new Chart(el, {{
      type: 'bar',
      data: {{
        labels: labels,
        datasets: [{{
          label: '\u65b0\u589e digest \u6570',
          data: data,
          backgroundColor: colors,
          borderColor: borders,
          borderWidth: 1.5,
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
          legend: {{display: false}},
          tooltip: {{callbacks: {{label: function(c) {{ return '\u65b0\u589e: ' + c.parsed.y + ' \u6761'; }}}}}}
        }},
        scales: {{
          x: {{ticks:{{font:{{size:10}},maxRotation:30}}}},
          y: {{beginAtZero:true, ticks:{{stepSize:1, font:{{size:11}}}}}}
        }}
      }}
    }});
  }}

  makeBar('chartCpuProxy',  '\u6628\u5929\u57fa\u51c6', {js_arr(cpu_proxy_base)},  '\u4eca\u5929\u672c\u6b21', {js_arr(cpu_proxy_cur)},  '%');
  makeBar('chartCpuMaster', '\u6628\u5929\u57fa\u51c6', {js_arr(cpu_master_base)}, '\u4eca\u5929\u672c\u6b21', {js_arr(cpu_master_cur)}, '%');
  makeBar('chartQps',       '\u6628\u5929\u57fa\u51c6', {js_arr(qps_master_base)}, '\u4eca\u5929\u672c\u6b21', {js_arr(qps_master_cur)}, '');
  makeSlowBar('chartSlowlog', {js_arr(new_counts)});
  }} catch(e) {{
    var errDiv = document.createElement('div');
    errDiv.style.cssText = 'color:red;padding:12px;font-size:13px;background:#fff0f0;border:1px solid #e74c3c;border-radius:4px;margin:8px';
    errDiv.textContent = '图表初始化错误: ' + e.message + ' (line:' + e.lineNumber + ')';
    var charts = document.getElementById('charts');
    if(charts) charts.prepend(errDiv);
    console.error('Charts error:', e);
  }}
}})();

"""
HTML += f"""
</script>

</body>
</html>"""


# ── 加载 Chart.js ────────────────────────────────────────────────────
# 优先查找本地 chart.umd.min.js（多个候选路径），最后尝试 CDN 兜底
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTJS_CANDIDATES = [
    os.path.join(_SCRIPT_DIR, "..", "node_modules", "chart.js", "dist", "chart.umd.min.js"),
    "/usr/local/lib/node_modules/chart.js/dist/chart.umd.min.js",
    "/app/node_modules/chart.js/dist/chart.umd.min.js",
]
CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"
chartjs_code = ""
for _candidate in CHARTJS_CANDIDATES:
    _norm = os.path.normpath(_candidate)
    try:
        chartjs_code = open(_norm, encoding="utf-8").read()
        if chartjs_code:
            print(f"[info] Chart.js 从本地加载 ({len(chartjs_code):,} bytes): {_norm}")
            break
    except Exception:
        pass
if not chartjs_code:
    try:
        import urllib.request

        with urllib.request.urlopen(CHARTJS_CDN, timeout=10) as resp:
            chartjs_code = resp.read().decode("utf-8")
        print(f"[info] Chart.js CDN 下载成功 ({len(chartjs_code):,} bytes)")
    except Exception:
        chartjs_code = "console.warn('Chart.js unavailable');"
        print("[warn] Chart.js 加载失败，图表功能不可用")

# ── 写文件 ──────────────────────────────────────────────────────────
import re as _re

CHARTJS_PLACEHOLDER = "CHARTJS_PLACEHOLDER"
OUT_PATH = OUTPUT
# CHARTJS_PLACEHOLDER 已在 <script>...</script> 标签内，只替换占位符本身
chartjs_safe = chartjs_code.replace("</script>", r"<\/script>").replace("</SCRIPT>", r"<\/SCRIPT>")
HTML_OUT = HTML.replace(CHARTJS_PLACEHOLDER, chartjs_safe, 1)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML_OUT)
print(f"HTML 报告已生成：{OUT_PATH} ({len(HTML_OUT):,} bytes)")
