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
from backend.components import JobApi
from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.enums import (
    BkJobHostErrorCode,
    BkJobInstanceStatus,
    BkJobStepStatus,
)


def query_result(bk_scope_type: str, bk_scope_id: int, job_instance_id: int):
    get_job_status_body = {
        "bk_scope_type": bk_scope_type,
        "bk_scope_id": bk_scope_id,
        "job_instance_id": job_instance_id,
        "return_ip_result": True,
    }

    job_status_resp = JobApi.get_job_instance_status(get_job_status_body, use_admin=True)
    job_finished: bool = job_status_resp["finished"]
    job_status = BkJobInstanceStatus(job_status_resp["job_instance"]["status"])

    step_instance_list = job_status_resp.get("step_instance_list") or []
    if not step_instance_list:
        return {
            "job_finished": False,
            "job_status": job_status,
            "step_instance_id": None,
            "host_results": [],
        }

    step_instance_id = step_instance_list[0]["step_instance_id"]
    step_ip_result_list = step_instance_list[0].get("step_ip_result_list") or []

    bk_host_ids = []
    host_results = {}
    for step_ip_result in step_ip_result_list:
        ip = step_ip_result["ip"]
        bk_cloud_id = step_ip_result["bk_cloud_id"]
        bk_host_id = step_ip_result["bk_host_id"]
        step_ip_status = BkJobStepStatus(step_ip_result["status"])
        step_ip_exit_code = step_ip_result["exit_code"]
        step_ip_host_error_code = BkJobHostErrorCode(step_ip_result["error_code"])

        bk_host_ids.append(bk_host_id)
        host_results[bk_host_id] = {
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
            "bk_host_id": bk_host_id,
            "status": step_ip_status,
            "exit_code": step_ip_exit_code,
            "error_code": step_ip_host_error_code,
        }

    if bk_host_ids:
        get_step_ip_log_body = {
            "bk_scope_type": bk_scope_type,
            "bk_scope_id": bk_scope_id,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "host_id_list": bk_host_ids,
        }
        step_ip_log_resp = JobApi.batch_get_job_instance_ip_log(get_step_ip_log_body, use_admin=True)
        for script_task_log in step_ip_log_resp["script_task_logs"]:
            bk_host_id = script_task_log["host_id"]
            log_content = script_task_log["log_content"]

            if bk_host_id in host_results:
                host_results[bk_host_id]["log_content"] = log_content

    return {
        "job_finished": job_finished,
        "job_status": job_status,
        "step_instance_id": step_instance_id,
        "host_results": list(host_results.values()),
    }
