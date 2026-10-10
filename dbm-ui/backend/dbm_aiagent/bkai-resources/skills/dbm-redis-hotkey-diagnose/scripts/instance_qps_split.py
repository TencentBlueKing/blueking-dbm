#!/usr/bin/env python3
"""
实例级 QPS/CPU 拆分与热点对比脚本

用法：
  python3 instance_qps_split.py <domain> <masters> <start_cst> <end_cst> [top_n]

masters 两种传法：
  1) 逗号分隔的 ip:port 列表，如 192.168.2.2:30000,192.168.2.2:30001,192.168.2.4:30002
  2) 一个 JSON 文件路径：把 redis_query_meta_list_cluster_masters 的返回 JSON 存盘后传入，
     脚本自动提取其中所有 ip:port（兼容 ip/port 分字段与 addr 字符串两种结构）

示例：
  python3 instance_qps_split.py cache.xxx.db 192.168.2.2:30000,192.168.2.2:30001 \
      2026-03-19T05:50:00+08:00 2026-03-19T06:05:00+08:00 5

流程：
  1) 并发拉取每个后端实例的 QPS 与 CPU 时序（instance_series）
  2) 按均值 QPS 降序找出 TOP N
  3) 输出 TOP N 实例的 QPS、CPU 与集群平均的倍数对比
     （集群平均 QPS 按实例均值，集群平均 CPU 按 IP 去重平均）

注意：
  - 时间参数使用 CST 带时区格式（+08:00），禁止手动转 UTC
  - 需先完成 MCP 鉴权（设置 MCPORTER_CONFIG 环境变量）
  - CPU 为主机级指标，同 IP 多实例返回相同值；QPS 为实例级（端口级）
"""
import subprocess, json, sys, os, re
from concurrent.futures import ThreadPoolExecutor

RE_IPPORT = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}:\d{1,5})\b")
RE_IP = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def query_instance_metric(domain, ip, port, metric, start, end):
    args = json.dumps(
        {
            "body_param": {
                "cluster_domain": domain,
                "metric_type": metric,
                "ip": ip,
                "port": int(port),
                "start_time": start,
                "end_time": end,
            }
        }
    )
    cmd = [
        "mcporter",
        "call",
        "bkdbm-mcp-prod-redis-metrics.redis_metrics_query_instance_series",
        "--args",
        args,
        "--output",
        "json",
    ]
    env = os.environ.copy()
    if "MCPORTER_CONFIG" in env:
        cmd += ["--config", env["MCPORTER_CONFIG"]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        d = json.loads(r.stdout)
        series = d["response_body"]["data"]["series"]
        for pts in series.values():
            return [p[0] for p in pts if p[0] is not None]
    except Exception:
        pass
    return []


def extract_from_json(obj, out):
    if isinstance(obj, dict):
        ip = obj.get("ip") or obj.get("instance_ip")
        port = obj.get("port")
        addr = obj.get("addr") or obj.get("instance_addr")
        if ip and port and RE_IP.match(str(ip)):
            out.add(f"{ip}:{port}")
        elif addr and RE_IPPORT.match(str(addr)):
            out.add(RE_IPPORT.search(str(addr)).group(1))
        for v in obj.values():
            extract_from_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            extract_from_json(v, out)


def parse_masters(arg):
    if os.path.isfile(arg):
        text = open(arg, encoding="utf-8", errors="ignore").read()
        out = set(RE_IPPORT.findall(text))
        try:
            extract_from_json(json.loads(text), out)
        except Exception:
            pass
        return sorted(out)
    addrs = [x.strip() for x in arg.split(",") if x.strip()]
    bad = [a for a in addrs if ":" not in a]
    if bad:
        print(f"格式错误：{bad} 。实例必须为 ip:port 形式，多实例用逗号分隔；" f"或传入 list_cluster_masters 返回 JSON 的文件路径。")
        sys.exit(1)
    return addrs


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    domain, masters_arg, start, end = sys.argv[1:5]
    top_n = int(sys.argv[5]) if len(sys.argv) > 5 else 5

    masters = parse_masters(masters_arg)
    if not masters:
        print("未解析到任何 ip:port 实例，请检查参数")
        sys.exit(1)

    def fetch(addr):
        ip, port = addr.rsplit(":", 1)
        qps = query_instance_metric(domain, ip, port, "qps", start, end)
        cpu = query_instance_metric(domain, ip, port, "cpu_usage", start, end)
        return addr, qps, cpu

    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(fetch, masters))

    stats = []
    for addr, qps, cpu in rows:
        stats.append(
            {
                "addr": addr,
                "qps_avg": sum(qps) / len(qps) if qps else 0.0,
                "qps_max": max(qps) if qps else 0.0,
                "cpu_avg": sum(cpu) / len(cpu) if cpu else 0.0,
                "cpu_max": max(cpu) if cpu else 0.0,
            }
        )

    qps_valid = [s for s in stats if s["qps_avg"] > 0]
    if not qps_valid:
        print("所有实例均无 QPS 数据，请检查：时间范围是否覆盖告警窗口 / MCPORTER_CONFIG 鉴权 / 实例列表")
        sys.exit(2)
    cluster_qps = sum(s["qps_avg"] for s in qps_valid) / len(qps_valid)

    cpu_by_ip = {}
    for s in stats:
        if s["cpu_avg"] > 0:
            cpu_by_ip.setdefault(s["addr"].rsplit(":", 1)[0], s["cpu_avg"])
    cluster_cpu = (sum(cpu_by_ip.values()) / len(cpu_by_ip)) if cpu_by_ip else 0.0

    stats.sort(key=lambda s: -s["qps_avg"])
    total_qps = sum(s["qps_avg"] for s in stats)

    print(f"\n== 全部 {len(stats)} 个实例（按均值QPS降序）==")
    print(f"{'实例':<24}{'均值QPS':>10}{'峰值QPS':>10}{'占比':>8}{'均值CPU':>10}{'峰值CPU':>10}")
    print("-" * 74)
    for s in stats:
        if s["qps_avg"] <= 0 and s["cpu_avg"] <= 0:
            print(f"{s['addr']:<24}{'无数据':>10}")
            continue
        pct = s["qps_avg"] / total_qps * 100 if total_qps else 0
        print(
            f"{s['addr']:<24}{s['qps_avg']:>10.1f}{s['qps_max']:>10.1f}"
            f"{pct:>7.1f}%{s['cpu_avg']:>10.2f}{s['cpu_max']:>10.2f}"
        )

    print("\n== 集群基准 ==")
    print(f"集群平均QPS(实例均值): {cluster_qps:.1f}    集群平均CPU(IP去重): {cluster_cpu:.2f}")

    print(f"\n== TOP {min(top_n, len(stats))} 实例 vs 集群平均 ==")
    print(f"{'实例':<24}{'QPS':>10}{'/集群均值':>10}{'CPU':>8}{'/集群均值':>10}  判定")
    print("-" * 74)
    hot = []
    for s in stats[:top_n]:
        qps_x = s["qps_avg"] / cluster_qps if cluster_qps else 0
        cpu_x = s["cpu_avg"] / cluster_cpu if cluster_cpu else 0
        share = s["qps_avg"] / total_qps * 100 if total_qps else 0
        verdict = ""
        if qps_x >= 3 or share >= 50:
            verdict = "⚠️ 热点候选(QPS+CPU)" if cpu_x >= 3 else "⚠️ 热点候选(QPS)"
            hot.append((s, qps_x, cpu_x, share))
        print(f"{s['addr']:<24}{s['qps_avg']:>10.1f}{qps_x:>9.1f}x" f"{s['cpu_avg']:>8.2f}{cpu_x:>9.1f}x  {verdict}")

    print("\n判定标准：QPS ≥ 集群均值 3x，或单实例占比 ≥ 50% → 热点候选；CPU ≥ 集群均值 3x 为交叉确认信号。")
    if hot:
        print("\n结论：以下实例进入 Step 2（确认热点 Key）：")
        for s, qps_x, cpu_x, share in hot:
            print(
                f"  {s['addr']}  QPS={s['qps_avg']:.0f}({qps_x:.1f}x均值, 占比{share:.0f}%) "
                f"CPU={s['cpu_avg']:.1f}({cpu_x:.1f}x均值)"
            )
    else:
        print("\n结论：TOP N 实例均未达热点标准。请检查：master 列表是否完整、" "时间范围是否覆盖告警窗口（告警前后 ±30 分钟）。")


if __name__ == "__main__":
    main()
