#!/usr/bin/env python3
"""MySQL Processlist Analyzer

Analyze MySQL processlist data from a JSON file using various aggregation dimensions.
Output is always JSON, intended to be read and formatted by an LLM.

Usage:
    python analyze_processlist.py <input_json_file> [--type <aggregate_type>]

Aggregate types:
    diagnose             - Anomaly detection: only report problems found, silence means healthy
    summary              - Overview + top users/IPs/fingerprints/DBs + longest + lock_wait
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

MYSQL_FIELDS = {
    "id",
    "source_host",
    "command",
    "user",
    "db",
    "time",
    "state",
    "info",
    "tables",
    "fingerprint",
    "fingerprint_md5",
    "query_len",
}
PROXY_FIELDS = {"id", "source_host", "user", "destination_host", "state", "db", "time"}


def detect_source_type(df: pd.DataFrame) -> str:
    """Detect whether data comes from MySQL or Proxy based on available columns."""
    cols = set(df.columns)
    if "destination_host" in cols and "command" not in cols:
        return "proxy"
    return "mysql"


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


def _has(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def analyze(processlist: list, aggregate_type: str) -> dict:
    """Analyze processlist, return structured JSON result."""
    if not processlist:
        return {}

    df = pd.DataFrame(processlist)
    source_type = detect_source_type(df)

    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)

    results = {"source_type": source_type}

    total = len(df)

    # --- overview (summary / all) ---
    if aggregate_type in ("summary", "all"):
        overview = {"total": total}
        if _has(df, "command"):
            cmd_counts = df["command"].value_counts()
            overview["by_command"] = {
                cmd: {"count": int(cnt), "pct": round(cnt / total * 100, 1)} for cmd, cnt in cmd_counts.items()
            }
        if _has(df, "state"):
            state_counts = df["state"].value_counts()
            overview["by_state"] = {
                st: {"count": int(cnt), "pct": round(cnt / total * 100, 1)} for st, cnt in state_counts.items()
            }
        results["overview"] = overview

    # --- top N fingerprints (MySQL only) ---
    if aggregate_type in ("group_by_fingerprint", "summary", "all"):
        if _has(df, "fingerprint"):
            results["top_fingerprints"] = (
                df.groupby("fingerprint")
                .agg(count=("fingerprint", "size"), avg_time=("time", "mean"))
                .nlargest(TOP_N, "count")
                .reset_index()
                .to_dict(orient="records")
            )

    # --- state breakdown ---
    if aggregate_type in ("group_by_state", "all"):
        if _has(df, "state"):
            results["by_state"] = df["state"].value_counts().to_dict()

    # --- top N users ---
    if aggregate_type in ("group_by_user", "summary", "all"):
        if _has(df, "user"):
            user_counts = df["user"].value_counts().head(TOP_N)
            results["top_users"] = [
                {"user": user, "count": int(cnt), "pct": round(cnt / total * 100, 1)}
                for user, cnt in user_counts.items()
            ]

    # --- top N client IPs ---
    if aggregate_type in ("group_by_client_host", "summary", "all"):
        if _has(df, "source_host"):
            df["client_ip"] = df["source_host"].apply(extract_ip)
            ip_counts = df["client_ip"].value_counts().head(TOP_N)
            results["top_client_ips"] = [
                {"ip": ip, "count": int(cnt), "pct": round(cnt / total * 100, 1)} for ip, cnt in ip_counts.items()
            ]

    # --- top N destination hosts (Proxy only) ---
    if aggregate_type in ("group_by_destination_host", "summary", "all"):
        if _has(df, "destination_host"):
            dest_counts = df["destination_host"].value_counts().head(TOP_N)
            results["top_destination_hosts"] = [
                {"destination_host": host, "count": int(cnt), "pct": round(cnt / total * 100, 1)}
                for host, cnt in dest_counts.items()
            ]

    # --- longest top N (excluding sleep / system users) ---
    if aggregate_type in ("longest_top_5", "summary", "all"):
        if _has(df, "command"):
            filtered = df[
                (~df["command"].isin(IGNORED_COMMANDS)) & (df["time"] > 0) & (~df["user"].isin(SYSTEM_USERS))
            ]
        else:
            filtered = df[(df["time"] > 0) & (~df["user"].isin(SYSTEM_USERS))]
        desired_cols = [
            "id",
            "user",
            "db",
            "command",
            "fingerprint",
            "info",
            "time",
            "state",
            "source_host",
            "destination_host",
        ]
        avail_cols = [c for c in desired_cols if c in filtered.columns]
        top5 = filtered.nlargest(TOP_N, "time")[avail_cols].to_dict(orient="records")
        results["longest_queries"] = top5

    # --- top N databases ---
    if aggregate_type in ("group_by_db", "summary", "all"):
        if _has(df, "db"):
            db_col = df["db"].fillna("未指定").replace("", "未指定")
            db_counts = db_col.value_counts().head(TOP_N)
            results["top_dbs"] = [
                {"db": db, "count": int(cnt), "pct": round(cnt / total * 100, 1)} for db, cnt in db_counts.items()
            ]

    # --- lock wait detection ---
    if aggregate_type in ("lock_wait", "summary", "all"):
        if _has(df, "state"):
            pattern = "|".join(LOCK_WAIT_KEYWORDS)
            mask = df["state"].str.lower().str.contains(pattern, na=False)
            locked = df[mask]
            lock_cols = ["id", "user", "source_host", "db", "time", "state", "info", "destination_host"]
            avail_lock_cols = [c for c in lock_cols if c in locked.columns]
            results["lock_wait"] = {
                "count": int(len(locked)),
                "connections": locked[avail_lock_cols].to_dict(orient="records") if len(locked) > 0 else [],
            }

    return results


SAMPLE_LIMIT = 30
MYSQL_SAMPLE_FIELDS = ["id", "user", "source_host", "db", "command", "time", "state", "fingerprint", "info"]
PROXY_SAMPLE_FIELDS = ["id", "user", "source_host", "destination_host", "db", "time", "state"]


def sample_active(processlist: list) -> dict:
    """Return a sample of active connections for LLM free-form analysis."""
    if not processlist:
        return {"total": 0, "sampled": 0, "connections": []}

    df = pd.DataFrame(processlist)
    source_type = detect_source_type(df)

    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)

    filters = ~df["user"].isin(SYSTEM_USERS)
    if _has(df, "command"):
        filters = filters & (~df["command"].isin(IGNORED_COMMANDS))

    active = df[filters].copy()
    active = active.sort_values("time", ascending=False)

    candidate_fields = MYSQL_SAMPLE_FIELDS if source_type == "mysql" else PROXY_SAMPLE_FIELDS
    cols = [c for c in candidate_fields if c in active.columns]
    sampled = active.head(SAMPLE_LIMIT)[cols]

    return {
        "source_type": source_type,
        "total": len(df),
        "active_total": len(active),
        "sampled": len(sampled),
        "connections": sampled.to_dict(orient="records"),
    }


DIAG_SLOW_QUERY_SECONDS = 10
DIAG_IDLE_PCT_THRESHOLD = 90
DIAG_IDLE_COUNT_MIN = 100
DIAG_CONCENTRATION_PCT = 30
DIAG_CONCENTRATION_MIN_TOTAL = 10
DIAG_SUSPECT_TXN_SECONDS = 600
DIAG_AUTH_PRESSURE_MIN = 5
DIAG_ACTIVE_THREAD_SURGE = 100
DIAG_SQL_STAMPEDE_MIN = 20
DIAG_MDL_CASCADE_MIN = 3
PROXY_IDLE_STATES = {"CON_STATE_READ_QUERY"}
MYSQL_AUTH_STATES = {"login"}
MYSQL_AUTH_USERS = {"unauthenticated user"}
PROXY_AUTH_STATES = {"CON_STATE_READ_HANDSHAKE", "CON_STATE_READ_AUTH_RESULT"}
DIAG_LOCK_WAIT_KEYWORDS = LOCK_WAIT_KEYWORDS + [
    "waiting for row lock",
    "waiting for global read lock",
    "waiting for commit lock",
]
DIAG_CONCERNING_STATES = {
    "creating sort index": "可能缺少索引，导致文件排序",
    "copying to tmp table": "查询需要临时表，可能涉及大结果集",
    "copying to tmp table on disk": "临时表落盘，内存不足或结果集过大",
    "converting heap to myisam": "内存临时表转磁盘，tmp_table_size 可能需要调大",
    "sending data": None,
    "creating tmp table": "频繁创建临时表",
}
DIAG_MAX_EVIDENCE = 10
IDLE_TIME_BUCKETS = [
    (7 * 86400, ">7天"),
    (86400, "1~7天"),
    (3600, "1~24小时"),
    (600, "10分~1小时"),
    (60, "1~10分钟"),
    (0, "<1分钟"),
]
IDLE_USER_PATTERN_SHORT_THRESHOLD = 60
IDLE_USER_PATTERN_LONG_THRESHOLD = 3600


def _fmt_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds / 86400:.1f}天"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}小时"
    if seconds >= 60:
        return f"{seconds / 60:.1f}分钟"
    return f"{seconds}秒"


def _pick_cols(df: pd.DataFrame, desired: list) -> list:
    return [c for c in desired if c in df.columns]


def _rows_to_evidence(df: pd.DataFrame, limit: int = DIAG_MAX_EVIDENCE) -> dict:
    desired = [
        "id",
        "user",
        "source_host",
        "destination_host",
        "db",
        "command",
        "time",
        "state",
        "fingerprint",
        "info",
    ]
    cols = _pick_cols(df, desired)
    rows = df.head(limit)[cols].copy()
    if "time" in rows.columns:
        rows["time_human"] = rows["time"].apply(_fmt_duration)
        cols = list(rows.columns)
    return {"columns": cols, "rows": rows.values.tolist()}


def _time_bucket_distribution(series: pd.Series) -> list:
    """Bucket a time series into human-readable duration ranges."""
    result = []
    remaining = series.copy()
    for threshold, label in IDLE_TIME_BUCKETS:
        mask = remaining >= threshold
        cnt = int(mask.sum())
        if cnt > 0:
            result.append({"range": label, "count": cnt})
            remaining = remaining[~mask]
    return result


def _top_n_grouped(df: pd.DataFrame, col: str, n: int = TOP_N) -> dict:
    """Group by column and return top N with count and percentage."""
    total = len(df)
    if total == 0 or col not in df.columns:
        return {"columns": [], "rows": []}
    counts = df[col].value_counts().head(n)
    return {
        "columns": [col, "count", "pct"],
        "rows": [[str(val), int(cnt), round(cnt / total * 100, 1)] for val, cnt in counts.items()],
    }


def _classify_idle_pattern(times: pd.Series) -> str:
    """Classify a user's idle time distribution as normal/leak/bimodal."""
    if len(times) < 3:
        return "normal"
    short = int((times < IDLE_USER_PATTERN_SHORT_THRESHOLD).sum())
    long_ = int((times > IDLE_USER_PATTERN_LONG_THRESHOLD).sum())
    total = len(times)
    short_pct = short / total
    long_pct = long_ / total
    if short_pct > 0.2 and long_pct > 0.2:
        return "bimodal"
    if long_pct > 0.5:
        return "leak"
    return "normal"


def _user_idle_profiles(idle_df: pd.DataFrame, n: int = 10) -> dict:
    """Per-user idle time profile with pattern classification."""
    if len(idle_df) == 0 or "user" not in idle_df.columns:
        return {"columns": [], "rows": []}
    total = len(idle_df)
    top_users = idle_df["user"].value_counts().head(n).index
    cols = ["user", "count", "pct", "time_p50_human", "time_p90_human", "pattern"]
    rows = []
    for user in top_users:
        user_times = idle_df.loc[idle_df["user"] == user, "time"]
        cnt = len(user_times)
        rows.append(
            [
                user,
                cnt,
                round(cnt / total * 100, 1),
                _fmt_duration(int(user_times.median())),
                _fmt_duration(int(user_times.quantile(0.9))),
                _classify_idle_pattern(user_times),
            ]
        )
    return {"columns": cols, "rows": rows}


def _ip_idle_profiles(idle_df: pd.DataFrame, n: int = 10) -> list:
    """Per-source-IP idle profile with median idle time."""
    if len(idle_df) == 0 or "source_host" not in idle_df.columns:
        return []
    total = len(idle_df)
    ip_df = idle_df.copy()
    ip_df["client_ip"] = ip_df["source_host"].apply(extract_ip)
    top_ips = ip_df["client_ip"].value_counts().head(n).index
    all_medians = []
    profiles = []
    for ip in top_ips:
        ip_times = ip_df.loc[ip_df["client_ip"] == ip, "time"]
        cnt = len(ip_times)
        median = int(ip_times.median())
        all_medians.append(median)
        profiles.append(
            {
                "ip": ip,
                "count": cnt,
                "pct": round(cnt / total * 100, 1),
                "idle_p50": median,
                "idle_p50_human": _fmt_duration(median),
            }
        )
    if len(all_medians) >= 2:
        global_median = sorted(all_medians)[len(all_medians) // 2]
        for p in profiles:
            p["suspect_leak"] = p["idle_p50"] > max(global_median * 3, 3600)
    return profiles


def _build_actions(finding_type: str, source_type: str, **ctx) -> list:
    """Generate actionable SQL/commands for each finding type."""
    actions = []
    if source_type == "proxy":
        return actions

    if finding_type == "suspect_uncommitted_txn":
        actions.append("-- 查看真正持有未提交事务的连接（比 processlist 更准确）")
        actions.append(
            "SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id, trx_rows_locked, trx_rows_modified FROM information_schema.innodb_trx ORDER BY trx_started;"
        )
        top_user = ctx.get("top_user", "")
        if top_user:
            actions.append(f"-- 筛查用户 {top_user} 的长 Sleep 连接")
            actions.append(
                f"SELECT id, user, host, db, time, state FROM information_schema.processlist WHERE command='Sleep' AND time>{DIAG_SUSPECT_TXN_SECONDS} AND user='{top_user}' ORDER BY time DESC;"
            )
        actions.append(f"-- 批量生成 KILL 语句（Sleep 超过 {DIAG_SUSPECT_TXN_SECONDS}秒 且无活跃事务的连接可安全清理）")
        actions.append(
            f"SELECT CONCAT('KILL ', id, ';') FROM information_schema.processlist WHERE command='Sleep' AND time>{DIAG_SUSPECT_TXN_SECONDS} AND id NOT IN (SELECT trx_mysql_thread_id FROM information_schema.innodb_trx);"
        )

    elif finding_type == "killed_threads":
        actions.append("-- 查看被 Kill 线程的回滚进度")
        actions.append("SHOW ENGINE INNODB STATUS;  -- 搜索 TRANSACTIONS 段，关注 undo log entries 数量变化")
        actions.append("-- 查看当前 Killed 线程")
        actions.append(
            "SELECT id, user, host, db, time, state, LEFT(info, 200) AS query FROM information_schema.processlist WHERE command='Killed';"
        )

    elif finding_type == "mdl_lock_cascade":
        actions.append("-- 查找 MDL 锁的持有者和等待者（需 MySQL 5.7+ 且开启 performance_schema）")
        actions.append("SELECT * FROM sys.schema_table_lock_waits\\G")
        actions.append("-- 如果 sys 库不可用，手动查找阻塞源：找到比最早 MDL 等待更老的事务")
        actions.append(
            "SELECT trx_mysql_thread_id, trx_started, trx_state, trx_query FROM information_schema.innodb_trx WHERE trx_started < (SELECT MIN(trx_started) FROM information_schema.innodb_trx WHERE trx_mysql_thread_id IN (SELECT id FROM information_schema.processlist WHERE state='Waiting for table metadata lock'));"
        )

    elif finding_type == "lock_wait":
        actions.append("-- 查看行锁等待详情")
        actions.append("SELECT * FROM information_schema.innodb_lock_waits;  -- MySQL 5.x")
        actions.append("SELECT * FROM performance_schema.data_lock_waits;  -- MySQL 8.0+")
        actions.append("-- 查看持锁事务")
        actions.append(
            "SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id, trx_rows_locked, trx_query FROM information_schema.innodb_trx;"
        )

    elif finding_type == "active_thread_surge":
        actions.append("-- 查看当前所有活跃查询（按执行时间排序）")
        actions.append(
            "SELECT id, user, host, db, time, state, LEFT(info, 200) AS query FROM information_schema.processlist WHERE command='Query' AND info IS NOT NULL ORDER BY time DESC;"
        )
        actions.append("-- 按 state 统计活跃线程分布")
        actions.append(
            "SELECT state, COUNT(*) AS cnt FROM information_schema.processlist WHERE command='Query' GROUP BY state ORDER BY cnt DESC;"
        )

    elif finding_type == "sql_stampede":
        top_sql = ctx.get("top_sql", "")
        if top_sql:
            actions.append("-- 查看最大并发的那条 SQL 的所有执行实例")
            safe_sql = top_sql[:80].replace("'", "\\'")
            actions.append(
                f"SELECT id, user, host, db, time, state FROM information_schema.processlist WHERE info LIKE '{safe_sql}%' ORDER BY time DESC;"
            )
        actions.append("-- 按 SQL 文本聚合活跃查询，找出并发最高的")
        actions.append(
            "SELECT LEFT(info, 200) AS sql_text, COUNT(*) AS cnt, MAX(time) AS max_sec FROM information_schema.processlist WHERE command='Query' AND info IS NOT NULL GROUP BY sql_text HAVING cnt>=5 ORDER BY cnt DESC LIMIT 20;"
        )

    elif finding_type == "auth_pressure":
        actions.append("-- 查看当前鉴权中的连接")
        actions.append(
            "SELECT id, user, host, time, state FROM information_schema.processlist WHERE command='Connect' OR user='unauthenticated user' ORDER BY time DESC;"
        )
        actions.append("-- 查看鉴权失败累计次数")
        actions.append("SHOW GLOBAL STATUS LIKE 'Aborted_connects';")

    elif finding_type == "slow_queries":
        actions.append("-- 查看当前正在执行的慢查询")
        actions.append(
            f"SELECT id, user, host, db, time, state, LEFT(info, 300) AS query FROM information_schema.processlist WHERE command='Query' AND time>{DIAG_SLOW_QUERY_SECONDS} ORDER BY time DESC;"
        )
        actions.append("-- 对最慢的查询生成 KILL QUERY 语句（仅终止查询，保留连接）")
        actions.append(
            f"SELECT CONCAT('KILL QUERY ', id, ';') FROM information_schema.processlist WHERE command='Query' AND time>{DIAG_SLOW_QUERY_SECONDS} ORDER BY time DESC LIMIT 10;"
        )

    elif finding_type == "idle_bloat":
        leak_users = ctx.get("leak_users", [])
        if leak_users:
            user_list = ", ".join(f"'{u}'" for u in leak_users[:3])
            actions.append(f"-- 查看泄漏模式用户的 Sleep 连接分布")
            actions.append(
                f"SELECT user, COUNT(*) AS cnt, MAX(time) AS max_sleep, MIN(time) AS min_sleep, ROUND(AVG(time)) AS avg_sleep FROM information_schema.processlist WHERE command='Sleep' AND user IN ({user_list}) GROUP BY user;"
            )
            actions.append(f"-- 清理泄漏用户超过 1 小时的 Sleep 连接")
            actions.append(
                f"SELECT CONCAT('KILL ', id, ';') FROM information_schema.processlist WHERE command='Sleep' AND time>3600 AND user IN ({user_list}) ORDER BY time DESC;"
            )
        actions.append("-- 按用户统计 Sleep 连接")
        actions.append(
            "SELECT user, COUNT(*) AS cnt, MAX(time) AS max_sleep FROM information_schema.processlist WHERE command='Sleep' GROUP BY user ORDER BY cnt DESC LIMIT 20;"
        )
        actions.append("-- 查看 wait_timeout 配置（决定空闲连接自动断开时间）")
        actions.append("SHOW GLOBAL VARIABLES LIKE 'wait_timeout';")

    return actions


def diagnose(processlist: list) -> dict:
    """Anomaly-focused analysis with drill-down data for root cause locating."""
    if not processlist:
        return {"source_type": "unknown", "total": 0, "findings": []}

    df = pd.DataFrame(processlist)
    source_type = detect_source_type(df)

    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").fillna(0).astype(int)

    total = len(df)
    findings = []

    user_filter = ~df["user"].isin(SYSTEM_USERS)
    user_df = df[user_filter]
    user_total = len(user_df)

    # --- Build idle / active masks ---
    if _has(df, "command"):
        idle_mask = user_filter & (df["command"] == "Sleep")
    elif source_type == "proxy" and _has(df, "state"):
        idle_mask = user_filter & df["state"].isin(PROXY_IDLE_STATES)
    else:
        idle_mask = pd.Series(False, index=df.index)

    active_filter = user_filter & (~idle_mask[user_filter].reindex(df.index, fill_value=False))
    if _has(df, "command"):
        active_filter = active_filter & (~df["command"].isin(IGNORED_COMMANDS))
    if source_type == "proxy" and _has(df, "state"):
        active_filter = active_filter & (~df["state"].isin(PROXY_IDLE_STATES))

    idle_df = df[idle_mask]
    idle_count = len(idle_df)

    # ================================================================
    # 1. Suspect uncommitted transactions (Sleep with long idle time)
    # ================================================================
    if _has(df, "command"):
        suspect_txn_mask = idle_mask & (df["time"] > DIAG_SUSPECT_TXN_SECONDS)
        suspect_txn = df[suspect_txn_mask].sort_values("time", ascending=False)
        if len(suspect_txn) > 0:
            by_user = _top_n_grouped(suspect_txn, "user", n=10)
            findings.append(
                {
                    "severity": "high",
                    "type": "suspect_uncommitted_txn",
                    "title": f"发现 {len(suspect_txn)} 个长时间 Sleep 连接（>{_fmt_duration(DIAG_SUSPECT_TXN_SECONDS)}），可能存在未提交事务",
                    "detail": "Sleep 超过 10 分钟的连接可能持有未提交事务，阻塞 DDL 或导致 undo log 膨胀",
                    "by_user": by_user,
                    "time_distribution": _time_bucket_distribution(suspect_txn["time"]),
                    "evidence": _rows_to_evidence(suspect_txn),
                }
            )

    # ================================================================
    # 2. Killed threads (stuck in rollback or cleanup)
    # ================================================================
    if _has(df, "command"):
        killed_mask = df["command"] == "Killed"
        killed_count = int(killed_mask.sum())
        if killed_count > 0:
            killed_df = df[killed_mask].sort_values("time", ascending=False)
            findings.append(
                {
                    "severity": "high",
                    "type": "killed_threads",
                    "title": f"发现 {killed_count} 个被 Kill 但未退出的线程",
                    "detail": "线程被标记终止但仍在运行（通常在回滚大事务），期间仍持有锁，可能阻塞其他操作。切勿重启 MySQL 强制中断，否则 InnoDB 恢复时回滚更慢",
                    "evidence": _rows_to_evidence(killed_df),
                }
            )

    # ================================================================
    # 3. Lock waits (split MDL cascade from generic lock waits)
    # ================================================================
    if _has(df, "state"):
        state_lower = df["state"].str.lower()

        mdl_mask = state_lower.str.contains("waiting for table metadata lock", na=False)
        mdl_df = df[mdl_mask].sort_values("time", ascending=False)
        mdl_count = len(mdl_df)

        other_lock_pattern = "|".join(kw for kw in DIAG_LOCK_WAIT_KEYWORDS if "metadata" not in kw)
        other_lock_mask = (
            state_lower.str.contains(other_lock_pattern, na=False)
            if other_lock_pattern
            else pd.Series(False, index=df.index)
        )
        other_locked = df[other_lock_mask].sort_values("time", ascending=False)

        if mdl_count >= DIAG_MDL_CASCADE_MIN:
            tables_affected = set()
            if _has(mdl_df, "info"):
                for sql_text in mdl_df["info"].dropna():
                    tables_affected.add(sql_text[:100])
            findings.append(
                {
                    "severity": "high",
                    "type": "mdl_lock_cascade",
                    "title": f"发现 {mdl_count} 个连接在等待 Metadata Lock，可能形成连锁阻塞",
                    "detail": "典型原因：存在未提交事务持有 MDL 读锁，阻塞了 DDL 操作（如 ALTER TABLE），而 DDL 又阻塞了后续所有该表的读写操作，导致连接堆积。需找到持锁的 Sleep 事务并 Kill",
                    "evidence": _rows_to_evidence(mdl_df),
                }
            )
        elif mdl_count > 0:
            findings.append(
                {
                    "severity": "high",
                    "type": "lock_wait",
                    "title": f"发现 {mdl_count} 个连接在等待 Metadata Lock",
                    "evidence": _rows_to_evidence(mdl_df),
                }
            )

        if len(other_locked) > 0:
            findings.append(
                {
                    "severity": "high",
                    "type": "lock_wait",
                    "title": f"发现 {len(other_locked)} 个连接在等待行锁/表锁",
                    "evidence": _rows_to_evidence(other_locked),
                }
            )

    # ================================================================
    # 5. Active thread surge (too many threads actively running)
    # ================================================================
    active_df_all = df[active_filter]
    active_count_total = len(active_df_all)
    if active_count_total > DIAG_ACTIVE_THREAD_SURGE:
        detail_parts = [f"当前 {active_count_total} 个线程在执行操作"]
        if _has(active_df_all, "state"):
            top_states = active_df_all["state"].value_counts().head(5)
            state_desc = "、".join(f"{s}({int(c)})" for s, c in top_states.items() if s)
            if state_desc:
                detail_parts.append(f"Top 状态：{state_desc}")
        findings.append(
            {
                "severity": "high",
                "type": "active_thread_surge",
                "title": f"活跃线程数过高（{active_count_total}），DB 处于高压状态",
                "detail": "；".join(detail_parts),
                "evidence": _rows_to_evidence(active_df_all.sort_values("time", ascending=False)),
            }
        )

    # ================================================================
    # 6. SQL stampede (many connections running the exact same SQL)
    # ================================================================
    if _has(df, "info") and _has(df, "command"):
        running_mask = active_filter & df["info"].notna() & (df["info"] != "")
        running_df = df[running_mask]
        if len(running_df) > 0:
            sql_counts = running_df["info"].value_counts()
            stampede_sqls = sql_counts[sql_counts >= DIAG_SQL_STAMPEDE_MIN]
            if len(stampede_sqls) > 0:
                entries = []
                for sql_text, cnt in stampede_sqls.items():
                    matching = running_df[running_df["info"] == sql_text]
                    entries.append(
                        {
                            "sql": sql_text[:300],
                            "concurrent": int(cnt),
                            "max_time": int(matching["time"].max()),
                            "max_time_human": _fmt_duration(int(matching["time"].max())),
                            "users": list(matching["user"].unique()[:5]),
                        }
                    )
                entries.sort(key=lambda e: e["concurrent"], reverse=True)
                total_stampede = sum(e["concurrent"] for e in entries)
                findings.append(
                    {
                        "severity": "high",
                        "type": "sql_stampede",
                        "title": f"发现 {len(entries)} 条 SQL 各有 ≥{DIAG_SQL_STAMPEDE_MIN} 个并发执行（共 {total_stampede} 个），并发可能失控",
                        "detail": "大量相同 SQL 并发执行通常意味着：缓存失效导致击穿、缺少并发控制（锁/去重）、或客户端重试风暴",
                        "stampede_sqls": entries[:10],
                    }
                )

    # ================================================================
    # 7. Authentication pressure
    # ================================================================
    if source_type == "mysql":
        auth_mask = df["user"].isin(MYSQL_AUTH_USERS) | (
            df["state"].str.lower().isin(MYSQL_AUTH_STATES) if _has(df, "state") else False
        )
    else:
        auth_mask = df["state"].isin(PROXY_AUTH_STATES) if _has(df, "state") else pd.Series(False, index=df.index)
    auth_count = int(auth_mask.sum())
    has_slow = len(findings) > 0 and any(f["type"] in ("slow_queries", "stale_connections") for f in findings)
    if auth_count >= DIAG_AUTH_PRESSURE_MIN:
        if has_slow:
            detail = f"同时存在慢查询/滞留连接，DB 可能过于繁忙导致鉴权排队"
        else:
            detail = f"无明显慢查询，大量鉴权连接说明可能存在频繁短连接（未使用连接池）"
        findings.append(
            {
                "severity": "medium",
                "type": "auth_pressure",
                "title": f"发现 {auth_count} 个连接处于鉴权状态",
                "detail": detail,
                "evidence": _rows_to_evidence(df[auth_mask].sort_values("time", ascending=False)),
            }
        )

    # ================================================================
    # 8. Active connections with abnormal duration
    # ================================================================
    active_long_filter = active_filter & (df["time"] > DIAG_SLOW_QUERY_SECONDS)
    active_long = df[active_long_filter].sort_values("time", ascending=False)
    if len(active_long) > 0:
        max_time = int(active_long["time"].max())
        if source_type == "proxy":
            findings.append(
                {
                    "severity": "high" if max_time > 3600 else "medium",
                    "type": "stale_connections",
                    "title": f"发现 {len(active_long)} 个滞留连接（非空闲状态持续超过 {DIAG_SLOW_QUERY_SECONDS}秒）",
                    "detail": f"最长已持续 {_fmt_duration(max_time)}，客户端可能已断开但连接未释放",
                    "by_user": _top_n_grouped(active_long, "user", n=5),
                    "evidence": _rows_to_evidence(active_long),
                }
            )
        else:
            detail_parts = [f"最长 {_fmt_duration(max_time)}"]
            if _has(active_long, "fingerprint"):
                fp_dist = _top_n_grouped(active_long, "fingerprint", n=5)
                if fp_dist and fp_dist[0]["value"]:
                    detail_parts.append(f"Top SQL 指纹：{fp_dist[0]['value'][:80]}（{fp_dist[0]['count']}次）")
            findings.append(
                {
                    "severity": "high" if max_time > 3600 else "medium",
                    "type": "slow_queries",
                    "title": f"发现 {len(active_long)} 个慢查询（执行超过 {DIAG_SLOW_QUERY_SECONDS}秒）",
                    "detail": "；".join(detail_parts),
                    "evidence": _rows_to_evidence(active_long),
                }
            )

    # ================================================================
    # 9. Idle connection bloat with drill-down
    # ================================================================
    if user_total > 0 and idle_count > 0:
        idle_pct = round(idle_count / user_total * 100, 1)
        if idle_pct > DIAG_IDLE_PCT_THRESHOLD and idle_count > DIAG_IDLE_COUNT_MIN:
            user_profiles = _user_idle_profiles(idle_df, n=10)
            drill_down = {
                "time_distribution": _time_bucket_distribution(idle_df["time"]),
                "by_user": user_profiles,
            }
            prof_cols = user_profiles.get("columns", [])
            prof_rows = user_profiles.get("rows", [])
            _ci = {c: i for i, c in enumerate(prof_cols)}
            bimodal_names = [
                r[_ci["user"]] for r in prof_rows if _ci.get("pattern") is not None and r[_ci["pattern"]] == "bimodal"
            ]
            leak_names = [
                r[_ci["user"]] for r in prof_rows if _ci.get("pattern") is not None and r[_ci["pattern"]] == "leak"
            ]
            if bimodal_names or leak_names:
                hints = []
                if bimodal_names:
                    names = ", ".join(bimodal_names[:3])
                    hints.append(f"用户 {names} 同时存在大量短 Sleep 和长 Sleep 连接（双峰），连接池可能在不断创建新连接但旧连接未回收")
                if leak_names:
                    names = ", ".join(leak_names[:3])
                    hints.append(f"用户 {names} 的连接大部分长期 Sleep（泄漏模式），可能存在连接泄漏")
                drill_down["pattern_analysis"] = "；".join(hints)

            if _has(idle_df, "source_host"):
                if source_type == "proxy":
                    drill_down["by_source_ip"] = _ip_idle_profiles(idle_df, n=10)
                else:
                    ip_df = idle_df.copy()
                    ip_df["client_ip"] = ip_df["source_host"].apply(extract_ip)
                    drill_down["by_source_ip"] = _top_n_grouped(ip_df, "client_ip", n=10)
            if _has(idle_df, "db"):
                drill_down["by_db"] = _top_n_grouped(idle_df, "db", n=10)

            findings.append(
                {
                    "severity": "medium",
                    "type": "idle_bloat",
                    "title": f"空闲连接占比过高：{idle_count}/{user_total}（{idle_pct}%）",
                    **drill_down,
                }
            )

    # ================================================================
    # 10. Proxy source IP concentration
    # ================================================================
    if source_type == "proxy" and _has(df, "source_host") and user_total >= DIAG_CONCENTRATION_MIN_TOTAL:
        ip_all = user_df.copy()
        ip_all["client_ip"] = ip_all["source_host"].apply(extract_ip)
        top_ips = ip_all["client_ip"].value_counts().head(10)
        top_ip_name, top_ip_count = top_ips.index[0], int(top_ips.iloc[0])
        top_ip_pct = round(top_ip_count / user_total * 100, 1)
        if top_ip_pct > DIAG_CONCENTRATION_PCT:
            findings.append(
                {
                    "severity": "medium",
                    "type": "proxy_source_concentration",
                    "title": f"来源 IP {top_ip_name} 占据 {top_ip_pct}% 连接（{top_ip_count}/{user_total}）",
                    "by_source_ip": [
                        {"ip": str(ip), "count": int(cnt), "pct": round(cnt / user_total * 100, 1)}
                        for ip, cnt in top_ips.items()
                    ],
                }
            )

    # ================================================================
    # 11. Concerning states
    # ================================================================
    if _has(df, "state"):
        state_lower = df["state"].str.lower()
        for state_key, hint in DIAG_CONCERNING_STATES.items():
            mask = state_lower == state_key
            cnt = int(mask.sum())
            if cnt >= 3:
                entry = {
                    "severity": "medium",
                    "type": "concerning_state",
                    "title": f'有 {cnt} 个连接处于 "{state_key}" 状态',
                }
                if hint:
                    entry["detail"] = hint
                entry["evidence"] = _rows_to_evidence(df[mask].sort_values("time", ascending=False))
                findings.append(entry)

    # ================================================================
    # 12. Proxy backend skew
    # ================================================================
    if _has(df, "destination_host") and source_type == "proxy":
        dest_counts = df["destination_host"].value_counts()
        if len(dest_counts) > 1:
            max_pct = round(dest_counts.iloc[0] / total * 100, 1)
            min_pct = round(dest_counts.iloc[-1] / total * 100, 1)
            if max_pct - min_pct > 20:
                findings.append(
                    {
                        "severity": "medium",
                        "type": "backend_skew",
                        "title": "后端实例连接分布不均",
                        "detail": f"最高 {dest_counts.index[0]}={max_pct}%，最低 {dest_counts.index[-1]}={min_pct}%",
                        "distribution": [
                            {"host": h, "count": int(c), "pct": round(c / total * 100, 1)}
                            for h, c in dest_counts.items()
                        ],
                    }
                )

    # ================================================================
    # 13. High fingerprint concentration (MySQL only, among active)
    # ================================================================
    if _has(df, "fingerprint") and _has(df, "command"):
        active_df = df[active_filter]
        active_total = len(active_df)
        if active_total > 5:
            fp_counts = active_df["fingerprint"].value_counts()
            top_fp = fp_counts.head(1)
            if len(top_fp) > 0:
                fp_text, fp_count = top_fp.index[0], int(top_fp.iloc[0])
                fp_pct = round(fp_count / active_total * 100, 1)
                if fp_pct > DIAG_CONCENTRATION_PCT and fp_text:
                    findings.append(
                        {
                            "severity": "medium",
                            "type": "fingerprint_concentration",
                            "title": f"单条 SQL 指纹占活跃连接的 {fp_pct}%（{fp_count}/{active_total}）",
                            "fingerprint": fp_text[:200],
                            "evidence": _rows_to_evidence(
                                active_df[active_df["fingerprint"] == fp_text].sort_values("time", ascending=False)
                            ),
                        }
                    )

    # ================================================================
    # 14. User concentration (MySQL: among all; skip for Proxy, handled above)
    # ================================================================
    if source_type != "proxy" and _has(df, "user") and user_total >= DIAG_CONCENTRATION_MIN_TOTAL:
        top_user = user_df["user"].value_counts().head(1)
        if len(top_user) > 0:
            u_name, u_count = top_user.index[0], int(top_user.iloc[0])
            u_pct = round(u_count / user_total * 100, 1)
            if u_pct > DIAG_CONCENTRATION_PCT:
                findings.append(
                    {
                        "severity": "medium",
                        "type": "user_concentration",
                        "title": f"用户 {u_name} 占据 {u_pct}% 连接（{u_count}/{user_total}）",
                        "detail": "单用户连接占比过高，检查该应用是否存在连接泄漏",
                    }
                )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 99))

    for f in findings:
        ctx = {}
        if f["type"] == "suspect_uncommitted_txn" and f.get("by_user"):
            bu = f["by_user"]
            if isinstance(bu, dict) and bu.get("rows"):
                ctx["top_user"] = bu["rows"][0][0]
        elif f["type"] == "sql_stampede" and f.get("stampede_sqls"):
            ctx["top_sql"] = f["stampede_sqls"][0]["sql"]
        elif f["type"] == "idle_bloat" and f.get("by_user"):
            bu = f["by_user"]
            if isinstance(bu, dict) and bu.get("columns"):
                _ci = {c: i for i, c in enumerate(bu["columns"])}
                ctx["leak_users"] = [
                    r[_ci["user"]]
                    for r in bu.get("rows", [])
                    if _ci.get("pattern") is not None and r[_ci["pattern"]] == "leak"
                ]
        actions = _build_actions(f["type"], source_type, **ctx)
        if actions:
            f["actions"] = actions

    active_count = int(active_filter.sum())

    return {
        "source_type": source_type,
        "total": total,
        "active": active_count,
        "idle": idle_count,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="MySQL Processlist Analyzer")
    parser.add_argument("input_file", help="Path to JSON file containing processlist data")
    parser.add_argument(
        "--type",
        dest="aggregate_type",
        default="diagnose",
        choices=[
            "diagnose",
            "summary",
            "all",
            "group_by_fingerprint",
            "group_by_state",
            "group_by_user",
            "group_by_client_host",
            "group_by_db",
            "group_by_destination_host",
            "lock_wait",
            "longest_top_5",
            "sample",
        ],
        help="Aggregation type (default: diagnose)",
    )
    args = parser.parse_args()

    processlist = load_processlist(args.input_file)
    if args.aggregate_type == "diagnose":
        results = diagnose(processlist)
    elif args.aggregate_type == "sample":
        results = sample_active(processlist)
    else:
        results = analyze(processlist, args.aggregate_type)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
