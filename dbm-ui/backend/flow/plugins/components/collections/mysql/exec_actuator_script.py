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
import copy
import json
import logging
import re
from dataclasses import asdict, is_dataclass

from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.mysql.common.get_mysql_sys_user import get_mysql_sys_users
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.script_template import actuator_template, fast_execute_script_common_kwargs

logger = logging.getLogger("json")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class ExecuteDBActuatorScriptService(BkJobService):
    """
    根据db-actuator组件，绑定fast_execute_script api接口访问。
    目前只能兼容传入一个ip执行，如果传入多ip列表模块，会有可能影响payload的拼接情况
    同时支持跨云管理，根据传入的 kwargs["bk_cloud_id"]来执行
    """

    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs.get("get_trans_data_ip_var"):
            exec_ips = self.splice_exec_ips_list(pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"]))
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        return exec_ips

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
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]

        # 获取mysql actuator 组件所需要执行的参数
        mysql_act_payload = MysqlActPayload(
            bk_cloud_id=kwargs["bk_cloud_id"],
            ticket_data=global_data,
            cluster=kwargs.get("cluster", None),
            cluster_type=kwargs.get("cluster_type", None),
        )
        if is_dataclass(trans_data):
            trans_data = asdict(trans_data)

        db_act_template = getattr(mysql_act_payload, kwargs["get_mysql_payload_func"])(
            ip=exec_ips[0], trans_data=trans_data
        )
        db_act_template["root_id"] = root_id
        db_act_template["node_id"] = node_id
        db_act_template["version_id"] = self._runtime_attrs.get("version")
        db_act_template["uid"] = global_data["uid"]

        # 拼接mysql系统账号固定参数
        if "general" in db_act_template["payload"]:
            db_act_template["payload"]["general"].update(
                {"runtime_extend": {"mysql_sys_users": get_mysql_sys_users(kwargs["bk_cloud_id"])}}
            )

        # payload参数转换base64格式
        db_act_template["payload"] = str(
            base64.b64encode(json.dumps(db_act_template["payload"]).encode("utf-8")), "utf-8"
        )
        FlowNode.objects.filter(root_id=kwargs["root_id"], node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(actuator_template)

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(template.render(db_act_template).encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("[{}] ready start task with body {}".format(node_name, body))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        if kwargs.get("run_as_system_user"):
            common_kwargs["account_alias"] = kwargs["run_as_system_user"]
        else:
            # 现在默认使用root账号来执行
            common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"{node_name} fast execute script response: {resp}")
        self.log_info(f"job url:{env.BK_JOB_URL}/api_execute/{resp['data']['job_instance_id']}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class ExecuteDBActuatorScriptComponent(Component):
    name = __name__
    code = "mysql_db_actuator_execute"
    bound_service = ExecuteDBActuatorScriptService
