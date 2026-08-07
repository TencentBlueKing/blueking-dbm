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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.string import base64_encode


class ProbeExecuteShellScriptService(BkJobService):
    """
    Execute shell command on target hosts.
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]
        account_alias = kwargs.get("account_alias")

        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
            return False
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        shell_command = kwargs["cluster"]["shell_command"]

        try:
            # 从数据库中查询最新的 admin_endpoints
            from backend.db_proxy.models import DBExtension

            admin_endpoints = DBExtension.get_dbha_v2_admin_endpoints()
            # 替换占位符
            shell_command = shell_command.replace("${ADMIN_ENDPOINTS}", admin_endpoints)
            self.log_info(f"[{node_name}] get admin_endpoints: {admin_endpoints}")
        except Exception as e:
            self.log_error(f"[{node_name}] get admin_endpoints failed: {str(e)}")

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(shell_command),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        if account_alias:
            body["account_alias"] = account_alias

        self.log_info("[{}] ready start task with body {}".format(node_name, body))
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


class ProbeExecuteShellScriptComponent(Component):
    name = __name__
    code = "common_probe_exec_shell_script"
    bound_service = ProbeExecuteShellScriptService
