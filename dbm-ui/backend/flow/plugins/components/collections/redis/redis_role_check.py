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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.flow.consts import SUCCESS_LIST
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_context_dataclass import RedisRoleCheckContext
from backend.flow.utils.redis.redis_meta_report import create_meta_check_report
from backend.flow.utils.redis.redis_script_template import (
    build_redis_role_check_script,
    redis_fast_execute_script_common_kwargs,
)
from backend.utils.string import base64_encode

logger = logging.getLogger("json")

# Regex pattern for extracting JSON context from script output
CTX_PATTERN = re.compile(r"<ctx>(?P<context>.+?)</ctx>", re.DOTALL)

# Maximum concurrent API requests
MAX_WORKERS = getattr(settings, "CONCURRENT_NUMBER", 10)

# Default polling configuration
DEFAULT_POLL_INTERVAL = 5  # seconds
DEFAULT_POLL_MAX_RETRIES = 120  # default timeout = 10min


class RedisRoleCheckScriptService(BaseService):
    """
    Execute Redis role check scripts on target machines for a batch of clusters.

    This component processes multiple clusters in parallel:
    - For each cluster in the batch, builds a role check script
    - Executes all scripts concurrently via JobApi.fast_execute_script
    - Stores all job IDs in trans_data for the report service to poll

    kwargs should contain:
        - clusters: List of dicts with cluster_id, bk_cloud_id, exec_ip, instances
        - node_name: Name of this node
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # Handle uninitialized trans_data (None or template string "${trans_data}")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = RedisRoleCheckContext()

        node_name = kwargs.get("node_name", self.__class__.__name__)
        clusters = kwargs.get("clusters", [])

        if not clusters:
            self.log_error(_("No clusters provided for role check"))
            return False

        self.log_info(f"[{node_name}] Starting role check for {len(clusters)} clusters in parallel")

        # Get flow_id from runtime_attrs (standard approach in BaseService)
        flow_id = self.runtime_attrs.get("root_pipeline_id", "")

        # Execute scripts for all clusters in parallel
        job_infos = []
        failed_clusters = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all jobs
            future_to_cluster = {
                executor.submit(self._execute_single_cluster, cluster_data, node_name, flow_id): cluster_data
                for cluster_data in clusters
            }

            # Collect results from completed futures (thread-safe pattern)
            for future in as_completed(future_to_cluster):
                cluster_data = future_to_cluster[future]
                try:
                    result = future.result()
                    if result:
                        job_infos.append(result)
                    else:
                        failed_clusters.append(cluster_data.get("cluster_id"))
                except Exception as e:
                    self.log_error(f"Failed to execute job for cluster {cluster_data.get('cluster_id')}: {e}")
                    failed_clusters.append(cluster_data.get("cluster_id"))

        if failed_clusters:
            self.log_warning(f"[{node_name}] Failed to start jobs for clusters: {failed_clusters}")

        if not job_infos:
            self.log_error(_("No jobs were started successfully"))
            return False

        self.log_info(f"[{node_name}] Successfully started {len(job_infos)} jobs")

        # Store job infos in trans_data for the report service
        trans_data.job_infos = job_infos
        data.outputs["trans_data"] = trans_data
        return True

    def _execute_single_cluster(self, cluster_data: Dict, node_name: str, flow_id: str) -> Optional[Dict]:
        """
        Execute role check script for a single cluster.

        Returns:
            Dict with job_instance_id, cluster_id, bk_cloud_id, exec_ip, instances
            or None if execution failed
        """
        cluster_id = cluster_data.get("cluster_id")
        bk_cloud_id = cluster_data.get("bk_cloud_id", 0)
        exec_ip = cluster_data.get("exec_ip")
        instances = cluster_data.get("instances", [])

        if not exec_ip or not instances:
            logger.error(f"Invalid cluster data for cluster {cluster_id}: missing exec_ip or instances")
            return None

        # Build the role check script
        script_content = build_redis_role_check_script(instances)

        target_ip_info = [{"bk_cloud_id": bk_cloud_id, "ip": exec_ip}]

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{flow_id}_{node_name}_cluster_{cluster_id}",
            "script_content": base64_encode(script_content),
            "script_language": 1,  # shell
            "target_server": {"ip_list": target_ip_info},
        }

        try:
            resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

            if not resp.get("result") or not resp.get("data"):
                logger.error(f"Job API failed for cluster {cluster_id}: {resp.get('message')}")
                return None

            job_instance_id = resp["data"]["job_instance_id"]
            logger.info(f"Started job {job_instance_id} for cluster {cluster_id} on {exec_ip}")

            return {
                "job_instance_id": job_instance_id,
                "cluster_id": cluster_id,
                "bk_cloud_id": bk_cloud_id,
                "exec_ip": exec_ip,
                "instances": instances,
            }

        except Exception as e:
            logger.exception(f"Exception executing job for cluster {cluster_id}: {e}")
            return None

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="trans_data", key="trans_data", type="dict")]


class RedisRoleCheckScriptComponent(Component):
    name = __name__
    code = "redis_role_check_script"
    bound_service = RedisRoleCheckScriptService


class RedisRoleCheckReportService(BaseService):
    """
    Poll job status and parse results for all jobs from the script service.

    This component uses the __need_schedule__ pattern to avoid blocking Celery workers:
    - _execute: Initializes state and returns True to start scheduling
    - _schedule: Called periodically to poll job status and process results

    For each job_id in trans_data (polled in parallel):
        - Check status of the job
        - If success: parse result and write report
        - If timeout or failed: update report as check failed

    kwargs should contain:
        - node_name: Name of this node
        - interval: Polling interval in seconds (default: 5)
        - max_retries: Maximum polling retries (default: 120)
    """

    # Use scheduler pattern to avoid blocking Celery workers with time.sleep
    __need_schedule__ = True
    # Default interval, will be overridden by kwargs in _execute
    interval = StaticIntervalGenerator(DEFAULT_POLL_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        """Initialize polling state and start the schedule loop."""
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # Handle uninitialized trans_data (None or template string "${trans_data}")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = RedisRoleCheckContext()

        node_name = kwargs.get("node_name", self.__class__.__name__)

        # Get polling configuration from kwargs
        poll_interval = kwargs.get("interval") or DEFAULT_POLL_INTERVAL
        max_retries = kwargs.get("max_retries") or DEFAULT_POLL_MAX_RETRIES

        job_infos = getattr(trans_data, "job_infos", [])
        if not job_infos:
            self.log_error(_("No job infos found in trans_data"))
            return False

        self.log_info(f"[{node_name}] Starting to poll {len(job_infos)} jobs for completion")
        self.log_info(f"[{node_name}] Polling config: interval={poll_interval}s, max_retries={max_retries}")

        # Override the interval for this instance
        self.interval = StaticIntervalGenerator(poll_interval)

        # Initialize polling state in data.outputs
        data.outputs.pending_jobs = {info["job_instance_id"]: info for info in job_infos}
        data.outputs.completed_jobs = []
        data.outputs.failed_jobs = []
        data.outputs.poll_count = 0
        data.outputs.max_retries = max_retries

        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        """
        Periodically poll job status. Called by the scheduler every JOB_POLL_INTERVAL seconds.
        This pattern frees up the Celery worker between polls.
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        node_name = kwargs.get("node_name", self.__class__.__name__)
        creator = global_data.get("created_by", "system")

        pending_jobs = data.outputs.pending_jobs
        completed_jobs = data.outputs.completed_jobs
        failed_jobs = data.outputs.failed_jobs
        poll_count = data.outputs.poll_count

        poll_count += 1
        data.outputs.poll_count = poll_count

        # Get max_retries from outputs (set in _execute)
        max_retries = data.outputs.get("max_retries", DEFAULT_POLL_MAX_RETRIES)

        # Check for timeout
        if poll_count > max_retries:
            self.log_warning(
                f"[{node_name}] Polling timeout after {poll_count} retries, marking {len(pending_jobs)} jobs as failed"
            )
            for job_id, job_info in pending_jobs.items():
                failed_jobs.append(job_info)
            pending_jobs.clear()

        # Poll pending jobs in parallel
        if pending_jobs:
            jobs_to_check = list(pending_jobs.keys())

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
                        # status == "running" means keep polling
                    except Exception as e:
                        logger.error(f"Error checking job {job_id}: {e}")

        # Update outputs
        data.outputs.pending_jobs = pending_jobs
        data.outputs.completed_jobs = completed_jobs
        data.outputs.failed_jobs = failed_jobs

        # If there are still pending jobs, continue scheduling
        if pending_jobs:
            self.log_info(f"[{node_name}] Poll #{poll_count}: {len(pending_jobs)} jobs still running")
            return True

        # All jobs completed or failed - process results
        self.log_info(f"[{node_name}] All jobs finished. Completed: {len(completed_jobs)}, Failed: {len(failed_jobs)}")

        # Process completed jobs - get logs and parse results
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_job = {
                executor.submit(self._process_completed_job, job_info, creator): job_info
                for job_info in completed_jobs
            }

            for future in as_completed(future_to_job):
                job_info = future_to_job[future]
                try:
                    result = future.result()
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    self.log_error(f"Error processing job {job_info.get('job_instance_id')}: {e}")
                    fail_count += 1

        # Handle failed/timeout jobs - write failure reports
        for job_info in failed_jobs:
            self._write_failure_report(job_info, creator)
            fail_count += 1

        self.log_info(f"[{node_name}] Role check complete: {success_count} succeeded, {fail_count} failed")

        # Finish scheduling by calling finish_schedule
        self.finish_schedule()
        return True

    def _check_job_status(self, job_instance_id: int) -> Tuple[str, Optional[int]]:
        """
        Check the status of a single job.

        Returns:
            Tuple of (status, step_instance_id) where status is "completed", "failed", or "running"
        """
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

        if job_status in SUCCESS_LIST:
            return "completed", step_instance_id
        else:
            return "failed", step_instance_id

    def _process_completed_job(self, job_info: Dict, creator: str) -> bool:
        """
        Process a completed job - get log, parse results, write reports.

        Returns:
            True if successful, False otherwise
        """
        job_instance_id = job_info["job_instance_id"]
        step_instance_id = job_info.get("step_instance_id")
        cluster_id = job_info["cluster_id"]
        bk_cloud_id = job_info["bk_cloud_id"]
        exec_ip = job_info["exec_ip"]

        if not step_instance_id:
            logger.error(f"No step_instance_id for job {job_instance_id}")
            return False

        # Get job log
        ip_dict = {"bk_cloud_id": bk_cloud_id, "ip": exec_ip}
        payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
        }

        try:
            log_resp = JobApi.get_job_instance_ip_log({**payload, **ip_dict}, raw=True)

            if not log_resp.get("result"):
                logger.error(f"Failed to get log for job {job_instance_id}")
                return False

            log_content = log_resp.get("data", {}).get("log_content", "")
            check_results = self._parse_results(log_content)

            if check_results is None:
                logger.error(f"Failed to parse results for job {job_instance_id}")
                return False

            # Write reports
            self._write_reports(cluster_id, check_results, creator, job_instance_id)
            return True

        except Exception as e:
            logger.exception(f"Error processing job {job_instance_id}: {e}")
            return False

    def _parse_results(self, log_content: str) -> Optional[List[Dict]]:
        """Parse the JSON results from script output."""
        match = CTX_PATTERN.search(log_content)
        if not match:
            return None

        try:
            context_str = match.group("context")
            result_data = json.loads(context_str)
            return result_data.get("results", [])
        except json.JSONDecodeError:
            return None

    def _write_reports(self, cluster_id: int, check_results: List[Dict], creator: str, job_instance_id: int):
        """Write check results to MetaCheckReport using existing utility function."""
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            logger.error(f"Cluster {cluster_id} not found")
            return

        for result in check_results:
            ip = result.get("ip", "")
            port = result.get("port", 0)
            meta_role = result.get("meta_role", "")
            actual_role = result.get("actual_role", "")
            role_match = result.get("match", False)
            error = result.get("error", "")

            if role_match:
                state = ReportStateType.NORMAL
                msg = f"Role matches: meta={meta_role}, actual={actual_role}"
            else:
                state = ReportStateType.ABNORMAL
                if error:
                    msg = f"Role check failed: {error} (job_instance_id={job_instance_id})"
                else:
                    msg = f"Role mismatch: meta={meta_role}, actual={actual_role} (job_instance_id={job_instance_id})"

            create_meta_check_report(
                cluster=cluster,
                ip=ip,
                port=port,
                subtype=MetaCheckSubType.RoleMismatch,
                msg=msg,
                state=state,
                creator=creator,
            )

    def _write_failure_report(self, job_info: Dict, creator: str):
        """Write failure report for a failed/timeout job."""
        cluster_id = job_info["cluster_id"]
        job_instance_id = job_info.get("job_instance_id", "")
        instances = job_info.get("instances", [])

        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            logger.error(f"Cluster {cluster_id} not found")
            return

        msg = f"Role check failed: job execution failed or timed out (job_instance_id={job_instance_id})"

        for inst in instances:
            create_meta_check_report(
                cluster=cluster,
                ip=inst.get("ip", ""),
                port=inst.get("port", 0),
                subtype=MetaCheckSubType.RoleMismatch,
                msg=msg,
                state=ReportStateType.ABNORMAL,
                creator=creator,
            )

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return []


class RedisRoleCheckReportComponent(Component):
    name = __name__
    code = "redis_role_check_report"
    bound_service = RedisRoleCheckReportService
