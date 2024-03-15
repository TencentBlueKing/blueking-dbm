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

import copy
import logging

from django.utils.translation import ugettext as _
from jinja2 import Environment
from pipeline.component_framework.component import Component

from backend.components import JobApi
from backend.core import consts
from backend.flow.plugins.components.collections.cloud.exec_service_script import ExecCloudScriptService
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


class PushConfigFiletService(ExecCloudScriptService):
    """
    云区域服务部署文件下发类
    逻辑与脚本执行类似，因此继承二次开发
    """

    def _exec_job_task(self, script_tpl, service_act_payload, target_ip_info, kwargs):
        """
        @param script_tpl: 脚本模板
        @param service_act_payload: 填充参数
        @param target_ip_info: 目标ip相关信息
        @param kwargs: 传入的kwargs参数
        """

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(script_tpl)

        payload = copy.deepcopy(consts.BK_PUSH_CONFIG_PAYLOAD)
        payload["task_name"] = f"{kwargs['node_name']}_{kwargs['node_id']}"
        payload["file_list"] = [
            {
                "file_name": kwargs["conf_file_name"],
                "content": base64_encode(template.render(service_act_payload)),
            }
        ]
        payload["target_server"]["ip_list"] = target_ip_info

        self.log_info(_("[{}] 下发介质包参数：{}").format(kwargs["node_name"], payload))
        return JobApi.push_config_file(payload, raw=True)


class PushConfigFiletComponent(Component):
    name = __name__
    code = "cloud_push_conf_file"
    bound_service = PushConfigFiletService
