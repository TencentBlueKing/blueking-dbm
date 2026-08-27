# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

解析 dbactuator SQL 导入 OutputCtx（<ctx>...</ctx>），按 单据号×集群×库×SQL文件 落库
db_report.models.MysqlSqlFileExecDuration。与 sql_exec_duration_recorder（单条 SQL 审计）分开。
sql_file_path 由流程 global_data.path 与文件名拼接为 BKRepo 对象路径。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Iterable, List, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.components import JobApi
from backend.db_report.models import MysqlSqlFileExecDuration
from backend.flow.utils.bk_job_record import _as_positive_int, try_resolve_cluster_id, try_resolve_step_instance_id

logger = logging.getLogger("flow")

CTX_RE = re.compile(r"<ctx>(?P<context>.+?)</ctx>")


def parse_sql_file_exec_ctx(log_content: str) -> List[dict]:
    """解析 actuator OutputCtx：{"3306":[{"sql_file","db_name","duration","success"}]}。"""
    if not log_content:
        return []
    matched = CTX_RE.search(log_content)
    if not matched:
        logger.warning(_("作业日志无 <ctx> len={}").format(len(log_content)))
        return []
    ctx = matched.group("context")
    try:
        raw = json.loads(ctx)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning(_("解析SQL文件执行耗时 <ctx> JSON失败: {} ctx={}").format(str(exc), ctx[:200]))
        return []
    if not isinstance(raw, dict):
        logger.warning(_("解析SQL文件执行耗时 <ctx> 非对象: {}").format(type(raw).__name__))
        return []
    rows = _flatten_port_items(raw)
    if not rows:
        logger.warning(_("解析SQL文件执行耗时: <ctx> 无有效的文件×库记录"))
    return rows


def join_sql_file_path(repo_dir: str, sql_file: str) -> str:
    """拼 BKRepo 对象路径：mysql/sqlfile/{biz}/foo.sql。两侧斜杠会去掉。"""
    base = str(repo_dir or "").strip().strip("/")
    name = str(sql_file or "").strip()
    if not base or not name:
        return ""
    return f"{base}/{name}"


def record_sql_file_exec_durations(*, data, fetch_ip_log: Optional[Callable[[dict], Any]] = None) -> int:
    """
    作业成功后入库。单据号或 cluster_id 缺失则跳过。
    fetch_ip_log(ip_dict) 返回 JobApi.get_job_instance_ip_log 风格 dict；缺省时按 outputs 拉作业日志。
    """
    ticket_id, cluster_id, root_id, repo_dir, ip_dicts = _resolve_record_keys(data)
    if ticket_id is None or cluster_id is None:
        return 0
    if not ip_dicts:
        logger.error(_("记录SQL文件执行耗时跳过: 执行IP为空 ticket_id={}").format(ticket_id))
        return 0
    if not repo_dir:
        logger.error(_("记录SQL文件执行耗时: 制品库目录缺失 ticket_id={}").format(ticket_id))

    fetcher = fetch_ip_log or _build_fetch_ip_log(data)
    if fetcher is None:
        return 0

    cluster_domain = _resolve_cluster_domain(cluster_id)
    objs = _collect_duration_objs(
        fetch_ip_log=fetcher,
        ip_dicts=ip_dicts,
        ticket_id=ticket_id,
        cluster_id=cluster_id,
        cluster_domain=cluster_domain,
        root_id=root_id,
        repo_dir=repo_dir,
    )
    if not objs:
        logger.info(_("记录SQL文件执行耗时: 无可入库记录 ticket_id={} cluster_id={}").format(ticket_id, cluster_id))
        return 0
    MysqlSqlFileExecDuration.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)


def _resolve_record_keys(data) -> tuple:
    global_data = data.get_one_of_inputs("global_data") or {}
    kwargs = data.get_one_of_inputs("kwargs") or {}
    if not isinstance(global_data, dict):
        global_data = {}
    if not isinstance(kwargs, dict):
        kwargs = {}
    ticket_id = _as_positive_int(global_data.get("uid"))
    if ticket_id is None:
        logger.error(_("记录SQL文件执行耗时跳过: 单据号缺失"))
        return None, None, "", "", []
    cluster_id = try_resolve_cluster_id(kwargs, global_data)
    if not cluster_id:
        logger.error(_("记录SQL文件执行耗时跳过: cluster_id 缺失 ticket_id={}").format(ticket_id))
        return ticket_id, None, "", "", []
    root_id = str(kwargs.get("root_id") or "")
    repo_dir = str(global_data.get("path") or "").strip()
    ip_dicts = _normalize_exec_ip_dicts(data.get_one_of_outputs("exec_ips"), kwargs.get("bk_cloud_id"))
    return ticket_id, cluster_id, root_id, repo_dir, ip_dicts


def _normalize_exec_ip_dicts(exec_ips: Any, bk_cloud_id: Any) -> List[dict]:
    if not exec_ips:
        return []
    ip_dicts: List[dict] = []
    for item in exec_ips:
        if isinstance(item, dict) and item.get("ip") is not None:
            cloud_id = item.get("bk_cloud_id", bk_cloud_id if bk_cloud_id is not None else 0)
            ip_dicts.append({"ip": item["ip"], "bk_cloud_id": cloud_id})
        elif isinstance(item, str) and item:
            ip_dicts.append({"ip": item, "bk_cloud_id": bk_cloud_id if bk_cloud_id is not None else 0})
    return ip_dicts


def _resolve_cluster_domain(cluster_id: int) -> str:
    try:
        from backend.db_meta.models import Cluster

        domain = Cluster.objects.filter(id=cluster_id).values_list("immute_domain", flat=True).first()
        return domain or ""
    except Exception as exc:
        logger.warning(_("查询集群域名失败 cluster_id={}: {}").format(cluster_id, str(exc)))
        return ""


def _flatten_port_items(raw: dict) -> List[dict]:
    rows: List[dict] = []
    for port_key, items in raw.items():
        port = _as_positive_int(port_key)
        if port is None or not isinstance(items, list):
            continue
        for item in items:
            row = _normalize_ctx_item(port, item)
            if row:
                rows.append(row)
    return rows


def _normalize_ctx_item(port: int, item: Any) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    sql_file = str(item.get("sql_file") or "").strip()
    db_name = str(item.get("db_name") or "").strip()
    if not sql_file or not db_name:
        return None
    try:
        duration_sec = int(item.get("duration"))
    except (TypeError, ValueError):
        return None
    return {
        "port": port,
        "sql_file": sql_file,
        "db_name": db_name,
        "duration_sec": duration_sec,
        "success": bool(item.get("success", False)),
    }


def _collect_duration_objs(
    *,
    fetch_ip_log: Callable[[dict], Any],
    ip_dicts: Iterable[dict],
    ticket_id: int,
    cluster_id: int,
    cluster_domain: str,
    root_id: str,
    repo_dir: str,
) -> List[MysqlSqlFileExecDuration]:
    objs: List[MysqlSqlFileExecDuration] = []
    seen = set()
    for ip_dict in ip_dicts:
        ip = str(ip_dict.get("ip") or "")
        log_content = _fetch_ip_log_content(fetch_ip_log, ip_dict)
        for row in parse_sql_file_exec_ctx(log_content):
            key = (ticket_id, cluster_id, row["db_name"], row["sql_file"])
            if key in seen:
                continue
            seen.add(key)
            objs.append(
                MysqlSqlFileExecDuration(
                    ticket_id=ticket_id,
                    cluster_id=cluster_id,
                    cluster_domain=cluster_domain,
                    db_name=row["db_name"],
                    sql_file=row["sql_file"],
                    sql_file_path=join_sql_file_path(repo_dir, row["sql_file"]),
                    duration_sec=row["duration_sec"],
                    success=row["success"],
                    root_id=root_id,
                    ip=ip,
                    port=row["port"],
                )
            )
    return objs


def _fetch_ip_log_content(fetch_ip_log: Callable[[dict], Any], ip_dict: dict) -> str:
    ip = str(ip_dict.get("ip") or "")
    try:
        resp = fetch_ip_log(ip_dict)
    except Exception as exc:
        logger.warning(_("拉取作业日志失败 ip={}: {}").format(ip, str(exc)))
        return ""
    log_content = _extract_log_content(resp)
    if not (isinstance(resp, dict) and resp.get("result")):
        logger.warning(_("拉取作业日志失败 ip={}: {}").format(ip, resp))
        return ""
    if not log_content:
        logger.warning(_("作业日志为空 ip={}").format(ip))
        return ""
    return log_content


def _extract_log_content(resp: Any) -> str:
    if not isinstance(resp, dict) or not resp.get("result"):
        return ""
    data = resp.get("data")
    if not isinstance(data, dict):
        return ""
    return data.get("log_content") or ""


def _build_fetch_ip_log(data) -> Optional[Callable[[dict], Any]]:
    ext_result = data.get_one_of_outputs("ext_result")
    if not (isinstance(ext_result, dict) and isinstance(ext_result.get("data"), dict)):
        logger.error(_("记录SQL文件执行耗时跳过: ext_result 缺失"))
        return None
    raw_id = ext_result["data"].get("job_instance_id")
    if raw_id is None:
        logger.error(_("记录SQL文件执行耗时跳过: job_instance_id 缺失"))
        return None
    job_instance_id = int(raw_id)
    step_instance_id = try_resolve_step_instance_id(ext_result, job_instance_id)
    if step_instance_id is None:
        logger.error(_("记录SQL文件执行耗时跳过: step_instance_id 缺失 job_instance_id={}").format(job_instance_id))
        return None

    def _fetch(ip_dict: dict):
        payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
        }
        return JobApi.get_job_instance_ip_log({**payload, **ip_dict}, raw=True)

    return _fetch
