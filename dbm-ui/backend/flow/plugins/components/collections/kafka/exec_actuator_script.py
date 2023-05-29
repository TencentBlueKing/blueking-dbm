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
from typing import List

from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.kafka.script_template import ACTUATOR_TEMPLATE, fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


class ExecuteDBActuatorScriptService(BkJobService):
    """
    根据db-actuator组件，绑定fast_execute_script api接口访问。
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
           get_mysql_payload_func : 表示获取执行 mysql的db-actuator 参数方法名称，对应MysqlActPayload类
           exec_ip: 表示执行的ip节点
           get_trans_data_ip_name: 表示从上下文获取到执行ip的变量名，对应单据的获取到上下文dataclass类
           cluster: 操作的集群名称

        }
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]
        exec_ips = kwargs["exec_ip"]

        self.log_info("nome_name = {} , exec_ips = {}".format(node_name, exec_ips))
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip["ip"]} for ip in exec_ips]

        # 获取kafka actuator 组件所需要执行的参数,
        db_act_template = kwargs["template"]
        db_act_template["root_id"] = root_id
        db_act_template["node_id"] = node_id
        db_act_template["version_id"] = self._runtime_attrs["version"]
        db_act_template["uid"] = global_data["uid"]

        db_act_template["payload"] = base64_encode(json.dumps(db_act_template["payload"]))

        FlowNode.objects.filter(root_id=kwargs["root_id"], node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(ACTUATOR_TEMPLATE)

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(template.render(db_act_template)),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**fast_execute_script_common_kwargs, **body}, raw=True)
        # 传入调用结果，并单调监听任务状态
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


class ExecuteDBActuatorScriptComponent(Component):
    name = __name__
    code = "kafka_db_actuator_execute"
    bound_service = ExecuteDBActuatorScriptService
