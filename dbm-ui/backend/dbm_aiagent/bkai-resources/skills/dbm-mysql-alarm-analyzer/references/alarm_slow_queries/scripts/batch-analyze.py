#!/usr/bin/env python3
"""
串行对每条慢查询执行 EXPLAIN + SHOW CREATE TABLE

用法: batch-analyze.py <cluster_domain>

输入: $OUTPUT_DIR/slowlog_<cluster_domain>_body.json  (慢查询数组, 已提取 slow_logs)
输出:
  $OUTPUT_DIR/slowlog_<cluster_domain>_explain.json  — EXPLAIN 结果数组 (每项含 query_digest_md5)
  $OUTPUT_DIR/slowlog_<cluster_domain>_schema.json   — 表结构结果数组 (每项含 query_digest_md5)
"""

import json
import os
import subprocess
import sys
import tempfile


def mcp_call(tool: str, body: dict, req_file: str) -> dict:
    """调用 dbm-mcp-cli, body 写入临时文件通过 body_param=@file 传递"""
    with open(req_file, "w") as f:
        json.dump(body, f, ensure_ascii=False)

    try:
        result = subprocess.run(
            ["dbm-mcp-cli", "call", tool, f"body_param=@{req_file}"], capture_output=True, text=True, timeout=60
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        elif result.stderr.strip():
            raise Exception(result.stderr)
        else:
            return {"error": result.stderr or "empty response"}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except (json.JSONDecodeError, Exception) as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("用法: batch-analyze.py <cluster_domain>", file=sys.stderr)
        sys.exit(1)

    domain = sys.argv[1]
    output_dir = os.environ.get("OUTPUT_DIR", "/app/.storage/session")
    os.makedirs(output_dir, exist_ok=True)
    slow_result_file = os.path.join(output_dir, f"slowlog_{domain}_body.json")
    explain_output = os.path.join(output_dir, f"slowlog_{domain}_explain.json")
    schema_output = os.path.join(output_dir, f"slowlog_{domain}_schema.json")
    tmp_dir = os.path.join(output_dir, f"slowlog_work_{domain}")

    os.makedirs(tmp_dir, exist_ok=True)

    with open(slow_result_file, "r") as f:
        slow_logs = json.load(f)

    count = len(slow_logs)
    print(f"开始获取慢查询的 table schema 和 explain 信息 [total sql: {count}] ...")

    explain_results = []
    schema_results = []

    for i, entry in enumerate(slow_logs):
        digest_md5 = entry.get("query_digest_md5", f"unknown_{i}")
        print(f"[{i+1}/{count}] digest={digest_md5}")

        # 即使某条异常，也要保证 explain_results/schema_results 与 slow_logs 下标一致
        schema_resp = {"error": "skipped", "query_digest_md5": digest_md5, "response_body": {}}
        explain_resp = {"error": "skipped", "query_digest_md5": digest_md5, "response_body": {}}

        try:
            db = entry["query_db_name"]
            table_names = entry["table_names"]  # "db1.table1,db2.table2"
            query_sql = entry["query_string"]

            # --- SHOW CREATE TABLE ---
            schema_req = os.path.join(tmp_dir, f"schema_req_{digest_md5}.json")
            schema_body = {"cluster_domain": domain, "db_name": db, "table_names": table_names.split(",")}
            schema_resp = mcp_call(
                "bkdbm-mcp-prod-mysql-query.mysql_query_show_create_tables", schema_body, schema_req
            )
            schema_resp["query_digest_md5"] = digest_md5
        except Exception as e:
            print(f"  [WARN] schema failed for {digest_md5}: {e}", file=sys.stderr)
            schema_resp["error"] = str(e)

        try:
            db = entry["query_db_name"]
            query_sql = entry["query_string"]

            # --- EXPLAIN ---
            explain_req = os.path.join(tmp_dir, f"explain_req_{digest_md5}.json")
            explain_body = {"cluster_domain": domain, "db_name": db, "query_sql": query_sql}
            explain_resp = mcp_call("bkdbm-mcp-prod-mysql-query.mysql_query_explain_sql", explain_body, explain_req)
            explain_resp["query_digest_md5"] = digest_md5
        except Exception as e:
            print(f"  [WARN] explain failed for {digest_md5}: {e}", file=sys.stderr)
            explain_resp["error"] = str(e)

        # 节省一点上下文
        try:
            schema_resp.pop("request_id", None)
            schema_resp.pop("status_code", None)
            schema_resp["response_body"].pop("request_id", None)
            schema_resp["response_body"].pop("result", None)
            explain_resp.pop("request_id", None)
            explain_resp.pop("status_code", None)
            explain_resp["response_body"].pop("request_id", None)
            explain_resp["response_body"].pop("result", None)
        except Exception as e:
            pass

        schema_results.append(schema_resp)
        explain_results.append(explain_resp)

    # 写入结果
    with open(explain_output, "w") as f:
        json.dump(explain_results, f, ensure_ascii=False, indent=2)

    with open(schema_output, "w") as f:
        json.dump(schema_results, f, ensure_ascii=False, indent=2)

    print(f"EXPLAIN results ({count} entries): {explain_output}")
    print(f"Schema results ({count} entries): {schema_output}")


if __name__ == "__main__":
    main()
