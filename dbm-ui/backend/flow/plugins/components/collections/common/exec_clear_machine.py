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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.clear_machine_script import (
    db_type_account_user_map,
    db_type_script_map,
    os_script_language_map,
)
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


class ClearMachineScriptService(BkJobService):
    """
    根据db-actuator组件，绑定fast_execute_script api接口访问。
    同时支持跨云管理
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行fast_execute_script脚本
        global_data 单据全局变量，格式字典
        trans_data  单据上下文
        kwargs 字典传入格式：
        {
           root_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_name: db-actuator任务必须参数，做录入日志平台的条件
        }
        """
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]
        exec_ips = kwargs["exec_ips"]
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        # 更新节点信息
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        body = {
            "timeout": kwargs.get("job_timeout", 3600),
            "account_alias": db_type_account_user_map[global_data["db_type"]],
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(db_type_script_map[global_data["db_type"]]),
            "script_language": os_script_language_map[global_data["os_name"]],
            "target_server": {"ip_list": exec_ips},
        }
        self.log_debug("[{}] ready start task with body {}".format(node_name, body))

        resp = JobApi.fast_execute_script(body, raw=True)
        self.log_debug(f"{node_name} fast execute script response: {resp}")
        self.log_info(f"job url:{env.BK_JOB_URL}/api_execute/{resp['data']['job_instance_id']}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class ClearMachineScriptComponent(Component):
    name = __name__
    code = "common_clear_machine_execute"
    bound_service = ClearMachineScriptService
