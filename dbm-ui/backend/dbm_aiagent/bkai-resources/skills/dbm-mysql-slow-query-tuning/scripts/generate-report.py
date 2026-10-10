#!/usr/bin/env python3
"""
将慢查询分析结果生成报告（markdown / html）

用法: generate-report.py <cluster_domain> [--start-time <time>] [--end-time <time>] [--format markdown|html]

  --format markdown  生成 markdown 报告（默认，格式参考 references/output-template.md）
  --format html      生成可交互式 HTML 报告（PMM 风格双面板布局）

输入:
  $OUTPUT_DIR/slowlog_<cluster_domain>_body.json     — 慢查询数组
  $OUTPUT_DIR/slowlog_<cluster_domain>_explain.json  — EXPLAIN 结果 map（key 为 query_digest_md5）
  $OUTPUT_DIR/slowlog_<cluster_domain>_schema.json   — 表结构结果 map（key 为 query_digest_md5）
  $OUTPUT_DIR/slowlog_<cluster_domain>_analysis.json — AI 分析结果 {"summary": {...}, "queries": {<digest_md5>: {...}}}（可选）

输出:
  $OUTPUT_DIR/slowlog_<cluster_domain>_report.md     — markdown 报告
  $OUTPUT_DIR/slowlog_<cluster_domain>_report.html   — 可交互式 HTML 报告
"""

import argparse
import json
import os
import sys
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


def load_json(path):
    """加载 JSON 文件"""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Failed to load {path}: {e}", file=sys.stderr)
        return []


def format_number(n):
    """格式化数字，添加千分位分隔符"""
    if isinstance(n, float):
        if n >= 1:
            return f"{n:,.2f}"
        elif n >= 0.01:
            return f"{n:.3f}"
        else:
            return f"{n:.4f}"
    if isinstance(n, int):
        return f"{n:,}"
    return str(n)


def format_duration(seconds):
    """将秒数格式化为可读时间"""
    if seconds < 1:
        return f"{seconds*1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    elif seconds < 3600:
        return f"{seconds/60:.1f} min"
    else:
        return f"{seconds/3600:.1f} h"


def severity_class(query_time_max, rows_examined_max):
    """根据查询耗时和扫描行数判断严重等级"""
    if query_time_max >= 10 or rows_examined_max >= 1000000:
        return "critical"
    elif query_time_max >= 3 or rows_examined_max >= 100000:
        return "warning"
    return "normal"


def normalize_analysis(analysis_results):
    """归一化 AI 分析结果，返回 (summary, by_digest)

    兼容新格式 {"summary": {...}, "queries": {<md5>: {...}}}
    以及旧格式 [{"query_digest_md5": ..., ...}, ...]
    """
    analysis_summary = {}
    analysis_by_digest = {}
    raw_queries = None
    if isinstance(analysis_results, dict):
        analysis_summary = analysis_results.get("summary", {})
        raw_queries = analysis_results.get("queries", {})
    elif isinstance(analysis_results, list):
        raw_queries = analysis_results

    if isinstance(raw_queries, dict):
        analysis_by_digest = raw_queries
    elif isinstance(raw_queries, list):
        for q in raw_queries:
            if isinstance(q, dict):
                md5 = q.get("query_digest_md5")
                if md5:
                    analysis_by_digest[md5] = q
    return analysis_summary, analysis_by_digest


def parse_explain_rows(explain_data):
    """从 explain mcp 响应中解析出 EXPLAIN 行列表"""
    explain_rows = []
    explain_body = explain_data.get("response_body", {}).get("data", {})
    if isinstance(explain_body, dict):
        explain_result = explain_body.get("explain_result", [])
        if isinstance(explain_result, dict):
            explain_list = [explain_result]
        elif isinstance(explain_result, list):
            explain_list = explain_result
        else:
            explain_list = []
        for row in explain_list:
            if isinstance(row, dict):
                explain_rows.append(
                    {
                        "id": row.get("id", ""),
                        "select_type": row.get("select_type", ""),
                        "table": row.get("table", ""),
                        "partitions": row.get("partitions", ""),
                        "type": row.get("type", ""),
                        "possible_keys": row.get("possible_keys", ""),
                        "key": row.get("key", ""),
                        "key_len": row.get("key_len", ""),
                        "ref": row.get("ref", ""),
                        "rows": row.get("rows", ""),
                        "filtered": row.get("filtered", ""),
                        "Extra": row.get("Extra", ""),
                    }
                )
    return explain_rows


def parse_schema_sqls(schema_data):
    """从 show create table mcp 响应中解析出建表语句列表"""
    schema_sqls = []
    resp_body = schema_data.get("response_body", {})
    schema_body = resp_body.get("data", {}) if isinstance(resp_body, dict) else {}

    if isinstance(schema_body, list):
        for t in schema_body:
            if isinstance(t, dict):
                create_sql_field = t.get("create_sql", "")
                if isinstance(create_sql_field, dict):
                    create_sql = create_sql_field.get("create_sql", "")
                else:
                    create_sql = str(create_sql_field)
                if create_sql:
                    schema_sqls.append(create_sql)
    elif isinstance(schema_body, dict):
        tables = schema_body.get("tables_info", schema_body.get("tables", []))
        if isinstance(tables, list):
            for t in tables:
                if isinstance(t, dict):
                    create_sql_field = t.get("create_table", t.get("create_sql", ""))
                    if isinstance(create_sql_field, dict):
                        create_sql = create_sql_field.get("create_sql", "")
                    else:
                        create_sql = str(create_sql_field)
                    if create_sql:
                        schema_sqls.append(create_sql)
    elif isinstance(schema_body, str) and schema_body:
        schema_sqls.append(schema_body)
    return schema_sqls


def get_explain_data(explain_results, digest_md5, i):
    """按 digest_md5(dict) 或索引(list) 取 explain 数据"""
    if isinstance(explain_results, dict):
        return explain_results.get(digest_md5, {})
    if isinstance(explain_results, list):
        return explain_results[i] if i < len(explain_results) else {}
    return {}


def get_schema_data(schema_results, digest_md5, i):
    """按 digest_md5(dict) 或索引(list) 取 schema 数据"""
    if isinstance(schema_results, dict):
        return schema_results.get(digest_md5, {})
    if isinstance(schema_results, list):
        return schema_results[i] if i < len(schema_results) else {}
    return {}


def generate_html(
    domain, slow_logs, explain_results, schema_results, analysis_results=None, start_time="", end_time=""
):
    """生成完整的 HTML 报告（PMM 双面板风格）"""
    analysis_summary, analysis_by_digest = normalize_analysis(analysis_results)

    count = len(slow_logs)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 统计摘要
    total_query_time = sum(e.get("query_time_sum", 0) for e in slow_logs)
    total_rows_examined = sum(e.get("rows_examined_sum", 0) for e in slow_logs)
    total_count = sum(e.get("count_star", 0) for e in slow_logs)
    critical_count = sum(
        1 for e in slow_logs if severity_class(e.get("query_time_max", 0), e.get("rows_examined_max", 0)) == "critical"
    )
    warning_count = sum(
        1 for e in slow_logs if severity_class(e.get("query_time_max", 0), e.get("rows_examined_max", 0)) == "warning"
    )
    normal_count = count - critical_count - warning_count

    # 构建表格行数据（JSON），传递给前端
    table_data = []
    for i, entry in enumerate(slow_logs):
        query_time_max = entry.get("query_time_max", 0)
        query_time_sum = entry.get("query_time_sum", 0)
        rows_examined_max = entry.get("rows_examined_max", 0)
        rows_examined_sum = entry.get("rows_examined_sum", 0)
        count_star = entry.get("count_star", 0)
        severity = severity_class(query_time_max, rows_examined_max)

        # 计算负载占比（用于迷你条形图）
        load_pct = (query_time_sum / total_query_time * 100) if total_query_time > 0 else 0
        rows_pct = (rows_examined_sum / total_rows_examined * 100) if total_rows_examined > 0 else 0

        table_data.append(
            {
                "idx": i,
                "severity": severity,
                "digest_md5": entry.get("query_digest_md5", f"unknown_{i}"),
                "query_digest_text": entry.get("query_digest_text", entry.get("query_string", "")),
                "query_string": entry.get("query_string", ""),
                "query_time_max": query_time_max,
                "query_time_sum": query_time_sum,
                "query_time_avg": query_time_sum / count_star if count_star > 0 else 0,
                "rows_examined_max": rows_examined_max,
                "rows_examined_sum": rows_examined_sum,
                "rows_examined_avg": rows_examined_sum / count_star if count_star > 0 else 0,
                "rows_sent_sum": entry.get("rows_sent_sum", 0),
                "count_star": count_star,
                "load_pct": load_pct,
                "rows_pct": rows_pct,
                "username": entry.get("username", ""),
                "query_db_name": entry.get("query_db_name", ""),
                "table_names": entry.get("table_names", ""),
                "instance_host": entry.get("instance_host", ""),
                "instance_port": entry.get("instance_port", ""),
                "client_host": entry.get("client_host", ""),
                "time_window_min": entry.get("time_window_min", ""),
                "time_window_max": entry.get("time_window_max", entry.get("time_window_min", "")),
                "lock_time_max": entry.get("lock_time_max", 0),
                "lock_time_sum": entry.get("lock_time_sum", 0),
            }
        )

    # 按 load_pct 降序排序，使序号代表 Load 排名
    table_data.sort(key=lambda x: x["load_pct"], reverse=True)
    for i, row in enumerate(table_data):
        row["idx"] = i

    # 构建详情数据 JSON（以 digest_md5 为 key 的字典，方便前端按 md5 关联）
    # explain_results / schema_results 可能是 dict（key=digest_md5）或 list
    detail_data = {}
    for i, entry in enumerate(slow_logs):
        digest_md5 = entry.get("query_digest_md5", f"unknown_{i}")
        explain_data = get_explain_data(explain_results, digest_md5, i)
        schema_data = get_schema_data(schema_results, digest_md5, i)
        # analysis_by_digest 以 digest_md5 为 key，直接按 md5 关联
        analysis_data = analysis_by_digest.get(digest_md5, {})

        explain_rows = parse_explain_rows(explain_data)
        schema_sqls = parse_schema_sqls(schema_data)

        detail_data[digest_md5] = {
            "explain_rows": explain_rows,
            "schema_sqls": schema_sqls,
            "analysis": analysis_data,
        }

    # 将数据序列化为 JSON 嵌入 HTML
    table_data_json = json.dumps(table_data, ensure_ascii=False)
    detail_data_json = json.dumps(detail_data, ensure_ascii=False)
    summary_data_json = json.dumps(analysis_summary, ensure_ascii=False)

    # 加载 Jinja2 模板并渲染
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env = Environment(
        loader=FileSystemLoader(script_dir),
        autoescape=True,
    )
    template = env.get_template("report-template.html.jinja")
    return template.render(
        domain=domain,
        start_time=start_time,
        end_time=end_time,
        now=now,
        count=count,
        critical_count=critical_count,
        warning_count=warning_count,
        normal_count=normal_count,
        total_query_time_formatted=format_duration(total_query_time),
        total_rows_examined_formatted=format_number(total_rows_examined),
        total_count_formatted=format_number(total_count),
        total_query_time=total_query_time,
        total_rows_examined=total_rows_examined,
        total_count=total_count,
        table_data_json=table_data_json,
        detail_data_json=detail_data_json,
        summary_data_json=summary_data_json,
    )


def _render_summary_md(summary):
    """将 AI 综合总结渲染为 markdown"""
    if not isinstance(summary, dict) or not summary:
        return "_（无 AI 综合总结）_\n"
    lines = []
    most_urgent = summary.get("most_urgent")
    root_cause = summary.get("root_cause_summary")
    key_findings = summary.get("key_findings")
    action_priority = summary.get("action_priority")
    if most_urgent:
        lines.append(f"- **最紧急问题**：{most_urgent}")
    if root_cause:
        lines.append(f"- **综合根因**：{root_cause}")
    if isinstance(key_findings, list) and key_findings:
        lines.append("- **关键发现**：")
        for f in key_findings:
            lines.append(f"  - {f}")
    if action_priority:
        lines.append(f"- **处理优先级**：{action_priority}")
    return "\n".join(lines) + "\n" if lines else "_（无 AI 综合总结）_\n"


def generate_markdown(
    domain, slow_logs, explain_results, schema_results, analysis_results=None, start_time="", end_time=""
):
    """生成 markdown 报告，格式参考 references/output-template.md"""
    analysis_summary, analysis_by_digest = normalize_analysis(analysis_results)

    out = []
    out.append(f"## 慢查询分析：{domain}\n")
    out.append(f"采集时间：{start_time} ~ {end_time}\n")
    out.append("### 总结\n")
    out.append(_render_summary_md(analysis_summary))

    for i, entry in enumerate(slow_logs):
        digest_md5 = entry.get("query_digest_md5", f"unknown_{i}")
        explain_data = get_explain_data(explain_results, digest_md5, i)
        schema_data = get_schema_data(schema_results, digest_md5, i)
        analysis_data = analysis_by_digest.get(digest_md5, {})

        explain_rows = parse_explain_rows(explain_data)
        schema_sqls = parse_schema_sqls(schema_data)

        username = entry.get("username", "")
        client_host = entry.get("client_host", "")
        count_star = entry.get("count_star", 0)
        query_time_max = entry.get("query_time_max", 0)
        rows_examined_max = entry.get("rows_examined_max", 0)
        rows_examined_sum = entry.get("rows_examined_sum", 0)
        rows_sent_max = entry.get("rows_sent_max", 0)
        table_names = entry.get("table_names", "")
        time_window_min = entry.get("time_window_min", "")
        query_digest_text = entry.get("query_digest_text", entry.get("query_string", ""))

        out.append(f"### SQL #{i+1} ({digest_md5})\n")
        user_info = f"用户名: {username}"
        if client_host:
            user_info += f" | 客户端来源: {client_host}"
        user_info += f" (出现次数: {count_star})\n"
        out.append(user_info)
        out.append("| 查询耗时 | 扫描行数 | 总扫描行数 | 返回行数 | 库表名 | 首次时间 |")
        out.append("|---------|---------|---------|---------|--------|----------|")
        out.append(
            f"| {format_duration(query_time_max)} | {format_number(rows_examined_max)} | "
            f"{format_number(rows_examined_sum)} | {format_number(rows_sent_max)} | "
            f"{table_names} | {time_window_min} |\n"
        )

        out.append("**SQL 指纹**: ")
        out.append("```sql")
        out.append(query_digest_text)
        out.append("```\n")

        out.append("**表结构**：")
        out.append("```sql")
        if schema_sqls:
            out.append("\n\n".join(s.strip() for s in schema_sqls))
        else:
            out.append("-- （无表结构信息）")
        out.append("```\n")

        out.append("**EXPLAIN**：")
        out.append("| select_type | type | key | rows | filtered | Extra |")
        out.append("|---|---|---|---|---|---|")
        if explain_rows:
            for r in explain_rows:
                out.append(
                    f"| {r.get('select_type','')} | {r.get('type','')} | {r.get('key','')} | "
                    f"{r.get('rows','')} | {r.get('filtered','')} | {r.get('Extra','')} |"
                )
        else:
            out.append("| - | - | - | - | - | - |")
        out.append("")

        out.append("**优化建议**：")
        problem = analysis_data.get("problem") if isinstance(analysis_data, dict) else None
        root_cause = analysis_data.get("root_cause") if isinstance(analysis_data, dict) else None
        suggestions = analysis_data.get("suggestions") if isinstance(analysis_data, dict) else None
        if problem:
            out.append(f"- 问题：{problem}")
        if root_cause:
            out.append(f"- 根因：{root_cause}")
        if isinstance(suggestions, list) and suggestions:
            for s in suggestions:
                out.append(f"- {s}")
        elif not problem and not root_cause:
            out.append("- （无 AI 优化建议）")
        out.append("")
        out.append("---\n")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="生成慢查询分析报告（markdown / html）")
    parser.add_argument("cluster_domain", help="集群域名")
    parser.add_argument("--start-time", default="", help="采集开始时间")
    parser.add_argument("--end-time", default="", help="采集结束时间")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown", help="报告格式，默认 markdown")
    args = parser.parse_args()

    domain = args.cluster_domain
    fmt = args.format
    output_dir = os.environ.get("OUTPUT_DIR", "/app/.storage/session")
    slow_file = os.path.join(output_dir, f"slowlog_{domain}_body.json")
    explain_file = os.path.join(output_dir, f"slowlog_{domain}_explain.json")
    schema_file = os.path.join(output_dir, f"slowlog_{domain}_schema.json")
    analysis_file = os.path.join(output_dir, f"slowlog_{domain}_analysis.json")
    ext = "html" if fmt == "html" else "md"
    output_file = os.path.join(output_dir, f"slowlog_{domain}_report.{ext}")

    # 加载数据
    slow_logs = load_json(slow_file)
    explain_results = load_json(explain_file)
    schema_results = load_json(schema_file)
    analysis_results = load_json(analysis_file)  # AI 分析结果（可选）

    if not slow_logs:
        print(f"[ERROR] No slow logs found in {slow_file}", file=sys.stderr)
        sys.exit(1)

    print(f"生成 {fmt} 报告: {len(slow_logs)} 条慢查询...")
    if isinstance(analysis_results, dict):
        queries = analysis_results.get("queries", {})
        has_summary = bool(analysis_results.get("summary"))
        print(f"  - 包含 {len(queries)} 条 AI 分析结果" + (" + 综合总结" if has_summary else ""))
    elif isinstance(analysis_results, list) and analysis_results:
        print(f"  - 包含 {len(analysis_results)} 条 AI 分析结果（旧格式）")
    else:
        print(f"  - 未找到 AI 分析结果 ({analysis_file})，报告中将不包含 AI 诊断")

    # 生成报告
    if fmt == "html":
        content = generate_html(
            domain,
            slow_logs,
            explain_results,
            schema_results,
            analysis_results=analysis_results,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    else:
        content = generate_markdown(
            domain,
            slow_logs,
            explain_results,
            schema_results,
            analysis_results=analysis_results,
            start_time=args.start_time,
            end_time=args.end_time,
        )

    # 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ {fmt} 报告已生成: {output_file}")
    if fmt == "html":
        print(f"   可使用浏览器打开: open {output_file}")


if __name__ == "__main__":
    main()
