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

from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.es.es_script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


class ExecCloudScriptService(BkJobService):
    """云区域服务部署脚本执行类"""

    def _execute(self, data, parent_data):
        """
        执行fast_execute_script脚本
        global_data 单据全局变量，格式字典
        trans_data  单据上下文
        kwargs 字典传入格式：
        {
           root_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_name: db-actuator任务必须参数，做录入日志平台的条件
           get_hdfs_payload_func : 表示获取执行 hdfs的db-actuator 参数方法名称，对应HdfsActPayload类
           exec_ip: 表示执行的ip节点
        }
        """

        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_id = kwargs["node_id"]

        target_ip_info = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"], parse_cloud=True)

        if not target_ip_info:
            self.log_error(_("该节点{}获取到执行ip信息为空，请联系系统管理员").format(kwargs))
            return False

        # 获取服务部署所需要执行的参数, 只考虑从kwargs获取ticket_data，避免全局的ticket data修改后造成上下文污染
        ticket_data = kwargs.get("ticket_data")
        cloud_service_payload = CloudServiceActPayload(ticket_data=ticket_data, kwargs=kwargs)
        service_act_payload = getattr(cloud_service_payload, kwargs["get_payload_func"])()
        script_tpl = kwargs["script_tpl"]

        # 执行job任务
        resp = self._exec_job_task(
            script_tpl=script_tpl,
            service_act_payload=service_act_payload,
            target_ip_info=target_ip_info,
            kwargs=kwargs,
        )

        # 传入调用结果，并单调监听任务状态
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=target_ip_info)
        data.outputs.ext_result = resp
        data.outputs.exec_ips = target_ip_info
        return True

    def _exec_job_task(self, script_tpl, service_act_payload, target_ip_info, kwargs):
        """
        @param script_tpl: 脚本模板
        @param service_act_payload: 填充参数
        @param target_ip_info: 目标ip相关信息
        @param job_func: 脚本任务函数名
        @param kwargs: 传入的kwargs参数
        """

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(script_tpl)

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{kwargs['node_name']}_{kwargs['node_id']}",
            "script_content": base64_encode(template.render(service_act_payload)),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("[{}] ready start task with body {}".format(kwargs["node_name"], body))
        return JobApi.fast_execute_script({**fast_execute_script_common_kwargs, **body}, raw=True)

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class ExecCloudScriptComponent(Component):
    name = __name__
    code = "cloud_exec_script"
    bound_service = ExecCloudScriptService
