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


def exec_redis_capture_tool_cmd(target_ips: List, timeout, port, grep_cmd) -> dict:
    cmds = f"""
            iface=`ip -o route get 1.1.1.1 | awk '{{print $5}}' || echo "ech1"`
            ip=`/sbin/ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{{print $2}}'|tr -d "addr:"`
            /home/mysql/dbtools/myRedisCapture -d ${{iface}} -i ${{ip}} -p {port} -t {timeout} | {grep_cmd}
        """
    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": _("执行redis抓请求工具"),
        "script_content": base64_encode(cmds),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": 300,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    return job_task


def generate_redis_capture_report(
    job_log_resp,
):
    result_msg = []
    for info in job_log_resp:
        # 先把结果直接原样返回，后面再来考虑要怎么去处理
        try:
            if info["log_content"]:
                result_msg.append(info["log_content"])
        except (Exception, IndexError):
            pass

    return result_msg
