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

from typing import List

from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode


def exec_cluster_query_net_tcp_cmd(target_ips: List) -> dict:
    cmds = """head -n 30000 /proc/net/tcp;"""
    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": _("查询集群接入层tcp的连接信息"),
        "script_content": base64_encode(cmds),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": 300,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    return job_task


def get_job_exec_status(job_instance_id: str):
    payload = {"bk_biz_id": env.JOB_BLUEKING_BIZ_ID, "job_instance_id": job_instance_id, "return_ip_result": True}
    resp = JobApi.get_job_instance_status(payload, use_admin=True)

    # job 未完成
    if not resp["finished"]:
        return {"finished": False, "job_log_resp": []}

    ip_result_list = resp["step_instance_list"][0]["step_ip_result_list"]

    # 执行完成直接获取主机执行的日志，不用判断是否有报错
    step_instance_id = resp["step_instance_list"][0]["step_instance_id"]
    bk_host_ids = [result["bk_host_id"] for result in resp["step_instance_list"][0]["step_ip_result_list"]]
    resp = JobApi.batch_get_job_instance_ip_log(
        {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "host_id_list": bk_host_ids,
        },
        use_admin=True,
    )
    script_task_logs = resp["script_task_logs"] or []

    # 保持兼容性，对于没有查到日志的主机填空
    log_host_ids = [log["host_id"] for log in script_task_logs]
    add_empty_task_logs = [
        {"host_id": res["bk_host_id"], "log_content": "", "bk_cloud_id": res["bk_cloud_id"], "ip": res["ip"]}
        for res in ip_result_list
        if res["bk_host_id"] not in log_host_ids
    ]
    script_task_logs.extend(add_empty_task_logs)
    return {"finished": True, "job_log_resp": script_task_logs}
