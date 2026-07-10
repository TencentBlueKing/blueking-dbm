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
import logging
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


class MysqlDtsExecShellService(BkJobService):
    """在目标机器上执行 DTS 部署/清理 shell 脚本。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_targets = kwargs.get("exec_targets") or []
        shell_script = kwargs.get("shell_script", "")
        if not exec_targets:
            self.log_error(_("该节点执行目标为空，请联系系统管理员"))
            return False
        if not shell_script:
            self.log_error(_("该节点 shell 脚本为空，请联系系统管理员"))
            return False

        target_ip_info = [{"bk_cloud_id": t["bk_cloud_id"], "ip": t["ip"]} for t in exec_targets]
        exec_ips = [{"ip": t["ip"], "bk_cloud_id": t["bk_cloud_id"]} for t in exec_targets]
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=[t["ip"] for t in exec_targets])

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(shell_script),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
            "account_alias": kwargs.get("run_as_system_user", DBA_ROOT_USER),
        }
        if kwargs.get("job_timeout"):
            body["timeout"] = kwargs["job_timeout"]

        self.log_info(_("[{}] 执行 DTS shell 脚本，目标: {}").format(node_name, target_ip_info))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class MysqlDtsExecShellComponent(Component):
    name = __name__
    code = "mysql_dts_exec_shell"
    bound_service = MysqlDtsExecShellService
