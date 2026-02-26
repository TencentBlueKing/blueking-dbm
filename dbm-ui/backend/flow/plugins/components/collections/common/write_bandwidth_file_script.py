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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.es.es_script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


class WriteBandwidthFileScriptService(BkJobService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_id = kwargs["node_id"]
        node_name = kwargs["node_name"]
        ips = kwargs["ips"]
        bandwidth = kwargs["bandwidth"]

        if not ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(ips))

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in ips]

        # 更新节点信息
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=ips)

        # 脚本内容
        script_content = f'echo "{bandwidth}" > /etc/dbm_bandwidth'

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM write bandwidth file",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_debug("[{}] ready start task with body {}".format(node_name, body))

        resp = JobApi.fast_execute_script({**fast_execute_script_common_kwargs, **body}, raw=True)

        self.log_debug(f"{node_name} fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")
        if (resp.get("result") is not True) or (int(resp["code"] != 0)):
            raise Exception(f"{str(resp)}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = ips
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class WriteBandwidthFileScriptComponent(Component):
    name = __name__
    code = "write_bandwidth_file"
    bound_service = WriteBandwidthFileScriptService
