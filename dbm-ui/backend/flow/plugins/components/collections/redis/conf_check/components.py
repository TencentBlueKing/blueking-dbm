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
from backend.flow.consts import SUCCESS_LIST
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import RedisConfCheckContext
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter
from backend.flow.utils.redis.redis_script_template import (
    CONF_CHECK_SCRIPT_HEADER,
    redis_fast_execute_script_common_kwargs,
)
from backend.utils.string import base64_encode

from .base import CheckTarget
from .registry import CHECKER_REGISTRY

logger = logging.getLogger("json")

# <CONFCHK checker="predixy_servers" port="50000">{json}</CONFCHK>
CONFCHK_PATTERN = re.compile(
    r'<CONFCHK\s+checker="(?P<checker>[^"]+)"\s+port="(?P<port>\d+)">(?P<body>.*?)</CONFCHK>', re.DOTALL
)

MAX_WORKERS = getattr(settings, "CONCURRENT_NUMBER", 10)
DEFAULT_DRS_GROUP_CHUNK_SIZE = 20
DEFAULT_POLL_INTERVAL = 5  # seconds
DEFAULT_POLL_MAX_RETRIES = 120  # default timeout = interval * max_retries = 10min

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


class RedisConfCheckCollectService(BaseService):
    """
    Deliver the on-host portion of every checker for a batch of clusters.

    Targets needing on-host work are grouped by host, and all applicable
    checkers' snippets for a host are concatenated into ONE script delivered as a
    single Job per host. Checkers that read live state only (via DRS) contribute
    no snippet, so hosts with only DRS checkers produce no job.

    kwargs:
        - clusters: [{"cluster_id": int, "bk_cloud_id": int}, ...]
        - node_name: str
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = RedisConfCheckContext()

        node_name = kwargs.get("node_name", self.__class__.__name__)
        clusters = kwargs.get("clusters", [])
        flow_id = self.runtime_attrs.get("root_pipeline_id", "")

        target_infos, metrics = _build_target_infos(clusters)
        trans_data.target_infos = target_infos
        trans_data.check_metrics = metrics

        # host_key (bk_cloud_id, ip) -> {"snippets": [...], "conf_targets": [...]}
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

        if not host_map:
            self.log_info(_("[{}] 本批次无需下发主机脚本(全部通过DRS采集)").format(node_name))
            trans_data.job_infos = []
            trans_data.check_metrics = {
                **getattr(trans_data, "check_metrics", {}),
                "host_job_count": 0,
                "host_script_count": 0,
            }
            data.outputs["trans_data"] = trans_data
            return True

        self.log_info(_("[{}] 准备下发 {} 个主机配置检查脚本").format(node_name, len(host_map)))

        job_infos = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {}
            for (bk_cloud_id, ip), entry in host_map.items():
                script = CONF_CHECK_SCRIPT_HEADER + "\n".join(entry["snippets"])
                future = executor.submit(self._fast_execute_script, script, ip, bk_cloud_id, flow_id, node_name)
                future_map[future] = (bk_cloud_id, ip, entry["conf_targets"])

            for future in as_completed(future_map):
                bk_cloud_id, ip, conf_targets = future_map[future]
                try:
                    job_instance_id = future.result()
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
                        self.log_warning(_("[{}] 主机 {} 脚本下发失败").format(node_name, ip))
                except Exception as e:
                    self.log_error(_("[{}] 主机 {} 脚本下发异常: {}").format(node_name, ip, e))

        self.log_info(_("[{}] 成功下发 {} 个主机脚本").format(node_name, len(job_infos)))
        trans_data.job_infos = job_infos
        trans_data.check_metrics = {
            **getattr(trans_data, "check_metrics", {}),
            "host_job_count": len(job_infos),
            "host_script_count": len(host_map),
        }
        data.outputs["trans_data"] = trans_data
        return True

    def _fast_execute_script(
        self, script_content: str, exec_ip: str, bk_cloud_id: int, flow_id: str, node_name: str
    ) -> Optional[int]:
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{flow_id}_{node_name}_{exec_ip}",
            "script_content": base64_encode(script_content),
            "script_language": 1,  # shell
            "target_server": {"ip_list": [{"bk_cloud_id": bk_cloud_id, "ip": exec_ip}]},
        }
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)
        if not resp.get("result") or not resp.get("data"):
            logger.error(f"conf_check fast_execute_script failed on {exec_ip}: {resp.get('message')}")
            return None
        return resp["data"]["job_instance_id"]

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="trans_data", key="trans_data", type="dict")]


class RedisConfCheckCollectComponent(Component):
    name = __name__
    code = "redis_conf_check_collect"
    bound_service = RedisConfCheckCollectService


class RedisConfCheckReportService(BaseService):
    """
    Poll the per-host conf-read jobs, gather live state via DRS, evaluate every
    checker and write reports. Uses __need_schedule__ to avoid blocking workers.

    kwargs:
        - clusters: [{"cluster_id": int, "bk_cloud_id": int}, ...]
        - node_name, interval, max_retries
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(DEFAULT_POLL_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = RedisConfCheckContext()

        node_name = kwargs.get("node_name", self.__class__.__name__)
        poll_interval = kwargs.get("interval") or DEFAULT_POLL_INTERVAL
        max_retries = kwargs.get("max_retries") or DEFAULT_POLL_MAX_RETRIES
        drs_chunk_size = kwargs.get("drs_chunk_size") or DEFAULT_DRS_GROUP_CHUNK_SIZE
        self.interval = StaticIntervalGenerator(poll_interval)

        job_infos = getattr(trans_data, "job_infos", []) or []
        self.log_info(_("[{}] 开始处理, 待轮询主机脚本任务数: {}").format(node_name, len(job_infos)))

        data.outputs.pending_jobs = {info["job_instance_id"]: info for info in job_infos}
        data.outputs.completed_jobs = []
        data.outputs.failed_jobs = []
        data.outputs.poll_count = 0
        data.outputs.max_retries = max_retries
        data.outputs.drs_chunk_size = drs_chunk_size
        data.outputs.job_status_check_count = 0
        data.outputs.job_log_fetch_count = 0
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = RedisConfCheckContext()
        node_name = kwargs.get("node_name", self.__class__.__name__)
        creator = global_data.get("created_by", "system")
        clusters = kwargs.get("clusters", [])

        pending_jobs = data.outputs.pending_jobs
        completed_jobs = data.outputs.completed_jobs
        failed_jobs = data.outputs.failed_jobs
        poll_count = data.outputs.poll_count + 1
        data.outputs.poll_count = poll_count
        max_retries = data.outputs.get("max_retries", DEFAULT_POLL_MAX_RETRIES)
        drs_chunk_size = data.outputs.get("drs_chunk_size", DEFAULT_DRS_GROUP_CHUNK_SIZE)

        if poll_count > max_retries and pending_jobs:
            self.log_warning(_("[{}] 轮询超时, {} 个主机脚本未完成").format(node_name, len(pending_jobs)))
            for job_info in pending_jobs.values():
                failed_jobs.append(job_info)
            pending_jobs.clear()

        if pending_jobs:
            jobs_to_check = list(pending_jobs.keys())
            data.outputs.job_status_check_count = data.outputs.get("job_status_check_count", 0) + len(jobs_to_check)
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_job_id = {
                    executor.submit(self._check_job_status, job_id): job_id for job_id in jobs_to_check
                }
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
                            failed_jobs.append(job_info)
                    except Exception as e:
                        logger.error(f"Error checking job {job_id}: {e}")

            data.outputs.pending_jobs = pending_jobs
            data.outputs.completed_jobs = completed_jobs
            data.outputs.failed_jobs = failed_jobs

            if pending_jobs:
                self.log_info(_("[{}] 轮询#{}: 仍有 {} 个主机脚本运行中").format(node_name, poll_count, len(pending_jobs)))
                return True

        # All host jobs done (or none). Pull conf data from logs, then evaluate every checker.
        host_conf_data = self._collect_host_conf_data(completed_jobs)
        data.outputs.job_log_fetch_count = len(completed_jobs)
        if failed_jobs:
            self.log_warning(_("[{}] {} 个主机脚本执行失败, 相关配置比对将标记为异常").format(node_name, len(failed_jobs)))

        target_infos = getattr(trans_data, "target_infos", []) or []
        ok, abnormal = self._evaluate_and_report(
            clusters, host_conf_data, creator, target_infos=target_infos, drs_chunk_size=drs_chunk_size
        )
        self.log_info(
            _(
                "[{}] 配置检查完成: 正常 {} 项, 异常 {} 项, Job状态查询 {} 次, 日志拉取 {} 次".format(
                    node_name,
                    ok,
                    abnormal,
                    data.outputs.get("job_status_check_count", 0),
                    data.outputs.get("job_log_fetch_count", 0),
                )
            )
        )

        self.finish_schedule()
        return True

    def _check_job_status(self, job_instance_id: int) -> Tuple[str, Optional[int]]:
        payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "return_ip_result": True,
        }
        resp = JobApi.get_job_instance_status(payload, raw=True)
        if not resp.get("result") or not resp.get("data"):
            return "running", None
        if not resp["data"]["finished"]:
            return "running", None

        job_status = resp["data"]["job_instance"]["status"]
        step_instance_id = (
            resp["data"]["step_instance_list"][0]["step_instance_id"] if resp["data"]["step_instance_list"] else None
        )
        return ("completed", step_instance_id) if job_status in SUCCESS_LIST else ("failed", step_instance_id)

    def _collect_host_conf_data(self, completed_jobs: List[Dict]) -> Dict[Tuple[str, str, int], Dict]:
        """
        Fetch each host's log (in parallel) and parse the tagged <CONFCHK> blocks.

        Returns: {(checker_name, ip, port): body_dict}
        """
        host_conf_data: Dict[Tuple[str, str, int], Dict] = {}
        if not completed_jobs:
            return host_conf_data

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_job = {executor.submit(self._get_job_ip_log, job): job for job in completed_jobs}
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    log_content = future.result()
                except Exception as e:
                    logger.error(f"Error fetching log for job {job.get('job_instance_id')}: {e}")
                    continue
                if not log_content:
                    continue
                for match in CONFCHK_PATTERN.finditer(log_content):
                    checker_name = match.group("checker")
                    port = int(match.group("port"))
                    try:
                        body = json.loads(match.group("body"))
                    except json.JSONDecodeError:
                        body = {"error": "bad_json"}
                    host_conf_data[(checker_name, job["exec_ip"], port)] = body
        return host_conf_data

    def _get_job_ip_log(self, job: Dict) -> str:
        step_instance_id = job.get("step_instance_id")
        if not step_instance_id:
            return ""
        payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job["job_instance_id"],
            "step_instance_id": step_instance_id,
            "bk_cloud_id": job["bk_cloud_id"],
            "ip": job["exec_ip"],
        }
        resp = JobApi.get_job_instance_ip_log(payload, raw=True)
        if not resp.get("result"):
            return ""
        return resp.get("data", {}).get("log_content", "")

    def _evaluate_and_report(
        self,
        clusters: List[Dict],
        host_conf_data: Dict[Tuple[str, str, int], Dict],
        creator: str,
        target_infos: Optional[List[Dict]] = None,
        drs_chunk_size: int = DEFAULT_DRS_GROUP_CHUNK_SIZE,
    ) -> Tuple[int, int]:
        """Run DRS (bounded + batched), evaluate every checker, write reports."""
        writer = RedisReportWriter()
        report_day = int(timezone.now().strftime("%Y%m%d"))
        if not target_infos:
            target_infos, metrics = _build_target_infos(clusters)
            self.log_info(
                _(
                    "配置检查target缺失, 已fallback重建: clusters={}, targets={}, collect_calls={}".format(
                        metrics["cluster_count"], metrics["target_count"], metrics["checker_target_collect_calls"]
                    )
                )
            )

        # Build eval tasks + the DRS request groups.
        # eval_tasks: [(target_info, checker, target, command, host_block)]
        eval_tasks = []
        # drs_groups: (bk_cloud_id, password, command) -> set(addresses)
        drs_groups: Dict[Tuple[int, str, str], set] = defaultdict(set)
        password_cache: Dict[int, Dict] = {}
        drs_cluster_ids = set()
        for target_info in target_infos:
            checker = _checker_by_name(target_info["checker"])
            if checker is None:
                continue
            target = _target_from_info(target_info)
            drs_req = checker.drs_request(target)
            if drs_req:
                drs_cluster_ids.add(target_info["cluster_id"])

        cluster_cache = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=drs_cluster_ids)}
        for cluster_id in drs_cluster_ids:
            cluster = cluster_cache.get(cluster_id)
            if cluster is None:
                continue
            try:
                password_cache[cluster_id] = PayloadHandler.redis_get_cluster_password(cluster)
            except Exception as e:
                logger.error(f"get password for cluster {cluster_id} failed: {e}")
                password_cache[cluster_id] = {}

        for target_info in target_infos:
            checker = _checker_by_name(target_info["checker"])
            if checker is None:
                continue
            target = _target_from_info(target_info)
            command = None
            drs_req = checker.drs_request(target)
            if drs_req:
                command, password_key = drs_req
                passwords = password_cache.get(target_info["cluster_id"], {})
                password = passwords.get(password_key, "")
                drs_groups[(target.bk_cloud_id, password, command)].add(target.address)
            host_block = host_conf_data.get((checker.name, target.ip, target.port))
            eval_tasks.append((target_info, checker, target, command, host_block))

        drs_result_map = self._run_drs_groups(drs_groups, chunk_size=drs_chunk_size)

        ok_count = 0
        abnormal_count = 0
        report_rows = []
        for target_info, checker, target, command, host_block in eval_tasks:
            drs_result = drs_result_map.get((target.bk_cloud_id, command, target.address)) if command else None
            try:
                results = checker.evaluate(target, drs_result, host_block)
            except Exception as e:
                logger.error(f"checker {checker.name} evaluate failed for {target.address}: {e}")
                continue
            for result in results:
                report_rows.append(
                    {
                        "cluster_id": target_info["cluster_id"],
                        "subtype": CONF_CHECK_SUBTYPE,
                        "cluster": target_info["cluster"],
                        "cluster_type": target_info["cluster_type"],
                        "bk_biz_id": target_info["bk_biz_id"],
                        "bk_cloud_id": target_info["bk_cloud_id"],
                        "report_day": report_day,
                        "creator": creator,
                        "state": result.state,
                        "msg": result.msg,
                        "instance": "{}:{}".format(result.ip, result.port),
                    }
                )
                if result.state == ReportStateType.NORMAL.value:
                    ok_count += 1
                else:
                    abnormal_count += 1
        writer.write_redis_reports(report_rows)
        return ok_count, abnormal_count

    def _run_drs_groups(
        self, drs_groups: Dict[Tuple[int, str, str], set], chunk_size: int = DEFAULT_DRS_GROUP_CHUNK_SIZE
    ) -> Dict[Tuple[int, str, str], str]:
        """Issue chunked batched redis_rpc calls per (bk_cloud_id, password, command), bounded by MAX_WORKERS."""
        drs_result_map: Dict[Tuple[int, str, str], str] = {}
        if not drs_groups:
            return drs_result_map
        chunk_size = max(int(chunk_size or DEFAULT_DRS_GROUP_CHUNK_SIZE), 1)

        def run_chunk(group_key: Tuple[int, str, str], addresses: List[str]) -> Dict[Tuple[int, str, str], str]:
            bk_cloud_id, password, command = group_key
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
                    out[(bk_cloud_id, command, item["address"])] = item.get("result")
            except Exception as e:
                logger.error(f"DRS '{command}' failed for bk_cloud_id={bk_cloud_id} ({len(addresses)} addrs): {e}")
            return out

        drs_chunks = []
        for group_key, address_set in drs_groups.items():
            addresses = sorted(address_set)
            for address_chunk in _chunks(addresses, chunk_size):
                drs_chunks.append((group_key, address_chunk))

        logger.info(
            "Redis conf check DRS: groups=%s chunks=%s addresses=%s",
            len(drs_groups),
            len(drs_chunks),
            sum(len(chunk) for _, chunk in drs_chunks),
        )
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(run_chunk, group_key, address_chunk) for group_key, address_chunk in drs_chunks]
            for future in as_completed(futures):
                drs_result_map.update(future.result())
        return drs_result_map

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return []


class RedisConfCheckReportComponent(Component):
    name = __name__
    code = "redis_conf_check_report"
    bound_service = RedisConfCheckReportService
