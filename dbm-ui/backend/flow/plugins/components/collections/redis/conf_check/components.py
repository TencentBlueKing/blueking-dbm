# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import datetime
import json
import logging
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend import env
from backend.components import DRSApi, JobApi
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_daily_cluster_rows
from backend.flow.consts import SUCCESS_LIST
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.payload_handler import DEFAULT_REDIS_PASSWORD_BATCH_SIZE, PayloadHandler
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter
from backend.flow.utils.redis.redis_script_template import (
    CONF_CHECK_SCRIPT_HEADER,
    redis_fast_execute_script_common_kwargs,
)
from backend.utils.string import base64_encode

from .base import CheckTarget
from .errors import format_password_drs_error, mark_host_targets
from .password_cache import get_cached_cluster_passwords, put_cached_cluster_passwords
from .redis_candidates import (
    REDIS_CONF_CHECK_CANDIDATES_TTL,
    delete_candidates_key,
    renew_candidates_key_ttl,
    slice_candidate_cluster_ids,
)
from .registry import CHECKER_REGISTRY

logger = logging.getLogger("flow")

# <CONFCHK checker="predixy_servers" port="50000">{json}</CONFCHK>
CONFCHK_PATTERN = re.compile(
    r'<CONFCHK\s+checker="(?P<checker>[^"]+)"\s+port="(?P<port>\d+)">(?P<body>.*?)</CONFCHK>', re.DOTALL
)

MAX_WORKERS = getattr(settings, "CONCURRENT_NUMBER", 10)
DEFAULT_DRS_GROUP_CHUNK_SIZE = 20
DEFAULT_DRS_CHUNKS_PER_TICK = 1
DEFAULT_POLL_INTERVAL = 5  # seconds
DEFAULT_POLL_MAX_RETRIES = 120  # default timeout = interval * max_retries = 10min

PHASE_POLL_JOBS = "poll_jobs"
PHASE_RUN_DRS = "run_drs"
PHASE_EVALUATE = "evaluate"
PHASE_BATCH_DELAY = "batch_delay"

# All conf-check findings (role mismatch, predixy fail/drift) share one subtype.
CONF_CHECK_SUBTYPE = RedisCheckSubType.ConfigInconsistent.value


def _checkers_for(cluster_type: str):
    return [c for c in CHECKER_REGISTRY if c.applies_to(cluster_type)]


def _checker_by_name(checker_name: str):
    for checker in CHECKER_REGISTRY:
        if checker.name == checker_name:
            return checker
    return None


def _chunks(items: List, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _load_batch_clusters(clusters: List[Dict]) -> Dict[int, Cluster]:
    cluster_ids = [info["cluster_id"] for info in clusters]
    storage_qs = StorageInstance.objects.select_related("machine")
    proxy_qs = ProxyInstance.objects.select_related("machine")
    return {
        cluster.id: cluster
        for cluster in Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
            Prefetch("storageinstance_set", queryset=storage_qs),
            Prefetch("proxyinstance_set", queryset=proxy_qs),
        )
    }


def _resolve_batch_clusters(kwargs: Dict) -> List[Dict]:
    """Load this act's cluster slice from Redis (renew TTL) or return empty list."""
    candidates_key = kwargs.get("candidates_key")
    batch_num = int(kwargs.get("batch_num") or 0)
    batch_size = int(kwargs.get("batch_size") or 0)
    if not candidates_key or batch_num < 1 or batch_size < 1:
        return []

    renew_candidates_key_ttl(candidates_key, REDIS_CONF_CHECK_CANDIDATES_TTL)
    cluster_ids = slice_candidate_cluster_ids(candidates_key, batch_num, batch_size)
    if not cluster_ids:
        return []

    rows = Cluster.objects.filter(id__in=cluster_ids).values("id", "bk_cloud_id")
    id_to_cloud = {row["id"]: row["bk_cloud_id"] for row in rows}
    clusters = []
    for cluster_id in cluster_ids:
        if cluster_id not in id_to_cloud:
            logger.warning("conf_check cluster %s not found in meta, skipping", cluster_id)
            continue
        clusters.append({"cluster_id": cluster_id, "bk_cloud_id": id_to_cloud[cluster_id]})
    return clusters


def _target_to_info(cluster: Cluster, checker, target: CheckTarget) -> Dict:
    return {
        "cluster_id": cluster.id,
        "cluster": cluster.immute_domain,
        "cluster_type": cluster.cluster_type,
        "bk_biz_id": cluster.bk_biz_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "checker": checker.name,
        "target_bk_cloud_id": target.bk_cloud_id,
        "ip": target.ip,
        "port": target.port,
        "extra": target.extra,
    }


def _target_from_info(target_info: Dict) -> CheckTarget:
    return CheckTarget(
        cluster_id=target_info["cluster_id"],
        bk_cloud_id=target_info.get("target_bk_cloud_id", target_info["bk_cloud_id"]),
        ip=target_info["ip"],
        port=target_info["port"],
        extra=target_info.get("extra", {}) or {},
    )


def _build_target_infos(clusters: List[Dict]) -> Tuple[List[Dict], Dict]:
    cluster_map = _load_batch_clusters(clusters)
    target_infos = []
    metrics = {
        "cluster_count": len(cluster_map),
        "checker_target_collect_calls": 0,
        "target_count": 0,
    }
    for cluster_info in clusters:
        cluster = cluster_map.get(cluster_info["cluster_id"])
        if cluster is None:
            continue
        for checker in _checkers_for(cluster.cluster_type):
            metrics["checker_target_collect_calls"] += 1
            for target in checker.collect_targets(cluster):
                target_infos.append(_target_to_info(cluster, checker, target))
    metrics["target_count"] = len(target_infos)
    return target_infos, metrics


def _build_host_map(target_infos: List[Dict]) -> Dict[Tuple[int, str], Dict]:
    """host_key (bk_cloud_id, ip) -> {"snippets": [...], "conf_targets": [...]}"""
    host_map: Dict[Tuple[int, str], Dict] = {}
    checker_targets_by_host: Dict[Tuple[str, int, str], List[CheckTarget]] = defaultdict(list)
    for target_info in target_infos:
        checker = _checker_by_name(target_info["checker"])
        if checker is None or not checker.requires_host_script:
            continue
        target = _target_from_info(target_info)
        checker_targets_by_host[(checker.name, target.bk_cloud_id, target.ip)].append(target)

    for (checker_name, bk_cloud_id, ip), host_targets in checker_targets_by_host.items():
        checker = _checker_by_name(checker_name)
        if checker is None:
            continue
        snippet = checker.host_script_snippet(host_targets)
        if not snippet:
            continue
        entry = host_map.setdefault((bk_cloud_id, ip), {"snippets": [], "conf_targets": []})
        entry["snippets"].append(snippet)
        for target in host_targets:
            entry["conf_targets"].append(
                {"checker": checker.name, "port": target.port, "cluster_id": target.cluster_id}
            )
    return host_map


def _fast_execute_script(
    script_content: str, exec_ip: str, bk_cloud_id: int, flow_id: str, node_name: str
) -> Tuple[Optional[int], Optional[str]]:
    body = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": f"DBM_{flow_id}_{node_name}_{exec_ip}",
        "script_content": base64_encode(script_content),
        "script_language": 1,  # shell
        "target_server": {"ip_list": [{"bk_cloud_id": bk_cloud_id, "ip": exec_ip}]},
    }
    try:
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)
    except Exception as e:
        logger.error(f"conf_check fast_execute_script raised on {exec_ip}: {e}")
        return None, "job_issue_exception: {}".format(e)
    if not resp.get("result") or not resp.get("data"):
        msg = resp.get("message") or "no_data"
        logger.error(f"conf_check fast_execute_script failed on {exec_ip}: {msg}")
        return None, "job_issue_failed: {}".format(msg)
    return resp["data"]["job_instance_id"], None


def _report_row(
    target_info: Dict,
    report_day: int,
    creator: str,
    *,
    state: str,
    msg: str,
    ip: str,
    port: int,
) -> Dict:
    return {
        "cluster_id": target_info["cluster_id"],
        "subtype": CONF_CHECK_SUBTYPE,
        "cluster": target_info["cluster"],
        "cluster_type": target_info["cluster_type"],
        "bk_biz_id": target_info["bk_biz_id"],
        "bk_cloud_id": target_info["bk_cloud_id"],
        "report_day": report_day,
        "creator": creator,
        "state": state,
        "msg": msg,
        "instance": "{}:{}".format(ip, port),
    }


def _issue_host_jobs(
    host_map: Dict[Tuple[int, str], Dict],
    flow_id: str,
    node_name: str,
    log_warning,
    log_error,
    host_conf_data: Dict[Tuple[str, str, int], Dict],
) -> Tuple[List[Dict], int]:
    if not host_map:
        return [], 0

    job_infos = []
    issue_failure_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {}
        for (bk_cloud_id, ip), entry in host_map.items():
            script = CONF_CHECK_SCRIPT_HEADER + "\n".join(entry["snippets"])
            future = executor.submit(_fast_execute_script, script, ip, bk_cloud_id, flow_id, node_name)
            future_map[future] = (bk_cloud_id, ip, entry["conf_targets"])

        for future in as_completed(future_map):
            bk_cloud_id, ip, conf_targets = future_map[future]
            try:
                job_instance_id, issue_reason = future.result()
                if job_instance_id:
                    job_infos.append(
                        {
                            "job_instance_id": job_instance_id,
                            "bk_cloud_id": bk_cloud_id,
                            "exec_ip": ip,
                            "conf_targets": conf_targets,
                        }
                    )
                else:
                    log_warning(_("[{}] 主机 {} 脚本下发失败").format(node_name, ip))
                    mark_host_targets(host_conf_data, ip, conf_targets, issue_reason or "job_issue_failed")
                    issue_failure_count += 1
            except Exception as e:
                log_error(_("[{}] 主机 {} 脚本下发异常: {}").format(node_name, ip, e))
                mark_host_targets(host_conf_data, ip, conf_targets, "job_issue_exception: {}".format(e))
                issue_failure_count += 1
    return job_infos, issue_failure_count


def _check_job_status(job_instance_id: int) -> Tuple[str, Optional[int]]:
    payload = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "job_instance_id": job_instance_id,
        "return_ip_result": True,
    }
    try:
        resp = JobApi.get_job_instance_status(payload, raw=True)
    except Exception as e:
        logger.error(f"conf_check get_job_instance_status raised for job {job_instance_id}: {e}")
        return "running", None
    if not resp.get("result") or not resp.get("data"):
        logger.warning(
            "conf_check get_job_instance_status no data for job %s: %s",
            job_instance_id,
            resp.get("message"),
        )
        return "running", None
    if not resp["data"]["finished"]:
        return "running", None

    job_status = resp["data"]["job_instance"]["status"]
    step_instance_id = (
        resp["data"]["step_instance_list"][0]["step_instance_id"] if resp["data"]["step_instance_list"] else None
    )
    return ("completed", step_instance_id) if job_status in SUCCESS_LIST else ("failed", step_instance_id)


def _poll_jobs_once(
    pending_jobs: Dict[int, Dict],
    completed_jobs: List[Dict],
    failed_jobs: List[Dict],
) -> Tuple[Dict[int, Dict], List[Dict], List[Dict], int]:
    """One schedule tick of job status polling. Returns (pending, completed, failed, checks_count)."""
    if not pending_jobs:
        return pending_jobs, completed_jobs, failed_jobs, 0

    jobs_to_check = list(pending_jobs.keys())
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_job_id = {executor.submit(_check_job_status, job_id): job_id for job_id in jobs_to_check}
        for future in as_completed(future_to_job_id):
            job_id = future_to_job_id[future]
            try:
                status, step_instance_id = future.result()
                if status == "completed":
                    job_info = pending_jobs.pop(job_id)
                    job_info["step_instance_id"] = step_instance_id
                    completed_jobs.append(job_info)
                elif status == "failed":
                    job_info = pending_jobs.pop(job_id)
                    job_info["step_instance_id"] = step_instance_id
                    job_info["failure_reason"] = "job_failed"
                    failed_jobs.append(job_info)
            except Exception as e:
                logger.error(f"Error checking job {job_id}: {e}")
    return pending_jobs, completed_jobs, failed_jobs, len(jobs_to_check)


def _get_job_ip_log(job: Dict) -> Tuple[str, Optional[str]]:
    step_instance_id = job.get("step_instance_id")
    if not step_instance_id:
        return "", "no_step_instance_id"
    payload = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "job_instance_id": job["job_instance_id"],
        "step_instance_id": step_instance_id,
        "bk_cloud_id": job["bk_cloud_id"],
        "ip": job["exec_ip"],
    }
    try:
        resp = JobApi.get_job_instance_ip_log(payload, raw=True)
    except Exception as e:
        logger.error(f"conf_check get_job_instance_ip_log raised for job {job.get('job_instance_id')}: {e}")
        return "", "log_fetch_exception: {}".format(e)
    if not resp.get("result"):
        logger.warning(
            "conf_check get_job_instance_ip_log no result for job %s: %s",
            job.get("job_instance_id"),
            resp.get("message"),
        )
        return "", "log_fetch_failed: {}".format(resp.get("message") or "no_result")
    return resp.get("data", {}).get("log_content", ""), None


def _collect_host_conf_data(completed_jobs: List[Dict]) -> Dict[Tuple[str, str, int], Dict]:
    """Fetch each host log and parse tagged <CONFCHK> blocks into host_conf_data."""
    host_conf_data: Dict[Tuple[str, str, int], Dict] = {}
    if not completed_jobs:
        return host_conf_data

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_job = {executor.submit(_get_job_ip_log, job): job for job in completed_jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            conf_targets = job.get("conf_targets", [])
            log_content, log_err = future.result()
            if log_err:
                mark_host_targets(host_conf_data, job["exec_ip"], conf_targets, log_err)
                continue
            if not log_content:
                mark_host_targets(host_conf_data, job["exec_ip"], conf_targets, "empty_log")
                continue
            matched_ports = set()
            for match in CONFCHK_PATTERN.finditer(log_content):
                checker_name = match.group("checker")
                port = int(match.group("port"))
                matched_ports.add(port)
                try:
                    body = json.loads(match.group("body"))
                except json.JSONDecodeError:
                    body = {"error": "bad_json"}
                host_conf_data[(checker_name, job["exec_ip"], port)] = body
            for ct in conf_targets:
                if ct["port"] not in matched_ports:
                    mark_host_targets(host_conf_data, job["exec_ip"], [ct], "no_confchk_output")
    return host_conf_data


# group_key: (bk_cloud_id, cluster_id, password_key, command)
DrsChunkKey = Tuple[int, int, str, str]
DrsChunk = Tuple[DrsChunkKey, List[str]]


def _build_drs_chunk_queue(target_infos: List[Dict], chunk_size: int) -> List[DrsChunk]:
    groups: Dict[DrsChunkKey, set] = defaultdict(set)
    for target_info in target_infos:
        checker = _checker_by_name(target_info["checker"])
        if checker is None:
            continue
        target = _target_from_info(target_info)
        drs_req = checker.drs_request(target)
        if not drs_req:
            continue
        command, password_key = drs_req
        groups[(target.bk_cloud_id, target_info["cluster_id"], password_key, command)].add(target.address)

    chunk_size = max(int(chunk_size or DEFAULT_DRS_GROUP_CHUNK_SIZE), 1)
    chunks: List[DrsChunk] = []
    for group_key, address_set in groups.items():
        for address_chunk in _chunks(sorted(address_set), chunk_size):
            chunks.append((group_key, address_chunk))
    return chunks


def _build_password_cache(
    cluster_ids: set, password_batch_size: int = DEFAULT_REDIS_PASSWORD_BATCH_SIZE
) -> Tuple[Dict[int, Dict], Dict[int, str]]:
    if not cluster_ids:
        return {}, {}

    password_cache, missing, password_errors = get_cached_cluster_passwords(set(cluster_ids))
    if not missing:
        return password_cache, password_errors

    cluster_cache = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=missing)}
    to_fetch: List[Cluster] = []
    for cluster_id in missing:
        cluster = cluster_cache.get(cluster_id)
        if cluster is None:
            password_cache[cluster_id] = {}
            password_errors[cluster_id] = "cluster_not_in_meta"
            continue
        to_fetch.append(cluster)

    if to_fetch:
        fetch_errors: Dict[int, str] = {}
        fetched = PayloadHandler.redis_batch_get_cluster_passwords(
            to_fetch, chunk_size=password_batch_size, errors_out=fetch_errors
        )
        password_cache.update(fetched)
        password_errors.update(fetch_errors)

    put_cached_cluster_passwords(
        {cluster_id: password_cache[cluster_id] for cluster_id in missing if cluster_id in password_cache},
        errors={cluster_id: password_errors[cluster_id] for cluster_id in missing if cluster_id in password_errors},
    )
    return password_cache, password_errors


def _get_password_cache_for_drs(
    data, password_batch_size: Optional[int] = None
) -> Tuple[Dict[int, Dict], Dict[int, str]]:
    """Resolve passwords from process-local cache only; never persist secrets in data.outputs."""
    if not data.outputs.drs_chunk_queue:
        return {}, {}
    cluster_ids = {chunk[0][1] for chunk in data.outputs.drs_chunk_queue}
    if password_batch_size is None:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        password_batch_size = kwargs.get("password_batch_size") or DEFAULT_REDIS_PASSWORD_BATCH_SIZE
    return _build_password_cache(cluster_ids, password_batch_size)


def _init_batch_schedule_outputs(
    data,
    *,
    phase: str,
    target_infos: List[Dict],
    pending_jobs: Dict,
    host_conf_data: Dict,
    drs_chunk_queue: List,
) -> None:
    """Persist only state that must survive bamboo schedule ticks between phases."""
    data.outputs.target_infos = target_infos
    data.outputs.phase = phase
    data.outputs.pending_jobs = pending_jobs
    data.outputs.completed_jobs = []
    data.outputs.failed_jobs = []
    data.outputs.host_conf_data = host_conf_data
    data.outputs.poll_count = 0
    data.outputs.drs_chunk_queue = drs_chunk_queue
    data.outputs.drs_cursor = 0
    data.outputs.drs_result_map = {}
    data.outputs.drs_error_map = {}


def _redis_rpc_chunk(
    bk_cloud_id: int,
    command: str,
    addresses: List[str],
    password: str,
    errors_out: Dict[Tuple[int, str, str], str],
) -> Dict[Tuple[int, str, str], str]:
    out: Dict[Tuple[int, str, str], str] = {}
    try:
        resp = DRSApi.redis_rpc(
            {
                "addresses": addresses,
                "db_num": 0,
                "password": password,
                "command": command,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        for item in resp or []:
            address = item.get("address")
            result = item.get("result")
            if address and result:
                out[(bk_cloud_id, command, address)] = result
            elif address is not None:
                errors_out[(bk_cloud_id, command, address)] = "empty_result: {}".format(
                    item.get("error_msg") or "no_result"
                )
    except Exception as e:
        logger.error(f"DRS '{command}' failed for bk_cloud_id={bk_cloud_id} ({len(addresses)} addrs): {e}")
        for address in addresses:
            errors_out[(bk_cloud_id, command, address)] = "drs_rpc_error: {}".format(e)
    return out


def _run_single_drs_chunk(
    group_key: DrsChunkKey,
    addresses: List[str],
    password_cache: Dict[int, Dict],
    password_errors: Dict[int, str],
) -> Tuple[Dict[Tuple[int, str, str], str], Dict[Tuple[int, str, str], str]]:
    bk_cloud_id, cluster_id, password_key, command = group_key
    local_errors: Dict[Tuple[int, str, str], str] = {}
    pwd_err = password_errors.get(cluster_id)
    if pwd_err:
        err = format_password_drs_error(pwd_err)
        for address in addresses:
            local_errors[(bk_cloud_id, command, address)] = err
        return {}, local_errors
    passwords = password_cache.get(cluster_id, {})
    password = passwords.get(password_key, "")
    out = _redis_rpc_chunk(bk_cloud_id, command, addresses, password, local_errors)
    return out, local_errors


def _run_drs_chunk_slice(
    chunk_slice: List[DrsChunk],
    password_cache: Dict[int, Dict],
    password_errors: Dict[int, str],
) -> Tuple[Dict[Tuple[int, str, str], str], Dict[Tuple[int, str, str], str]]:
    """Run DRS redis_rpc for queued chunks in parallel (bounded by MAX_WORKERS)."""
    if not chunk_slice:
        return {}, {}
    if len(chunk_slice) == 1:
        group_key, addresses = chunk_slice[0]
        return _run_single_drs_chunk(group_key, addresses, password_cache, password_errors)

    result_map: Dict[Tuple[int, str, str], str] = {}
    error_map: Dict[Tuple[int, str, str], str] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_run_single_drs_chunk, group_key, addresses, password_cache, password_errors)
            for group_key, addresses in chunk_slice
        ]
        for future in as_completed(futures):
            chunk_result, chunk_errors = future.result()
            result_map.update(chunk_result)
            error_map.update(chunk_errors)
    return result_map, error_map


def _evaluate_and_report(
    clusters: List[Dict],
    host_conf_data: Dict[Tuple[str, str, int], Dict],
    creator: str,
    *,
    target_infos: Optional[List[Dict]] = None,
    drs_result_map: Optional[Dict[Tuple[int, str, str], str]] = None,
    drs_error_map: Optional[Dict[Tuple[int, str, str], str]] = None,
    checker_customized: Optional[Dict[str, Dict]] = None,
    log_info=None,
) -> Tuple[int, int]:
    """Evaluate pre-collected checker inputs and write reports. DRS must be fetched in schedule."""
    writer = RedisReportWriter()
    report_day = int(timezone.now().strftime("%Y%m%d"))
    checker_customized = checker_customized or {}
    drs_result_map = drs_result_map if drs_result_map is not None else {}
    drs_error_map = drs_error_map if drs_error_map is not None else {}
    if not target_infos:
        target_infos, metrics = _build_target_infos(clusters)
        logger.warning(
            "conf check target_infos missing, rebuilt: clusters=%s targets=%s collect_calls=%s",
            metrics["cluster_count"],
            metrics["target_count"],
            metrics["checker_target_collect_calls"],
        )
        if log_info:
            log_info(
                _(
                    "配置检查target缺失, 已fallback重建: clusters={}, targets={}, collect_calls={}".format(
                        metrics["cluster_count"], metrics["target_count"], metrics["checker_target_collect_calls"]
                    )
                )
            )

    eval_tasks = []
    for target_info in target_infos:
        checker = _checker_by_name(target_info["checker"])
        if checker is None:
            continue
        target = _target_from_info(target_info)
        drs_req = checker.drs_request(target)
        command = drs_req[0] if drs_req else None
        host_block = host_conf_data.get((checker.name, target.ip, target.port))
        eval_tasks.append((target_info, checker, target, command, host_block))

    report_rows = []
    for target_info, checker, target, command, host_block in eval_tasks:
        drs_result = drs_result_map.get((target.bk_cloud_id, command, target.address)) if command else None
        drs_error = drs_error_map.get((target.bk_cloud_id, command, target.address)) if command else None
        checker_config = checker_customized.get(checker.name, {})
        try:
            results = checker.evaluate(
                target, drs_result, host_block, checker_config=checker_config, drs_error=drs_error
            )
        except Exception as e:
            logger.error(f"checker {checker.name} evaluate failed for {target.address}: {e}")
            report_rows.append(
                _report_row(
                    target_info,
                    report_day,
                    creator,
                    state=ReportStateType.ABNORMAL.value,
                    msg=_("evaluate_internal_error[{}]: {}").format(checker.name, e),
                    ip=target.ip,
                    port=target.port,
                )
            )
            continue
        for result in results:
            report_rows.append(
                _report_row(
                    target_info,
                    report_day,
                    creator,
                    state=result.state,
                    msg=result.msg,
                    ip=result.ip,
                    port=result.port,
                )
            )
    collapsed_rows = _collapse_conf_check_report_rows(report_rows)
    writer.write_redis_reports(collapsed_rows)
    ingest_daily_cluster_rows(
        collapsed_rows,
        dimension=RedisPortraitDimensionCode.CONFIG_HEALTH,
        prefix=_("[配置]"),
    )
    ok_count = sum(1 for row in collapsed_rows if row["state"] == ReportStateType.NORMAL.value)
    abnormal_count = sum(1 for row in collapsed_rows if row["state"] != ReportStateType.NORMAL.value)
    return ok_count, abnormal_count


def _collapse_conf_check_report_rows(report_rows: List[Dict]) -> List[Dict]:
    """
    Per cluster: emit one cluster-level NORMAL row when all instances pass;
    otherwise emit only abnormal instance rows.
    """
    by_cluster: Dict[int, List[Dict]] = defaultdict(list)
    for row in report_rows:
        by_cluster[row["cluster_id"]].append(row)

    collapsed: List[Dict] = []
    for rows in by_cluster.values():
        abnormal_rows = [row for row in rows if row["state"] != ReportStateType.NORMAL.value]
        if abnormal_rows:
            collapsed.extend(abnormal_rows)
            continue
        if not rows:
            continue
        sample = rows[0]
        collapsed.append(
            {
                **sample,
                "instance": "all",
                "msg": _("集群{}配置检查通过").format(sample["cluster"]),
            }
        )
    return collapsed


class RedisConfCheckBatchService(BaseService):
    """
    Per-batch conf check in a single scheduled node: issue host scripts in
    _execute, then poll jobs, pace DRS chunks, evaluate and report in _schedule.

    kwargs:
        - candidates_key, batch_num, batch_size, total_batches
        - node_name, interval, max_retries, drs_chunk_size, drs_chunks_per_tick
        - delay_after_seconds: wait before finishing (merged inter-batch delay; 0 on last batch)
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(DEFAULT_POLL_INTERVAL)

    @staticmethod
    def _set_schedule_interval(service, seconds: float) -> None:
        """Adjust poll wake-up interval in place (bamboo reads interval.interval, not a new generator)."""
        wait_seconds = max(int(seconds), 1)
        if isinstance(service.interval, StaticIntervalGenerator):
            service.interval.interval = wait_seconds
        else:
            service.interval = StaticIntervalGenerator(wait_seconds)

    @staticmethod
    def _finish_batch(service, kwargs: Dict) -> None:
        candidates_key = kwargs.get("candidates_key")
        batch_num = int(kwargs.get("batch_num") or 0)
        total_batches = int(kwargs.get("total_batches") or 0)
        if candidates_key and batch_num == total_batches:
            delete_candidates_key(candidates_key)
        service.finish_schedule()

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        node_name = kwargs.get("node_name", self.__class__.__name__)
        clusters = _resolve_batch_clusters(kwargs)
        flow_id = self.runtime_attrs.get("root_pipeline_id", "")

        poll_interval = kwargs.get("interval") or DEFAULT_POLL_INTERVAL
        drs_chunk_size = kwargs.get("drs_chunk_size") or DEFAULT_DRS_GROUP_CHUNK_SIZE
        self.interval = StaticIntervalGenerator(poll_interval)

        if not clusters:
            self.log_warning(_("[{}] 本批次无待检查集群, 跳过").format(node_name))
            _init_batch_schedule_outputs(
                data,
                phase=PHASE_EVALUATE,
                target_infos=[],
                pending_jobs={},
                host_conf_data={},
                drs_chunk_queue=[],
            )
            return True

        target_infos, metrics = _build_target_infos(clusters)
        host_map = _build_host_map(target_infos)
        drs_chunk_queue = _build_drs_chunk_queue(target_infos, drs_chunk_size)

        if host_map:
            self.log_info(_("[{}] 准备下发 {} 个主机配置检查脚本").format(node_name, len(host_map)))
            host_conf_data: Dict[Tuple[str, str, int], Dict] = {}
            job_infos, issue_failure_count = _issue_host_jobs(
                host_map,
                flow_id,
                node_name,
                self.log_warning,
                self.log_error,
                host_conf_data,
            )
            self.log_info(_("[{}] 成功下发 {} 个主机脚本").format(node_name, len(job_infos)))
            if issue_failure_count:
                self.log_warning(_("[{}] {} 个主机脚本下发失败, 相关配置比对将标记为异常").format(node_name, issue_failure_count))
        else:
            self.log_info(_("[{}] 本批次无需下发主机脚本(全部通过DRS采集)").format(node_name))
            job_infos = []
            host_conf_data = {}

        metrics = {
            **metrics,
            "host_job_count": len(job_infos),
            "host_script_count": len(host_map),
            "drs_chunk_count": len(drs_chunk_queue),
        }

        pending_jobs = {info["job_instance_id"]: info for info in job_infos}
        if pending_jobs:
            phase = PHASE_POLL_JOBS
        elif drs_chunk_queue:
            phase = PHASE_RUN_DRS
        else:
            phase = PHASE_EVALUATE

        _init_batch_schedule_outputs(
            data,
            phase=phase,
            target_infos=target_infos,
            pending_jobs=pending_jobs,
            host_conf_data=host_conf_data,
            drs_chunk_queue=drs_chunk_queue,
        )

        self.log_info(
            _("[{}] 批次初始化: targets={}, host_jobs={}, drs_chunks={}, phase={}").format(
                node_name, metrics["target_count"], len(pending_jobs), len(drs_chunk_queue), phase
            )
        )
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        node_name = kwargs.get("node_name", self.__class__.__name__)
        creator = global_data.get("created_by", "system")

        phase = data.outputs.phase
        target_infos = data.outputs.target_infos
        max_retries = kwargs.get("max_retries") or DEFAULT_POLL_MAX_RETRIES
        drs_chunks_per_tick = max(int(kwargs.get("drs_chunks_per_tick") or DEFAULT_DRS_CHUNKS_PER_TICK), 1)
        password_batch_size = max(int(kwargs.get("password_batch_size") or DEFAULT_REDIS_PASSWORD_BATCH_SIZE), 1)

        if phase == PHASE_POLL_JOBS:
            poll_count = data.outputs.poll_count + 1
            data.outputs.poll_count = poll_count
            pending_jobs = data.outputs.pending_jobs
            completed_jobs = data.outputs.completed_jobs
            failed_jobs = data.outputs.failed_jobs

            if poll_count > max_retries and pending_jobs:
                self.log_warning(_("[{}] 轮询超时, {} 个主机脚本未完成").format(node_name, len(pending_jobs)))
                for job_info in pending_jobs.values():
                    job_info["failure_reason"] = "job_timeout"
                    failed_jobs.append(job_info)
                pending_jobs.clear()

            if pending_jobs:
                pending_jobs, completed_jobs, failed_jobs, _status_checks = _poll_jobs_once(
                    pending_jobs, completed_jobs, failed_jobs
                )
                data.outputs.pending_jobs = pending_jobs
                data.outputs.completed_jobs = completed_jobs
                data.outputs.failed_jobs = failed_jobs

                if pending_jobs:
                    self.log_info(_("[{}] 轮询#{}: 仍有 {} 个主机脚本运行中").format(node_name, poll_count, len(pending_jobs)))
                    return True

            host_conf_data = dict(data.outputs.host_conf_data)
            host_conf_data.update(_collect_host_conf_data(completed_jobs))
            for job in failed_jobs:
                mark_host_targets(
                    host_conf_data,
                    job["exec_ip"],
                    job.get("conf_targets", []),
                    job.get("failure_reason") or "job_failed",
                )
            data.outputs.host_conf_data = host_conf_data
            failed_job_count = len(failed_jobs)
            data.outputs.completed_jobs = []
            data.outputs.failed_jobs = []
            if failed_job_count:
                self.log_warning(_("[{}] {} 个主机脚本执行失败, 相关配置比对将标记为异常").format(node_name, failed_job_count))

            if data.outputs.drs_chunk_queue:
                data.outputs.phase = PHASE_RUN_DRS
                return True
            data.outputs.phase = PHASE_EVALUATE
            phase = PHASE_EVALUATE

        if phase == PHASE_RUN_DRS:
            drs_chunk_queue = data.outputs.drs_chunk_queue
            drs_cursor = data.outputs.drs_cursor
            password_cache, password_errors = _get_password_cache_for_drs(data, password_batch_size)
            drs_result_map = data.outputs.drs_result_map
            drs_error_map = data.outputs.drs_error_map

            end = min(drs_cursor + drs_chunks_per_tick, len(drs_chunk_queue))
            chunk_results, chunk_errors = _run_drs_chunk_slice(
                drs_chunk_queue[drs_cursor:end],
                password_cache,
                password_errors,
            )
            drs_result_map.update(chunk_results)
            drs_error_map.update(chunk_errors)
            data.outputs.drs_cursor = end
            data.outputs.drs_result_map = drs_result_map
            data.outputs.drs_error_map = drs_error_map

            if end < len(drs_chunk_queue):
                self.log_info(_("[{}] DRS进度: {}/{} chunks").format(node_name, end, len(drs_chunk_queue)))
                return True

            data.outputs.drs_chunk_queue = []
            data.outputs.phase = PHASE_EVALUATE
            phase = PHASE_EVALUATE

        if phase == PHASE_EVALUATE:
            ok, abnormal = _evaluate_and_report(
                [],
                data.outputs.host_conf_data,
                creator,
                target_infos=target_infos,
                drs_result_map=data.outputs.drs_result_map,
                drs_error_map=data.outputs.drs_error_map,
                checker_customized=global_data.get("checker_customized") or {},
                log_info=self.log_info,
            )
            self.log_info(_("[{}] 配置检查完成: 正常 {} 项, 异常 {} 项").format(node_name, ok, abnormal))
            delay_after_seconds = int(kwargs.get("delay_after_seconds") or 0)
            if delay_after_seconds > 0:
                target_time = timezone.now() + datetime.timedelta(seconds=delay_after_seconds)
                data.outputs.phase = PHASE_BATCH_DELAY
                data.outputs.delay_target_time = target_time
                self._set_schedule_interval(self, min(delay_after_seconds, 60))
                self.log_info(_("[{}] 批次间隔等待 {} 秒后继续下一批次, 预计 {}").format(node_name, delay_after_seconds, target_time))
                return True
            self._finish_batch(self, kwargs)
            return True

        if phase == PHASE_BATCH_DELAY:
            remaining_seconds = (data.outputs.delay_target_time - timezone.now()).total_seconds()
            if remaining_seconds <= 0:
                self.log_info(_("[{}] 批次间隔等待完成").format(node_name))
                self._finish_batch(self, kwargs)
                return True
            if remaining_seconds > self.interval.interval:
                self._set_schedule_interval(self, min(remaining_seconds / 2, 60))
            else:
                self._set_schedule_interval(self, remaining_seconds)
            self.log_info(_("[{}] 批次间隔等待中, 剩余 {} 秒").format(node_name, int(remaining_seconds)))
            return True

        logger.warning("conf check batch unknown phase: %s", phase)
        return False

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return []


class RedisConfCheckBatchComponent(Component):
    name = __name__
    code = "redis_conf_check_batch"
    bound_service = RedisConfCheckBatchService
