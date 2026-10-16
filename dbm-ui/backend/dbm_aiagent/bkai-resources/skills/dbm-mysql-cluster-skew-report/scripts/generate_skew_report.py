#!/usr/bin/env python3
"""generate_skew_report.py

Parse MCP skew response, analyze, generate an HTML report with Chart.js,
upload via MCP, and print a short summary + report_id to stdout.

Usage:
    python3 generate_skew_report.py <raw_json_file> \
        --bk-biz-id <id> --cluster-domain <domain> \
        --raw-query "<query>" --out-dir <dir>

Stdout (for LLM consumption):
    SUMMARY: <≤200 chars>
    REPORT_ID: <id>
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# ── Constants ────────────────────────────────────────────────────────────────

SEGMENT_GAP_MINUTES = 30

METRIC_NAMES = {
    "connections": "连接数",
    "cpu_summary": "CPU",
    "qps_summary": "QPS",
    "memory_usage": "内存使用率",
    "disk_used": "磁盘使用量",
}

ROLE_NAMES = {
    "spider_master": "Spider接入层(master)",
    "spider_slave": "Spider接入层(slave)",
    "proxy_master": "Proxy接入层",
    "remote_master": "远程存储层(master)",
    "remote_slave": "远程存储层(slave)",
    "backend_master": "后端存储层(master)",
    "backend_slave": "后端存储层(slave)",
}

ROLE_TIERS = {"spider": "接入层", "proxy": "接入层", "remote": "存储层", "backend": "存储层"}

ATTRIBUTION = {
    ("connections", "接入层"): {
        "cause": "接入层连接数倾斜，常见原因为 DNS 缓存导致连接集中或业务直连 IP",
        "tips": ["换用 CLB 替代 DNS 接入", "避免短时间集中新建大量连接", "排查业务是否直连 IP"],
    },
    ("qps_summary", "接入层"): {
        "cause": "接入层 QPS 倾斜，长连接下各连接业务逻辑差异或短连接下模块请求量差异导致",
        "tips": ["分析连接模式（长/短连接）", "检查是否伴随连接数倾斜", "考虑请求级负载均衡"],
    },
    ("cpu_summary", "接入层"): {
        "cause": "接入层 CPU 倾斜，通常由 QPS 不均引发",
        "tips": ["优先排查 QPS 倾斜", "检查是否有复杂查询集中在特定节点"],
    },
    ("memory_usage", None): {
        "cause": "内存使用率倾斜，需先排除机器配置差异",
        "tips": ["对比同角色节点机器规格", "配置一致则排查异常内存消耗", "配置不一致属正常表现"],
    },
    ("disk_used", "接入层"): {
        "cause": "接入层磁盘倾斜，通常是临时文件（大查询排序文件、未清理日志等）",
        "tips": ["检查临时排序文件", "检查日志 rotate"],
    },
    ("disk_used", "存储层"): {
        "cause": "存储层磁盘倾斜，可能分片不合理、机器配置不一致或备份未清理",
        "tips": ["检查分片键", "对比机器规格", "检查备份清理任务"],
    },
    (None, "存储层"): {
        "cause": "存储层倾斜，几乎都是数据分片不合理导致",
        "tips": ["检查分片键选择", "排查热点 shard", "必要时重新规划分片策略"],
    },
}

# ── Data Parsing ─────────────────────────────────────────────────────────────


def load_raw(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def extract_data(raw):
    if "response_body" in raw:
        body = raw["response_body"]
        if body.get("code", -1) != 0:
            print(f"ERROR: MCP error: {body.get('message')}", file=sys.stderr)
            sys.exit(1)
        return body.get("data", {})
    if "code" in raw:
        if raw["code"] != 0:
            print(f"ERROR: MCP error: {raw.get('message')}", file=sys.stderr)
            sys.exit(1)
        return raw.get("data", {})
    return raw


_NODE_RE = re.compile(r"([\d.]+):(\d+)\s+value=([\d.]+)\s+mean=([\d.]+)\s+pct=([+-][\d.]+)%\s+abs_dev=([\d.]+)")


def parse_nodes(s):
    if not s:
        return []
    out = []
    for m in _NODE_RE.finditer(s):
        ip, port, val, mean, pct, ad = m.groups()
        port = int(port)
        out.append(
            {
                "display": ip if port == 0 else f"{ip}:{port}",
                "ip": ip,
                "port": port,
                "value": float(val),
                "mean": float(mean),
                "pct": float(pct),
                "abs_dev": float(ad),
            }
        )
    return out


def _parse_tz_offset(s):
    """Parse timezone offset string like '+08:00' or '-05:00' into timedelta."""
    m = re.match(r"^([+-])(\d{2}):(\d{2})$", s)
    if not m:
        return timedelta(0)
    sign = 1 if m.group(1) == "+" else -1
    return timedelta(hours=int(m.group(2)) * sign, minutes=int(m.group(3)) * sign)


def _parse_dt(s, tz_offset=None):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if tz_offset:
                dt += tz_offset
            return dt
        except ValueError:
            pass
    return None


def parse_episodes(data, tz_offset=None):
    ep_raw = data.get("episodes", {})
    cols = {n: i for i, n in enumerate(ep_raw.get("columns", []))}
    out = []
    for row in ep_raw.get("rows", []):
        hot = parse_nodes(row[cols.get("hot_nodes", 6)])
        cold = parse_nodes(row[cols.get("cold_nodes", 7)])
        hp = [n["pct"] for n in hot]
        cp = [abs(n["pct"]) for n in cold]
        transitions = row[cols.get("transitions", 8)] if len(row) > cols.get("transitions", 8) else None
        out.append(
            {
                "metric": row[cols.get("metric", 0)],
                "role": row[cols.get("role", 1)],
                "pattern": row[cols.get("pattern", 2)],
                "start": row[cols.get("start", 3)],
                "end": row[cols.get("end", 4)],
                "group_mean": row[cols.get("group_mean", 5)],
                "hot_nodes": hot,
                "cold_nodes": cold,
                "transitions": transitions,
                "transition_count": len(transitions) if isinstance(transitions, list) else 0,
                "start_dt": _parse_dt(row[cols.get("start", 3)], tz_offset),
                "end_dt": _parse_dt(row[cols.get("end", 4)], tz_offset),
                "max_hot_pct": max(hp) if hp else 0,
                "max_cold_pct": max(cp) if cp else 0,
            }
        )
    return out


# ── Analysis ─────────────────────────────────────────────────────────────────


def _tier(role):
    return ROLE_TIERS.get(role.split("_")[0], "未知")


def merge_segments(episodes):
    if not episodes:
        return []
    eps = sorted(episodes, key=lambda e: e["start"])
    segs = []
    cur = {
        "start": eps[0]["start"],
        "end": eps[0]["end"],
        "sdt": eps[0]["start_dt"],
        "edt": eps[0]["end_dt"],
        "eps": [eps[0]],
    }
    for ep in eps[1:]:
        gap = (ep["start_dt"] - cur["edt"]).total_seconds() / 60 if ep["start_dt"] and cur["edt"] else 999
        if gap <= SEGMENT_GAP_MINUTES:
            cur["end"] = ep["end"]
            cur["edt"] = ep["end_dt"]
            cur["eps"].append(ep)
        else:
            segs.append(cur)
            cur = {"start": ep["start"], "end": ep["end"], "sdt": ep["start_dt"], "edt": ep["end_dt"], "eps": [ep]}
    segs.append(cur)
    result = []
    for s in segs:
        pats = [e["pattern"] for e in s["eps"]]
        fc, mc = pats.count("fixed"), pats.count("migrating")
        if mc == 0:
            pat = "始终同一节点最忙"
        elif fc == 0:
            pat = "最忙节点在变化"
        else:
            total = fc + mc
            pat = f"{total}次中{fc}次固定/{mc}次变化"
        dur = (s["edt"] - s["sdt"]).total_seconds() / 60 if s["sdt"] and s["edt"] else 0
        hot_set = set()
        for ep in s["eps"]:
            for n in ep["hot_nodes"]:
                hot_set.add(n["display"])
        result.append(
            {
                "start": s["start"],
                "end": s["end"],
                "count": len(s["eps"]),
                "pattern": pat,
                "max_pct": round(max(e["max_hot_pct"] for e in s["eps"]), 1),
                "duration_min": round(dur),
                "hot_nodes": sorted(hot_set),
            }
        )
    return result


def node_stats(episodes):
    st = defaultdict(lambda: {"hc": 0, "cc": 0, "hp": [], "cp": [], "hv": [], "cv": []})
    for ep in episodes:
        for n in ep["hot_nodes"]:
            d = st[n["display"]]
            d["hc"] += 1
            d["hp"].append(n["pct"])
            d["hv"].append(n["value"])
        for n in ep["cold_nodes"]:
            d = st[n["display"]]
            d["cc"] += 1
            d["cp"].append(abs(n["pct"]))
            d["cv"].append(n["value"])
    out = {}
    for k, d in st.items():
        out[k] = {
            "display": k,
            "hot_count": d["hc"],
            "cold_count": d["cc"],
            "avg_hot_pct": round(sum(d["hp"]) / len(d["hp"]), 1) if d["hp"] else 0,
            "max_hot_pct": round(max(d["hp"]), 1) if d["hp"] else 0,
            "avg_cold_pct": round(sum(d["cp"]) / len(d["cp"]), 1) if d["cp"] else 0,
            "max_cold_pct": round(max(d["cp"]), 1) if d["cp"] else 0,
            "avg_hot_val": round(sum(d["hv"]) / len(d["hv"]), 1) if d["hv"] else 0,
            "avg_cold_val": round(sum(d["cv"]) / len(d["cv"]), 1) if d["cv"] else 0,
        }
    return out


def _severity(max_pct, ep_count, hours):
    cov = ep_count / max(hours * 12, 1)
    if max_pct > 100 or (max_pct > 50 and cov > 0.3):
        return "严重"
    if max_pct > 50 or (max_pct > 30 and cov > 0.2):
        return "中度"
    return "轻度"


def _get_attr(metric, role):
    tier = _tier(role)
    for key in [(metric, tier), (metric, None), (None, tier)]:
        if key in ATTRIBUTION:
            return ATTRIBUTION[key]
    return {"cause": f"{METRIC_NAMES.get(metric, metric)}倾斜", "tips": ["进一步排查"]}


# ── Deep Pattern Analysis ────────────────────────────────────────────────────


def _linreg(x, y):
    """Simple linear regression. Returns (slope, r2)."""
    n = len(x)
    if n < 3:
        return 0, 0
    sx, sy = sum(x), sum(y)
    sxy = sum(a * b for a, b in zip(x, y))
    sx2 = sum(a * a for a in x)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0, 0
    slope = (n * sxy - sx * sy) / denom
    ym = sy / n
    ss_tot = sum((yi - ym) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + (sy - slope * sx) / n)) ** 2 for xi, yi in zip(x, y))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return slope, r2


def _pearson(x, y):
    n = len(x)
    if n < 3:
        return 0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x) ** 0.5
    dy = sum((b - my) ** 2 for b in y) ** 0.5
    return num / (dx * dy) if dx * dy > 0 else 0


def deep_analysis(sorted_eps, ns):
    """Produce deeper insights from episode list and node_stats."""
    result = {}

    # 1. Hour-of-day distribution
    hour_counts = defaultdict(int)
    for ep in sorted_eps:
        if ep["start_dt"]:
            hour_counts[ep["start_dt"].hour] += 1
    hour_dist = [(h, hour_counts.get(h, 0)) for h in range(24)]
    peak_hours = sorted(hour_counts, key=hour_counts.get, reverse=True)[:3]
    total = len(sorted_eps)
    peak_pct = sum(hour_counts[h] for h in peak_hours) / total * 100 if total else 0
    result["hour_dist"] = hour_dist
    result["peak_hours"] = peak_hours
    result["peak_pct"] = round(peak_pct, 1)

    # 2. Trend: deviation over time
    if len(sorted_eps) >= 3:
        t0 = sorted_eps[0]["start_dt"]
        xs = [(ep["start_dt"] - t0).total_seconds() / 3600 for ep in sorted_eps if ep["start_dt"]]
        ys = [ep["max_hot_pct"] for ep in sorted_eps]
        slope, r2 = _linreg(xs, ys)
        if r2 > 0.3 and abs(slope) > 1:
            if slope > 0:
                trend = "上升"
                trend_desc = f"偏离度在加剧（每小时 +{slope:.1f}%，R²={r2:.2f}）"
            else:
                trend = "下降"
                trend_desc = f"偏离度在缓解（每小时 {slope:.1f}%，R²={r2:.2f}）"
        else:
            trend = "平稳"
            trend_desc = f"偏离度基本平稳（R²={r2:.2f}，无显著趋势）"
        result["trend"] = trend
        result["trend_desc"] = trend_desc
        result["trend_slope"] = round(slope, 2)
        result["trend_r2"] = round(r2, 2)
    else:
        result["trend"] = "数据不足"
        result["trend_desc"] = "事件数不足，无法判断趋势"

    # 3. Node behavior classification
    node_classes = []
    for name, s in ns.items():
        total_app = s["hot_count"] + s["cold_count"]
        if total_app == 0:
            continue
        hot_ratio = s["hot_count"] / total_app
        if s["hot_count"] > 0 and s["cold_count"] == 0:
            cls = "持续高负载"
            desc = f"全部 {s['hot_count']} 次均为偏高"
        elif s["cold_count"] > 0 and s["hot_count"] == 0:
            cls = "持续低负载"
            desc = f"全部 {s['cold_count']} 次均为偏低"
        elif hot_ratio > 0.7:
            cls = "偏高为主"
            desc = f"{s['hot_count']}次偏高 / {s['cold_count']}次偏低"
        elif hot_ratio < 0.3:
            cls = "偏低为主"
            desc = f"{s['hot_count']}次偏高 / {s['cold_count']}次偏低"
        else:
            cls = "波动型"
            desc = f"{s['hot_count']}次偏高 / {s['cold_count']}次偏低，角色不固定"
        node_classes.append(
            {"display": name, "class": cls, "desc": desc, "hot": s["hot_count"], "cold": s["cold_count"]}
        )
    node_classes.sort(key=lambda x: (-x["hot"], -x["cold"]))
    result["node_classes"] = node_classes

    # 4. Load-skew correlation
    means = [ep["group_mean"] for ep in sorted_eps if ep["group_mean"] is not None]
    pcts = [ep["max_hot_pct"] for ep in sorted_eps]
    if len(means) >= 3 and len(means) == len(pcts):
        r = _pearson(means, pcts)
        result["load_corr"] = round(r, 2)
        if r > 0.5:
            result["load_corr_desc"] = f"正相关（r={r:.2f}）：负载越高倾斜越严重，属于负载驱动型倾斜"
        elif r < -0.5:
            result["load_corr_desc"] = f"负相关（r={r:.2f}）：负载低时反而更倾斜，可能是空闲连接分布不均"
        else:
            result["load_corr_desc"] = f"无显著关联（r={r:.2f}）：倾斜与负载高低无关，属于结构性倾斜"
    else:
        result["load_corr"] = 0
        result["load_corr_desc"] = "数据不足"

    # 5. Episode gap analysis
    if len(sorted_eps) >= 2:
        gaps = []
        for i in range(1, len(sorted_eps)):
            if sorted_eps[i]["start_dt"] and sorted_eps[i - 1]["end_dt"]:
                g = (sorted_eps[i]["start_dt"] - sorted_eps[i - 1]["end_dt"]).total_seconds() / 60
                if g > 0:
                    gaps.append(g)
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            result["gap_avg"] = round(avg_gap)
            result["gap_min"] = round(min(gaps))
            result["gap_max"] = round(max(gaps))
            if avg_gap < 30:
                result["gap_desc"] = "倾斜几乎持续发生，间隔极短"
            elif avg_gap < 120:
                result["gap_desc"] = "倾斜频繁发作，间隔较短"
            else:
                result["gap_desc"] = "倾斜间歇性出现，有明显恢复期"
            # Check if gaps are getting shorter (acceleration)
            if len(gaps) >= 4:
                half = len(gaps) // 2
                first_half_avg = sum(gaps[:half]) / half
                second_half_avg = sum(gaps[half:]) / (len(gaps) - half)
                if second_half_avg < first_half_avg * 0.6:
                    result["gap_desc"] += "，且发作频率在加速"
                elif second_half_avg > first_half_avg * 1.5:
                    result["gap_desc"] += "，但发作频率在减缓"
        else:
            result["gap_desc"] = "无法计算间隔"
    else:
        result["gap_desc"] = "仅一次事件，无法分析间隔"

    # 6. Key event highlights
    highlights = []
    if sorted_eps:
        # Most severe episode
        worst = max(sorted_eps, key=lambda e: e["max_hot_pct"])
        hot_names = ", ".join(n["display"] for n in worst["hot_nodes"][:2])
        top_val = worst["hot_nodes"][0]["value"] if worst["hot_nodes"] else 0
        highlights.append(
            {
                "tag": "最严重",
                "time": f"{worst['start']} - {worst['end']}" if worst["start"] != worst["end"] else worst["start"],
                "text": (
                    f"最大偏离 +{worst['max_hot_pct']:.1f}%，组均值 {worst['group_mean']}。"
                    f"热点节点 {hot_names}，实际值 {top_val:.1f}，"
                    f"约为均值的 {top_val / worst['group_mean']:.1f} 倍。"
                    if worst["group_mean"]
                    else f"最大偏离 +{worst['max_hot_pct']:.1f}%"
                ),
            }
        )

        # Most transitions in one episode
        max_trans_ep = None
        max_trans_count = 0
        for ep in sorted_eps:
            if ep["transition_count"] > max_trans_count:
                max_trans_count = ep["transition_count"]
                max_trans_ep = ep
        if max_trans_ep and max_trans_count >= 3:
            dur = ""
            if max_trans_ep["start"] != max_trans_ep["end"]:
                if max_trans_ep["start_dt"] and max_trans_ep["end_dt"]:
                    mins = int((max_trans_ep["end_dt"] - max_trans_ep["start_dt"]).total_seconds() / 60)
                    dur = f"（{mins}分钟内）"
            highlights.append(
                {
                    "tag": "最频繁切换",
                    "time": f"{max_trans_ep['start']} - {max_trans_ep['end']}",
                    "text": f"{dur}发生 {max_trans_count} 次热点切换，热点集合剧烈变化。",
                }
            )

        # Node role flips: normally cold node becoming hot
        overall_hot = {
            n["display"]
            for n in sorted(ns.values(), key=lambda x: -x["hot_count"])
            if n["hot_count"] > n["cold_count"]
        }
        overall_cold = {
            n["display"]
            for n in sorted(ns.values(), key=lambda x: -x["cold_count"])
            if n["cold_count"] > n["hot_count"] * 3
        }
        flips = []
        for ep in sorted_eps:
            hot_set = {n["display"] for n in ep["hot_nodes"]}
            for name in hot_set & overall_cold:
                node_data = next((n for n in ep["hot_nodes"] if n["display"] == name), None)
                if node_data:
                    flips.append(
                        {
                            "node": name,
                            "time": ep["start"],
                            "pct": node_data["pct"],
                            "value": node_data["value"],
                        }
                    )
        if flips:
            seen = set()
            unique_flips = []
            for f in flips:
                if f["node"] not in seen:
                    seen.add(f["node"])
                    unique_flips.append(f)
            flip_text = "；".join(
                f"{f['node']} 在 {f['time']} 反转为偏高（+{f['pct']:.1f}%，值 {f['value']:.1f}）" for f in unique_flips[:3]
            )
            highlights.append(
                {
                    "tag": "角色反转",
                    "text": f"平时持续偏低的节点突然变为热点：{flip_text}。这表明负载分布发生了剧烈变化。",
                }
            )

        # Highest absolute load episode
        max_mean_ep = max(sorted_eps, key=lambda e: e["group_mean"] or 0)
        if max_mean_ep["group_mean"] and len(sorted_eps) > 3:
            avg_all = sum(e["group_mean"] for e in sorted_eps if e["group_mean"]) / len(sorted_eps)
            ratio = max_mean_ep["group_mean"] / avg_all if avg_all else 0
            if ratio > 2:
                highlights.append(
                    {
                        "tag": "负载峰值",
                        "time": f"{max_mean_ep['start']} - {max_mean_ep['end']}"
                        if max_mean_ep["start"] != max_mean_ep["end"]
                        else max_mean_ep["start"],
                        "text": (
                            f"组均值 {max_mean_ep['group_mean']}，是全时段平均值 {avg_all:.1f} 的 "
                            f"{ratio:.1f} 倍。高负载时段的倾斜往往影响更大。"
                        ),
                    }
                )

    result["highlights"] = highlights

    # 7. Time-of-day narrative
    narratives = []
    if hour_counts:
        night_hours = range(0, 8)
        day_hours = range(8, 20)
        night_count = sum(hour_counts.get(h, 0) for h in night_hours)
        day_count = sum(hour_counts.get(h, 0) for h in day_hours)
        night_eps = [e for e in sorted_eps if e["start_dt"] and e["start_dt"].hour in night_hours]
        day_eps = [e for e in sorted_eps if e["start_dt"] and e["start_dt"].hour in day_hours]
        night_avg_pct = (sum(e["max_hot_pct"] for e in night_eps) / len(night_eps)) if night_eps else 0
        day_avg_pct = (sum(e["max_hot_pct"] for e in day_eps) / len(day_eps)) if day_eps else 0
        night_avg_mean = (
            (sum(e["group_mean"] for e in night_eps if e["group_mean"]) / len(night_eps)) if night_eps else 0
        )
        day_avg_mean = (sum(e["group_mean"] for e in day_eps if e["group_mean"]) / len(day_eps)) if day_eps else 0

        if night_count > 0 and day_count > 0:
            if night_avg_pct > day_avg_pct * 1.3:
                narratives.append(
                    f"夜间（00-08时）平均偏离 {night_avg_pct:.1f}% 显著高于白天（08-20时）{day_avg_pct:.1f}%。"
                    f"夜间平均负载 {night_avg_mean:.1f}，白天 {day_avg_mean:.1f}。"
                )
                if night_avg_mean > day_avg_mean * 1.5:
                    narratives.append("夜间负载明显更高且倾斜更严重，建议排查凌晨是否有定时任务、批处理或数据同步作业集中连接特定节点。")
                else:
                    narratives.append("夜间负载并不明显更高但倾斜更严重，说明夜间连接分布比白天更不均匀，可能与夜间业务连接模式有关。")
            elif day_avg_pct > night_avg_pct * 1.3:
                narratives.append(f"白天（08-20时）平均偏离 {day_avg_pct:.1f}% 高于夜间 {night_avg_pct:.1f}%，" f"倾斜主要发生在业务高峰时段。")
            else:
                narratives.append(f"全天倾斜程度相当（夜间 {night_avg_pct:.1f}% vs 白天 {day_avg_pct:.1f}%），属于持续性结构倾斜。")
        elif night_count > 0:
            narratives.append("倾斜集中在夜间，白天未检测到倾斜。")
        elif day_count > 0:
            narratives.append("倾斜集中在白天，夜间未检测到倾斜。")

    result["time_narrative"] = narratives

    # 8. Enhanced recommendations based on data
    enhanced_tips = []
    if total > 0:
        mig_ratio = sum(1 for e in sorted_eps if e["pattern"] == "migrating") / total
        if mig_ratio > 0.6:
            enhanced_tips.append("热点迁移占比超过 60%，强烈指向 DNS 缓存问题：TTL 到期时连接跳转到新节点形成新热点。建议优先将接入方式从 DNS 改为 CLB。")
        persistent_cold = [nc for nc in result.get("node_classes", []) if nc["class"] == "持续低负载"]
        if persistent_cold:
            names = "、".join(nc["display"] for nc in persistent_cold[:3])
            enhanced_tips.append(f"{names} 始终处于低负载，流量几乎不经过这些节点。建议检查 DNS 解析是否将这些节点纳入轮询，或确认这些节点是否健康可用。")
        if night_eps and night_avg_pct > 100:
            enhanced_tips.append("凌晨时段出现极端倾斜（偏离 >100%），建议检查该时段是否有定时任务、数据同步或批处理作业，这类作业通常通过固定连接打到单一节点。")
    result["enhanced_tips"] = enhanced_tips

    return result


def analyze_group(metric, role, episodes):
    starts = sorted(e["start"] for e in episodes)
    ends = sorted(e["end"] for e in episodes)
    pats = [e["pattern"] for e in episodes]
    means = [e["group_mean"] for e in episodes if e["group_mean"] is not None]
    dts = [e["start_dt"] for e in episodes if e["start_dt"]] + [e["end_dt"] for e in episodes if e["end_dt"]]
    hours = (max(dts) - min(dts)).total_seconds() / 3600 if dts else 0
    max_hp = max(e["max_hot_pct"] for e in episodes) if episodes else 0

    ns = node_stats(episodes)
    hot_ranked = sorted(
        [n for n in ns.values() if n["hot_count"] > 0], key=lambda x: (-x["hot_count"], -x["max_hot_pct"])
    )
    cold_ranked = sorted(
        [n for n in ns.values() if n["cold_count"] > 0], key=lambda x: (-x["cold_count"], -x["max_cold_pct"])
    )

    sorted_eps = sorted(episodes, key=lambda x: x["start"])
    timeline = [
        {"t": e["start"][-11:], "pct": round(e["max_hot_pct"], 1), "pat": e["pattern"], "mean": e["group_mean"]}
        for e in sorted_eps
    ]

    all_node_names = set()
    for ep in episodes:
        for n in ep["hot_nodes"] + ep["cold_nodes"]:
            all_node_names.add(n["display"])
    node_series = {}
    for name in sorted(all_node_names):
        series = []
        for ep in sorted_eps:
            val = None
            for n in ep["hot_nodes"] + ep["cold_nodes"]:
                if n["display"] == name:
                    val = round(n["value"], 1)
                    break
            series.append(val)
        node_series[name] = series
    mean_series = [ep["group_mean"] for ep in sorted_eps]

    deep = deep_analysis(sorted_eps, ns)

    return {
        "metric": metric,
        "role": role,
        "metric_name": METRIC_NAMES.get(metric, metric),
        "role_name": ROLE_NAMES.get(role, role),
        "tier": _tier(role),
        "ep_count": len(episodes),
        "time_range": f"{starts[0]} - {ends[-1]}",
        "hours": round(hours, 1),
        "fixed": pats.count("fixed"),
        "migrating": pats.count("migrating"),
        "avg_mean": round(sum(means) / len(means), 1) if means else 0,
        "max_hot_pct": round(max_hp, 1),
        "max_cold_pct": round(max(e["max_cold_pct"] for e in episodes), 1) if episodes else 0,
        "severity": _severity(max_hp, len(episodes), hours),
        "segments": merge_segments(episodes),
        "hot_ranked": hot_ranked[:10],
        "cold_ranked": cold_ranked[:10],
        "node_stats": ns,
        "attr": _get_attr(metric, role),
        "timeline": timeline,
        "node_series": node_series,
        "mean_series": mean_series,
        "deep": deep,
    }


def analyze(data, tz_offset=None, tz_label="UTC"):
    cluster = data.get("cluster", "unknown")
    period = data.get("period", {})
    period["tz_label"] = tz_label
    if tz_offset:
        for key in ("from", "to"):
            dt = _parse_dt(period.get(key, ""), tz_offset)
            if dt:
                period[key] = dt.strftime("%Y-%m-%d %H:%M")
    if not data.get("has_skew"):
        return {"has_skew": False, "cluster": cluster, "period": period, "groups": []}

    episodes = parse_episodes(data, tz_offset=tz_offset)
    if not episodes:
        return {"has_skew": False, "cluster": cluster, "period": period, "groups": []}

    grouped = defaultdict(list)
    for ep in episodes:
        grouped[(ep["metric"], ep["role"])].append(ep)

    groups = [analyze_group(m, r, eps) for (m, r), eps in grouped.items()]
    sev_order = {"严重": 0, "中度": 1, "轻度": 2}
    groups.sort(key=lambda g: (sev_order.get(g["severity"], 9), -g["ep_count"]))

    # Cross-metric correlations
    corrs = []
    qps_g = [g for g in groups if g["metric"] == "qps_summary"]
    cpu_g = [g for g in groups if g["metric"] == "cpu_summary"]
    for q in qps_g:
        for c in cpu_g:
            if _tier(q["role"]) == _tier(c["role"]):
                qh = {n["display"] for n in q["hot_ranked"][:3]}
                ch = {n["display"] for n in c["hot_ranked"][:3]}
                overlap = qh & ch
                if overlap:
                    corrs.append(f"QPS 与 CPU 倾斜在{_tier(q['role'])}联动，" f"热点节点重合({', '.join(sorted(overlap))})")

    return {
        "has_skew": True,
        "cluster": cluster,
        "period": period,
        "groups": groups,
        "correlations": corrs,
        "total_eps": sum(g["ep_count"] for g in groups),
        "severity": groups[0]["severity"] if groups else "轻度",
    }


# ── Summary ──────────────────────────────────────────────────────────────────


def make_summary(a):
    if not a["has_skew"]:
        return f"{a['cluster']} 查询时段内未检测到倾斜。"
    groups = a["groups"]
    parts = []
    for gi in groups:
        ranked = gi["hot_ranked"]
        if len(ranked) <= 2:
            hot_desc = "、".join(n["display"] for n in ranked)
        else:
            hot_desc = f"{ranked[0]['display']}等{len(ranked)}节点"
        pat = "迁移" if gi["migrating"] > gi["fixed"] else "稳定"
        parts.append(
            f"{gi['tier']}{gi['metric_name']}{gi['ep_count']}次" f"（最大偏离{gi['max_hot_pct']}%，热点{pat}，{hot_desc}）"
        )
    s = f"{a['cluster']} 检测到{a['total_eps']}次倾斜（{a['severity']}）：{'；'.join(parts)}。"
    return s[:200]


# ── HTML Report ──────────────────────────────────────────────────────────────

_SEV_COLOR = {"严重": "#e74c3c", "中度": "#f39c12", "轻度": "#27ae60"}


def _card(label, value, color=None):
    vc = f' style="color:{color}"' if color else ""
    return f'<div class="card"><div class="val"{vc}>{value}</div><div class="lbl">{label}</div></div>'


def _seg_table(segments):
    rows = ""
    for s in segments:
        dur = f"{s['duration_min']}分钟" if s["duration_min"] > 0 else "单次检测"
        nodes = "、".join(s["hot_nodes"])
        if len(s["hot_nodes"]) == 1:
            who = f"始终为 {nodes}"
        else:
            who = f"在 {nodes} 之间变化"
        rows += (
            f"<tr><td>{s['start']}</td><td>{s['end']}</td><td>{dur}</td>"
            f"<td>{s['count']}</td><td>{s['pattern']}</td>"
            f"<td class='hot'>{who}</td>"
            f"<td>{s['max_pct']}%</td></tr>\n"
        )
    return f"""<table>
<thead><tr><th>开始</th><th>结束</th><th>持续</th><th>检测次数</th><th>最忙节点是否变化</th><th>涉及节点</th><th>最大偏离</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def _node_table(hot_ranked, cold_ranked):
    rows = ""
    for n in hot_ranked:
        rows += (
            f"<tr><td>{n['display']}</td><td class='hot'>偏高</td>"
            f"<td>{n['hot_count']}</td><td>+{n['avg_hot_pct']}%</td>"
            f"<td>+{n['max_hot_pct']}%</td><td>{n['avg_hot_val']}</td></tr>\n"
        )
    for n in cold_ranked:
        if n["display"] not in {h["display"] for h in hot_ranked}:
            rows += (
                f"<tr><td>{n['display']}</td><td class='cold'>偏低</td>"
                f"<td>{n['cold_count']}</td><td>-{n['avg_cold_pct']}%</td>"
                f"<td>-{n['max_cold_pct']}%</td><td>{n['avg_cold_val']}</td></tr>\n"
            )
    return f"""<table>
<thead><tr><th>节点</th><th>方向</th><th>出现次数</th><th>平均偏离</th><th>最大偏离</th><th>平均值</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def _deep_html(deep):
    parts = []

    # Key event highlights (most important - put first)
    highlights = deep.get("highlights", [])
    if highlights:
        items = ""
        tag_colors = {"最严重": "#e74c3c", "最频繁切换": "#e67e22", "角色反转": "#9b59b6", "负载峰值": "#2980b9"}
        for h in highlights:
            tc = tag_colors.get(h["tag"], "#555")
            time_str = f' <span style="color:#888">({h["time"]})</span>' if h.get("time") else ""
            items += (
                f'<div class="highlight-item">'
                f'<span class="hl-tag" style="background:{tc}">{h["tag"]}</span>'
                f'{time_str}<br>{h["text"]}</div>\n'
            )
        parts.append(f'<div class="insight"><h4>关键事件</h4>{items}</div>')

    # Time-of-day narrative
    time_narr = deep.get("time_narrative", [])
    hour_dist = deep.get("hour_dist", [])
    if hour_dist:
        max_c = max(c for _, c in hour_dist) or 1
        bars = ""
        for h, c in hour_dist:
            w = int(c / max_c * 100) if c > 0 else 0
            label = f"{c}" if c > 0 else ""
            bars += (
                f'<div class="hour-row"><span class="hour-label">{h:02d}时</span>'
                f'<div class="hour-bar" style="width:{w}%">{label}</div></div>\n'
            )
        narr_html = "".join(f"<p>{n}</p>" for n in time_narr)
        peak = "、".join(f"{h:02d}时" for h in deep.get("peak_hours", []))
        parts.append(
            f"""<div class="insight">
<h4>时间维度</h4>
<p>倾斜集中在 <strong>{peak}</strong>（占 {deep.get('peak_pct', 0)}%）</p>
{narr_html}
<div class="hour-chart">{bars}</div></div>"""
        )

    # Node classification
    nc = deep.get("node_classes", [])
    if nc:
        rows = ""
        cls_colors = {"持续高负载": "#e74c3c", "偏高为主": "#e67e22", "波动型": "#f39c12", "偏低为主": "#3498db", "持续低负载": "#2980b9"}
        for n in nc:
            c = cls_colors.get(n["class"], "#999")
            rows += (
                f"<tr><td>{n['display']}</td>"
                f"<td><span style='color:{c};font-weight:600'>{n['class']}</span></td>"
                f"<td>{n['desc']}</td></tr>\n"
            )
        parts.append(
            f"""<div class="insight">
<h4>节点行为分类</h4>
<table><thead><tr><th>节点</th><th>类型</th><th>说明</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""
        )

    # Trend + Load correlation + Gap (compact row)
    parts.append(
        f"""<div class="insight">
<h4>趋势判断</h4><p>{deep.get('trend_desc', '')}</p></div>"""
    )

    parts.append(
        f"""<div class="insight">
<h4>负载-倾斜关联</h4><p>{deep.get('load_corr_desc', '')}</p></div>"""
    )

    gap_desc = deep.get("gap_desc", "")
    gap_detail = ""
    if "gap_avg" in deep:
        gap_detail = f"（平均间隔 {deep['gap_avg']} 分钟，最短 {deep['gap_min']} 分钟，最长 {deep['gap_max']} 分钟）"
    parts.append(
        f"""<div class="insight">
<h4>发作间隔</h4><p>{gap_desc}{gap_detail}</p></div>"""
    )

    # Enhanced recommendations
    tips = deep.get("enhanced_tips", [])
    if tips:
        items = "".join(f"<li>{t}</li>" for t in tips)
        parts.append(
            f"""<div class="insight" style="background:#fff3cd;border-left:3px solid #f0c040">
<h4>数据驱动的排查建议</h4><ul style="padding-left:20px;margin:6px 0">{items}</ul></div>"""
        )

    return f'<div class="deep-section"><h3>深度分析</h3>{"".join(parts)}</div>'


def _group_html(g, idx):
    sc = _SEV_COLOR.get(g["severity"], "#999")
    return f"""
<div class="group">
  <h2>{g['metric_name']} / {g['role_name']}
    <span class="badge" style="background:{sc}">{g['severity']}</span></h2>
  <div class="cards">
    {_card('倾斜事件', g['ep_count'])}
    {_card('时间跨度', f"{g['hours']}h")}
    {_card('最大偏离', f"{g['max_hot_pct']}%", sc)}
    {_card('热点稳定', g['fixed'])}
    {_card('热点迁移', g['migrating'])}
    {_card('组均值', g['avg_mean'])}
  </div>
  <div class="chart-box"><h3>各节点负载走势</h3>
    <div class="chart-toolbar">
      <span class="chart-hint">点击图例可显示/隐藏单个节点</span>
      <button onclick="toggleAllNodes('ns_{idx}',true)">全部显示</button>
      <button onclick="toggleAllNodes('ns_{idx}',false)">全部隐藏</button>
    </div>
    <canvas id="ns_{idx}"></canvas></div>
  <div class="chart-box"><h3>节点热点/冷点频次</h3><canvas id="nd_{idx}"></canvas></div>
  <div class="commentary"><!-- COMMENTARY_{idx}_OVERVIEW --></div>
  <h3>倾斜时段</h3>
  {_seg_table(g['segments'])}
  <div class="commentary"><!-- COMMENTARY_{idx}_SEGMENTS --></div>
  <h3>节点统计</h3>
  {_node_table(g['hot_ranked'], g['cold_ranked'])}
  <div class="commentary"><!-- COMMENTARY_{idx}_NODES --></div>
  {_deep_html(g['deep'])}
  <div class="commentary"><!-- COMMENTARY_{idx}_DEEP --></div>
</div>"""


_NODE_COLORS = [
    "#e74c3c",
    "#3498db",
    "#2ecc71",
    "#f39c12",
    "#9b59b6",
    "#1abc9c",
    "#e67e22",
    "#34495e",
    "#d35400",
    "#8e44ad",
    "#16a085",
    "#c0392b",
    "#2980b9",
    "#27ae60",
]


def _charts_js(groups):
    blocks = []
    for i, g in enumerate(groups):
        labels = json.dumps([d["t"] for d in g["timeline"]], ensure_ascii=False)

        # Node QPS walk chart
        node_datasets = []
        mean_data = json.dumps(g["mean_series"])
        node_names = sorted(g["node_series"].keys())
        for ci, name in enumerate(node_names):
            color = _NODE_COLORS[ci % len(_NODE_COLORS)]
            data = json.dumps(g["node_series"][name])
            node_datasets.append(
                f'{{label:"{name}",data:{data},borderColor:"{color}",borderWidth:2,'
                f'pointRadius:3,pointBackgroundColor:"{color}",fill:false,spanGaps:false}}'
            )
        node_datasets.append(
            f'{{label:"组均值",data:{mean_data},borderColor:"rgba(150,150,150,0.4)",borderWidth:1,'
            f'pointRadius:0,fill:true,backgroundColor:"rgba(100,100,100,0.25)",spanGaps:true}}'
        )
        node_ds_str = ",\n    ".join(node_datasets)

        ns = g["node_stats"]
        all_nodes = sorted(ns.values(), key=lambda n: (-n["hot_count"], -n["cold_count"]))
        nlabels = json.dumps([n["display"] for n in all_nodes], ensure_ascii=False)
        hcounts = json.dumps([n["hot_count"] for n in all_nodes])
        ccounts = json.dumps([-n["cold_count"] for n in all_nodes])

        mname = g["metric_name"]
        blocks.append(
            f"""
_charts['ns_{i}'] = new Chart(document.getElementById('ns_{i}'), {{
  type:'line',
  data:{{labels:{labels},datasets:[
    {node_ds_str}
  ]}},
  options:{{responsive:true,
    plugins:{{legend:{{position:'bottom',
      labels:{{padding:14,usePointStyle:true,pointStyle:'rectRounded',font:{{size:12}}}},
      onClick:function(e,item,legend){{
        var ds=legend.chart.data.datasets;
        if(item.datasetIndex===ds.length-1) return;
        var meta=legend.chart.getDatasetMeta(item.datasetIndex);
        meta.hidden=!meta.hidden; legend.chart.update();
      }}
    }},title:{{display:false}}}},
    scales:{{
      x:{{ticks:{{maxRotation:60,font:{{size:10}}}}}},
      y:{{title:{{display:true,text:'{mname}'}},beginAtZero:true}}
    }}
  }}
}});
new Chart(document.getElementById('nd_{i}'), {{
  type:'bar',
  data:{{labels:{nlabels},datasets:[
    {{label:'热点次数',data:{hcounts},backgroundColor:'#e74c3c'}},
    {{label:'冷点次数',data:{ccounts},backgroundColor:'#3498db'}}
  ]}},
  options:{{indexAxis:'y',responsive:true,
    plugins:{{legend:{{position:'bottom'}},
      tooltip:{{callbacks:{{label:function(c){{return c.dataset.label+': '+Math.abs(c.raw)+'次'}}}}}}}},
    scales:{{x:{{ticks:{{callback:function(v){{return Math.abs(v)}}}}}}}}
  }}
}});"""
        )
    return "\n".join(blocks)


def generate_html(analysis):
    a = analysis
    cluster = a["cluster"]
    period = a["period"]
    p_from = period.get("from", "")
    p_to = period.get("to", "")
    tz = period.get("tz_label", "UTC")

    if not a["has_skew"]:
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{cluster} 集群倾斜报告</title></head><body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h1>{cluster} 集群倾斜报告</h1><p>查询范围：{p_from} - {p_to} ({tz})</p>
<div style="background:#d4edda;padding:20px;border-radius:8px;font-size:18px">
✅ 查询时段内未检测到倾斜</div></body></html>"""

    groups_html = "\n".join(_group_html(g, i) for i, g in enumerate(a["groups"]))
    corr_html = ""
    if a.get("correlations"):
        items = "".join(f"<li>{c}</li>" for c in a["correlations"])
        corr_html = f'<div class="group"><h2>跨指标关联</h2><ul>{items}</ul></div>'

    sc = _SEV_COLOR.get(a["severity"], "#999")
    summary_text = make_summary(a)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{cluster} 集群倾斜报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#f0f2f5;color:#1a1a2e;line-height:1.6}}
.wrap{{max-width:1100px;margin:0 auto;padding:16px}}
header{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;
  padding:28px 32px;border-radius:10px;margin-bottom:20px}}
header h1{{font-size:22px;margin-bottom:6px}}
header p{{opacity:.85;font-size:14px}}
.summary{{background:#fff;padding:16px 20px;border-radius:10px;margin-bottom:20px;
  border-left:4px solid {sc};font-size:14px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:16px 0}}
.card{{background:#fff;padding:14px;border-radius:8px;text-align:center;
  box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card .val{{font-size:24px;font-weight:700}}
.card .lbl{{font-size:12px;color:#888;margin-top:2px}}
.group{{background:#fff;padding:20px 24px;border-radius:10px;margin-bottom:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.group h2{{font-size:17px;border-bottom:2px solid #3498db;padding-bottom:6px;margin-bottom:14px}}
.group h3{{font-size:14px;margin:16px 0 8px;color:#555}}
.badge{{display:inline-block;color:#fff;font-size:12px;padding:2px 10px;border-radius:12px;
  margin-left:8px;vertical-align:middle}}
.chart-box{{margin:14px 0}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}}
th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #eee}}
th{{background:#f8f9fa;font-weight:600}}
.hot{{color:#e74c3c;font-weight:600}}
.cold{{color:#3498db;font-weight:600}}
.attr{{background:#fffbea;border-left:4px solid #f0c040;padding:14px 18px;border-radius:0 8px 8px 0;margin-top:14px}}
.attr ul{{padding-left:20px;margin-top:6px}}
.attr li{{margin:4px 0}}
.deep-section{{margin-top:20px;border-top:2px solid #3498db;padding-top:16px}}
.highlight-item{{margin:8px 0;padding:8px 12px;background:#fff;border-radius:6px;
  border:1px solid #eee;font-size:13px;line-height:1.7}}
.hl-tag{{display:inline-block;color:#fff;font-size:11px;padding:1px 8px;border-radius:10px;
  margin-right:6px;font-weight:600}}
.insight{{background:#f8f9fa;padding:12px 16px;border-radius:8px;margin:10px 0}}
.insight h4{{font-size:13px;color:#2c3e50;margin-bottom:6px}}
.insight p{{font-size:13px;margin:0}}
.hour-chart{{display:flex;flex-direction:column;gap:2px;margin-top:8px}}
.hour-row{{display:flex;align-items:center;gap:6px}}
.hour-label{{font-size:11px;color:#888;width:32px;text-align:right}}
.hour-bar{{background:#3498db;color:#fff;font-size:10px;padding:1px 6px;border-radius:2px;min-height:14px}}
.chart-toolbar{{display:flex;align-items:center;gap:10px;margin:4px 0 8px}}
.chart-hint{{font-size:12px;color:#888}}
.chart-toolbar button{{font-size:12px;padding:3px 10px;border:1px solid #ccc;border-radius:4px;
  background:#f8f9fa;cursor:pointer}}
.chart-toolbar button:hover{{background:#e9ecef}}
.commentary{{background:#f5f0ff;border-left:3px solid #8e44ad;padding:14px 18px;
  margin:14px 0;border-radius:0 8px 8px 0;font-size:13px;line-height:1.8;color:#333}}
.commentary:empty{{display:none}}
.commentary p{{margin:8px 0}}
.commentary ol,.commentary ul{{padding-left:20px;margin:8px 0}}
.commentary li{{margin:4px 0}}
.commentary strong{{color:#2c3e50}}
.commentary-section{{background:#fff;padding:20px 24px;border-radius:10px;margin-bottom:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #8e44ad}}
.commentary-section h2{{font-size:17px;color:#8e44ad;margin-bottom:12px}}
.commentary-section p{{margin:8px 0;font-size:13px;line-height:1.8}}
.commentary-section ol,.commentary-section ul{{padding-left:20px;margin:8px 0;font-size:13px;line-height:1.8}}
.commentary-section li{{margin:6px 0}}
footer{{text-align:center;color:#aaa;font-size:12px;padding:20px 0}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>{cluster} 集群倾斜报告</h1>
  <p>查询范围：{p_from} - {p_to} ({tz}) &nbsp;|&nbsp; 共 {a['total_eps']} 次倾斜事件</p>
</header>
<div class="summary">
  <strong style="color:{sc}">【{a['severity']}】</strong> {summary_text}
</div>
{groups_html}
{corr_html}
<!-- COMMENTARY_OVERALL -->
<footer>由 mysql-cluster-skew-report 自动生成</footer>
</div>
<script>
Chart.defaults.font.size = 11;
var _charts = {{}};
function toggleAllNodes(id, show) {{
  var c = _charts[id]; if (!c) return;
  var last = c.data.datasets.length - 1;
  for (var i = 0; i < last; i++) c.getDatasetMeta(i).hidden = !show;
  c.update();
}}
{_charts_js(a['groups'])}
</script>
</body>
</html>"""


# ── Findings Export ───────────────────────────────────────────────────────────


def export_findings(analysis):
    """Export compact findings for LLM consumption (no raw data)."""
    a = analysis
    if not a["has_skew"]:
        return {"has_skew": False, "cluster": a["cluster"]}

    groups_out = []
    for idx, g in enumerate(a["groups"]):
        d = g["deep"]
        groups_out.append(
            {
                "commentary_keys": {
                    "overview": f"{idx}_overview",
                    "segments": f"{idx}_segments",
                    "nodes": f"{idx}_nodes",
                    "deep": f"{idx}_deep",
                },
                "metric": g["metric_name"],
                "role": g["role_name"],
                "severity": g["severity"],
                "episode_count": g["ep_count"],
                "time_range": g["time_range"],
                "hours": g["hours"],
                "fixed": g["fixed"],
                "migrating": g["migrating"],
                "max_hot_pct": g["max_hot_pct"],
                "avg_mean": g["avg_mean"],
                "top_hot": [f"{n['display']}({n['hot_count']}次,最大+{n['max_hot_pct']}%)" for n in g["hot_ranked"][:3]],
                "persistent_cold": [f"{n['display']}({n['cold_count']}次)" for n in g["cold_ranked"][:3]],
                "highlights": [h["text"] for h in d.get("highlights", [])],
                "time_narrative": d.get("time_narrative", []),
                "trend": d.get("trend_desc", ""),
                "load_corr": d.get("load_corr_desc", ""),
                "gap": d.get("gap_desc", ""),
                "node_classes": [f"{nc['display']}: {nc['class']}" for nc in d.get("node_classes", [])],
                "enhanced_tips": d.get("enhanced_tips", []),
                "attribution_cause": g["attr"]["cause"],
            }
        )

    return {
        "has_skew": True,
        "cluster": a["cluster"],
        "period": f"{a['period'].get('from', '')} - {a['period'].get('to', '')}",
        "severity": a["severity"],
        "total_episodes": a["total_eps"],
        "correlations": a.get("correlations", []),
        "groups": groups_out,
    }


# ── Inject Commentary ────────────────────────────────────────────────────────


def inject_commentaries(html_path, commentaries_path):
    """Replace <!-- COMMENTARY_xxx --> placeholders with LLM-generated text."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    with open(commentaries_path, encoding="utf-8") as f:
        commentaries = json.load(f)

    for key, text in commentaries.items():
        placeholder = f"<!-- COMMENTARY_{key.upper()} -->"
        if key.lower() == "overall":
            section = f'<div class="commentary-section"><h2>综合解读</h2>' f"<div>{text}</div></div>"
        else:
            section = text
        html = html.replace(placeholder, section)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"INJECTED: {html_path}")


# ── MCP Query ────────────────────────────────────────────────────────────────


def query_skew_data(cluster_domain, from_date, to_date, raw_query, out_path):
    body = {
        "cluster_domain": cluster_domain,
        "from_date": from_date,
        "to_date": to_date,
    }
    cmd = [
        "dbm-mcp-cli",
        "call",
        "bkdbm-mcp-prod-mysql-query.mysql_query_query_cluster_skew_data",
        f"body_param={json.dumps(body, ensure_ascii=False)}",
        "--raw-query",
        raw_query or "查询集群倾斜数据",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        print("ERROR: dbm-mcp-cli not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: MCP query timed out", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print(f"ERROR: MCP query failed (exit {proc.returncode}): {proc.stderr[:300]}", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout)
    return out_path


# ── Upload ───────────────────────────────────────────────────────────────────


def upload_report(html_path, bk_biz_id, cluster_domain, summary, raw_query):
    cluster = cluster_domain
    body = {
        "ai_agent": "mysql-cluster-skew-report",
        "format": "html",
        "bk_biz_id": bk_biz_id,
        "cluster_domain": cluster_domain,
        "title": f"{cluster} 集群倾斜报告",
        "summary": summary,
        "content": f"@{html_path}",
    }
    cmd = [
        "dbm-mcp-cli",
        "call",
        "bkdbm-mcp-prod-ai-report.ai_report_write_report",
        f"body_param={json.dumps(body, ensure_ascii=False)}",
        "--raw-query",
        raw_query or "集群倾斜分析",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print("ERROR: dbm-mcp-cli not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: upload timed out", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print(f"ERROR: upload failed (exit {proc.returncode}): {proc.stderr[:300]}", file=sys.stderr)
        sys.exit(1)

    try:
        resp = json.loads(proc.stdout)
        data = resp.get("response_body", resp).get("data", resp.get("data", {}))
        url = data.get("share_url", "")
        rid = data.get("report_id", "")
        print(f"REPORT_URL: {url}")
        print(f"REPORT_ID: {rid}")
    except (json.JSONDecodeError, AttributeError):
        print(f"WARN: cannot parse upload response, raw: {proc.stdout[:200]}", file=sys.stderr)
        print("REPORT_URL: ")
        print("REPORT_ID: ")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="Generate MySQL skew report")
    sub = ap.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Query MCP, analyze, and generate report")
    gen.add_argument("--bk-biz-id", type=int, required=True)
    gen.add_argument("--cluster-domain", required=True)
    gen.add_argument("--from-date", required=True, help="Start time with timezone offset")
    gen.add_argument("--to-date", required=True, help="End time with timezone offset")
    gen.add_argument("--timezone", default="+08:00", help="Timezone offset for display, e.g. +08:00")
    gen.add_argument("--raw-query", default="")
    gen.add_argument("--out-dir", required=True)
    gen.add_argument("--raw-file", default="", help="Skip MCP query, use this file instead (for testing)")

    inj = sub.add_parser("inject", help="Inject LLM commentaries into report HTML")
    inj.add_argument("html_file", help="Path to report.html")
    inj.add_argument("commentaries_file", help="Path to commentaries.json")

    upl = sub.add_parser("upload", help="Upload report HTML via MCP")
    upl.add_argument("html_file", help="Path to report.html")
    upl.add_argument("--bk-biz-id", type=int, required=True)
    upl.add_argument("--cluster-domain", required=True)
    upl.add_argument("--summary", required=True)
    upl.add_argument("--raw-query", default="")

    args = ap.parse_args()

    if args.command == "inject":
        inject_commentaries(args.html_file, args.commentaries_file)
        return

    if args.command == "upload":
        upload_report(args.html_file, args.bk_biz_id, args.cluster_domain, args.summary, args.raw_query)
        return

    if args.command != "generate":
        ap.print_help()
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)

    raw_path = args.raw_file
    if not raw_path:
        raw_path = os.path.join(args.out_dir, "skew_raw.json")
        query_skew_data(args.cluster_domain, args.from_date, args.to_date, args.raw_query, raw_path)

    raw = load_raw(raw_path)
    data = extract_data(raw)

    tz_offset = _parse_tz_offset(args.timezone)

    if not data.get("has_skew"):
        cluster = data.get("cluster", args.cluster_domain)
        print(f"SUMMARY: {cluster} 查询时段内未检测到倾斜。")
        print("NO_SKEW: true")
        return

    a = analyze(data, tz_offset=tz_offset, tz_label=f"UTC{args.timezone}")

    html = generate_html(a)
    html_path = os.path.join(args.out_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    summary = make_summary(a)

    findings = export_findings(a)
    findings_path = os.path.join(args.out_dir, "findings.json")
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)

    print(f"SUMMARY: {summary}")
    print(f"HTML: {html_path}")
    print(f"FINDINGS: {findings_path}")


if __name__ == "__main__":
    main()
