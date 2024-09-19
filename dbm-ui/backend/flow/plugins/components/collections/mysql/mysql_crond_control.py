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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


class MysqlCrondMonitorControlService(BkJobService):
    """
    执行shell命令
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_id = kwargs["node_id"]
        node_name = kwargs["node_name"]

        exec_ips = kwargs["exec_ips"]
        if not exec_ips:
            self.log_error(_("执行ip信息为空，请联系系统管理员"))
            return False
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)
        cmd_str = "cd /home/mysql/mysql-crond && ./mysql-crond "
        if kwargs["enable"]:
            cmd_str += " enable-job"
        else:
            cmd_str += " pause-job -r {}m".format(kwargs["minutes"])
        if kwargs["port"] == 0:
            cmd_str += " --name-match mysql-monitor-.*"
        else:
            cmd_str += " --name-match mysql-monitor-{}-.*".format(kwargs["port"])
        if kwargs["name"] != "":
            cmd_str += " --name {}".format(kwargs["name"])
        self.log_info(cmd_str)
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(cmd_str),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**fast_execute_script_common_kwargs, **body}, raw=True)
        self.log_info(f"{node_name} fast execute script response: {resp}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class MysqlCrondMonitorControlComponent(Component):
    name = __name__
    code = "mysql_crond_monitor_control"
    bound_service = MysqlCrondMonitorControlService
