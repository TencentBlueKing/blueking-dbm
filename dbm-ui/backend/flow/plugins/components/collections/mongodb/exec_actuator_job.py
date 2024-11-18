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
import json
import logging
import re
from typing import List

from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.mongodb.mongodb_dataclass as flow_context
from backend import env
from backend.components import JobApi
from backend.flow.consts import MongoDBManagerUser
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.mongodb.mongodb_script_template import (
    make_script_common_kwargs,
    mongodb_actuator_template,
    mongodb_create_actuator_dir_template,
    mongodb_os_init_actuator_template,
    mongodb_stop_old_dbmon_script,
)

logger = logging.getLogger("json")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class ExecuteDBActuatorJobService(BkJobService):
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
           get_redis_payload_func : 表示获取执行 redis的db-actuator 参数方法名称，对应RedisActPayload类
           exec_ip: 表示执行的ip节点
           get_trans_data_ip_name: 表示从上下文获取到执行ip的变量名，对应单据的获取到上下文dataclass类
           cluster: 操作的集群名称
           extend_attr: 额外的字段数据，需要从RedisApplyContext中获取
        }
        """

        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        # 创建db管理员账号，从上游流程节点获取密码
        if kwargs.get("create_manager_user", False):
            if kwargs["set_name"]:
                kwargs["db_act_template"]["payload"]["password"] = trans_data[kwargs["set_name"]][
                    kwargs["db_act_template"]["payload"]["username"]
                ]
            else:
                kwargs["db_act_template"]["payload"]["password"] = trans_data[
                    kwargs["db_act_template"]["payload"]["username"]
                ]

        # 创建额外管理员账号
        if kwargs.get("create_extra_manager_user", False):
            script = kwargs["db_act_template"]["payload"]["script"]
            if kwargs["set_name"]:
                kwargs["db_act_template"]["payload"]["adminPassword"] = trans_data[kwargs["set_name"]][
                    kwargs["db_act_template"]["payload"]["adminUsername"]
                ]
                script = script.replace(
                    "{{appdba_pwd}}", trans_data[kwargs["set_name"]][MongoDBManagerUser.AppDbaUser]
                )
                script = script.replace(
                    "{{monitor_pwd}}", trans_data[kwargs["set_name"]][MongoDBManagerUser.MonitorUser]
                )
                script = script.replace(
                    "{{appmonitor_pwd}}", trans_data[kwargs["set_name"]][MongoDBManagerUser.AppMonitorUser]
                )
            else:
                kwargs["db_act_template"]["payload"]["adminPassword"] = trans_data[
                    kwargs["db_act_template"]["payload"]["adminUsername"]
                ]
                script = script.replace("{{appdba_pwd}}", trans_data[MongoDBManagerUser.AppDbaUser])
                script = script.replace("{{monitor_pwd}}", trans_data[MongoDBManagerUser.MonitorUser])
                script = script.replace("{{appmonitor_pwd}}", trans_data[MongoDBManagerUser.AppMonitorUser])
            kwargs["db_act_template"]["payload"]["script"] = script

        # 进行db初始设置获，从上游流程节点获取密码
        if kwargs.get("db_init_set", False):
            if kwargs["set_name"]:
                kwargs["db_act_template"]["payload"]["adminPassword"] = trans_data[kwargs["set_name"]][
                    kwargs["db_act_template"]["payload"]["adminUsername"]
                ]
            else:
                kwargs["db_act_template"]["payload"]["adminPassword"] = trans_data[
                    kwargs["db_act_template"]["payload"]["adminUsername"]
                ]

        # cluster添加shards，从上游流程节点获取密码
        if kwargs.get("add_shard_to_cluster", False):
            kwargs["db_act_template"]["payload"]["adminPassword"] = trans_data[
                kwargs["db_act_template"]["payload"]["adminUsername"]
            ]

        # 替换mongos安装新的mongos获取configDB配置  所有的mongos修改configDB参数
        mongos_replace_install = kwargs.get("mongos_replace_install", False)
        all_mongos_change_configdb = kwargs.get("all_mongos_change_configdb", False)
        if mongos_replace_install or all_mongos_change_configdb:
            act_kwargs = ActKwargs()
            act_kwargs.payload = {}
            act_kwargs.get_cluster_info_deinstall(cluster_id=kwargs["cluster_id"])
            if mongos_replace_install:
                config_db = [
                    "{}:{}".format(node["ip"], str(node["port"])) for node in act_kwargs.payload["config_nodes"]
                ]
                kwargs["db_act_template"]["payload"]["configDB"] = config_db
            elif all_mongos_change_configdb:
                kwargs["exec_ip"] = [node["ip"] for node in act_kwargs.payload["mongos_nodes"]]
                kwargs["db_act_template"]["payload"]["port"] = act_kwargs.payload["mongos_nodes"][0]["port"]

        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs["get_trans_data_ip_var"]:
            exec_ips = self.splice_exec_ips_list(
                ticket_ips=kwargs["exec_ip"], pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"])
            )
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, kwargs["node_name"]))

        # 获取 actuator 组件所需要执行的参数,
        db_act_template = kwargs["db_act_template"]
        db_act_template["root_id"] = root_id
        db_act_template["node_id"] = node_id
        db_act_template["version_id"] = self._runtime_attrs["version"]
        db_act_template["uid"] = global_data["uid"]
        db_act_template["payload"] = str(
            base64.b64encode(json.dumps(db_act_template["payload"]).encode("utf-8")), "utf-8"
        )

        FlowNode.objects.filter(root_id=kwargs["root_id"], node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        jinja_env = Environment()
        exec_account = "root"
        template = jinja_env.from_string(mongodb_actuator_template)
        if kwargs.get("init_flag", False):
            template = jinja_env.from_string(mongodb_os_init_actuator_template)
        elif kwargs.get("create_dir", False):
            template = jinja_env.from_string(mongodb_create_actuator_dir_template)
        elif kwargs.get("stop_old_dbmon", False):
            template = jinja_env.from_string(mongodb_stop_old_dbmon_script)
            exec_account = "mysql"
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(template.render(db_act_template).encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info(
            "[{}] ready start task with body {} {}".format(
                node_name, make_script_common_kwargs(exec_account=exec_account), body
            )
        )
        resp = JobApi.fast_execute_script({**make_script_common_kwargs(exec_account=exec_account), **body}, raw=True)

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


class ExecuteDBActuatorJobComponent(Component):
    name = __name__
    code = "mongodb_db_actuator_execute"
    bound_service = ExecuteDBActuatorJobService
