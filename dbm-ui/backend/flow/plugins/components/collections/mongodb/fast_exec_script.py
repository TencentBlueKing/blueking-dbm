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
import base64
import logging
import re
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.mongodb.mongodb_dataclass as flow_context
from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.mongodb.mongodb_script_template import make_script_common_kwargs

logger = logging.getLogger("json")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class _ExecBkJobService(BkJobService):
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
           exec_ip: 表示执行的ip节点
           get_trans_data_ip_name: 表示从上下文获取到执行ip的变量名，对应单据的获取到上下文dataclass类
           extend_attr: 额外的字段数据，需要从RedisApplyContext中获取
        }
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        self.log_info("_execute trans_data {} global_data {} kwargs {}".format(trans_data, global_data, kwargs))
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
            self.log_info("now init trans_data {}".format(trans_data))

        self.log_info("trans_data {}".format(trans_data))

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        ticket_ips = []
        # get ip from bk_host_list
        for v in kwargs["bk_host_list"]:
            ticket_ips.append(v["ip"])
        exec_ips = self.splice_exec_ips_list(ticket_ips=ticket_ips)
        self.log_info("exec_ips {}".format(exec_ips))
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        self.log_info("kwargs {}".format(kwargs))
        self.log_info("data {}".format(data))

        target_ip_info = kwargs["bk_host_list"]
        self.log_info("{} exec {}".format(target_ip_info, kwargs["node_name"]))

        # 获取 actuator 组件所需要执行的参数
        """
        jinja_env = Environment()
        template = jinja_env.from_string(kwargs["script_content"])
        db_act_template = kwargs["db_act_template"]
        db_act_template["root_id"] = root_id
        db_act_template["node_id"] = node_id
        db_act_template["version_id"] = self._runtime_attrs["version"]
        db_act_template["uid"] = global_data["uid"]
        db_act_template["payload"] = str(
            base64.b64encode(json.dumps(db_act_template["payload"]).encode("utf-8")), "utf-8"
        )
        """
        # 这一段是为了替换脚本中的模板，但我们现在不需要替换，所以注释掉

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)
        # 拼接fast_execute_script 接口请求参数
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(kwargs["script_content"].encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info("[{}] ready start task with body {} {}".format(node_name, "", body))
        resp = JobApi.fast_execute_script(
            {**(make_script_common_kwargs(timeout=3600, exec_account=kwargs["exec_account"])), **body}, raw=True
        )

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        trans_data.set("step1", "step1")
        data.outputs["trans_data"] = trans_data
        self.log_info("[{}] set trans_data {} {}".format(node_name, "", trans_data))
        return True

    @staticmethod
    def inputs_format() -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    @staticmethod
    def outputs_format() -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class MongoFastExecScriptComponent(Component):
    name = __name__
    code = "MongoFastExecScript"
    bound_service = _ExecBkJobService
