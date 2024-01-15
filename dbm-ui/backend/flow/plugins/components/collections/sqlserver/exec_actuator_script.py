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
import json
import logging
import re
from dataclasses import asdict, is_dataclass

from django.conf import settings
from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import sqlserver_actuator_template
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload

logger = logging.getLogger("json")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class SqlserverActuatorScriptService(BkJobService):
    """
    根据db-actuator组件，绑定fast_execute_script api接口访问。
    目前只能兼容传入一个ip执行，如果传入多ip列表模块，会有可能影响payload的拼接情况
    同时支持跨云管理，根据传入的 kwargs["bk_cloud_id"]来执行
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
           get_mssql_payload_func : 表示获取执行 mssql的db-actuator 参数方法名称，对应MssqlActPayload类
           exec_ips: 表示执行的ip节点列表, 列表元素: {ip:xxx, bk_cloud_id:xxx}
           cluster: 操作的集群名称

        }
        """
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_ips = kwargs["exec_ips"]
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        # 获取sqlserver actuator 组件所需要执行的参数
        mssql_act_payload = SqlserverActPayload(global_data=global_data)
        if is_dataclass(trans_data):
            trans_data = asdict(trans_data)

        db_act_template = getattr(mssql_act_payload, kwargs["get_payload_func"])(ips=exec_ips, trans_data=trans_data)
        db_act_template.update(
            {
                "root_id": root_id,
                "node_id": node_id,
                "version_id": self._runtime_attrs.get("version"),
                "uid": global_data["uid"],
            }
        )

        # payload参数转换base64格式
        db_act_template["payload"] = str(
            base64.b64encode(json.dumps(db_act_template["payload"]).encode("utf-8")), "utf-8"
        )
        # 更新节点信息
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(sqlserver_actuator_template)

        body = {
            "timeout": kwargs.get("job_timeout", 3600),
            "account_alias": "system",
            "is_param_sensitive": 1,
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(template.render(db_act_template).encode("utf-8")), "utf-8"),
            "script_language": 5,
            "target_server": {"ip_list": exec_ips},
            "script_param": str(base64.b64encode(json.dumps(db_act_template["payload"]).encode("utf-8")), "utf-8"),
        }
        self.log_debug("[{}] ready start task with body {}".format(node_name, body))

        if settings.DEBUG:
            # debug模式下打开
            body["is_param_sensitive"] = 0

        resp = JobApi.fast_execute_script(body, raw=True)
        self.log_debug(f"{node_name} fast execute script response: {resp}")
        self.log_info(f"job url:{env.BK_JOB_URL}/api_execute/{resp['data']['job_instance_id']}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class SqlserverActuatorScriptComponent(Component):
    name = __name__
    code = "sqlserver_db_actuator_execute"
    bound_service = SqlserverActuatorScriptService
