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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import CCApi
from backend.components.sops.client import BkSopsApi
from backend.flow.plugins.components.collections.common.base_service import BkSopsService


class CheckMachineIdleCheck(BkSopsService):
    def __get_bk_biz_id_for_ip(self, ip: str, bk_cloud_id: int):

        # 先通过ip获取对应的bk_host_id
        res = CCApi.list_hosts_without_biz(
            {
                "fields": ["bk_host_id"],
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "in", "value": [ip]},
                        {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                    ],
                },
            },
            use_admin=True,
        )
        bk_host_id = res["info"][0]["bk_host_id"]
        self.log_info(f"the bk_host_id of machine [{ip}] is {bk_host_id}")

        # 再通过bk_host_id获取
        res = CCApi.find_host_biz_relations({"bk_host_id": [bk_host_id]})
        return res[0]["bk_biz_id"]

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        ips = kwargs["ips"]
        # 获取业务id
        if kwargs.get("bk_biz_id"):
            bk_biz_id = kwargs["bk_biz_id"]
        else:
            # 否则认为你这一批的机器都是来自于同一个业务上，则已其中一个ip获取的业务id为准
            bk_biz_id = self.__get_bk_biz_id_for_ip(ip=ips[0], bk_cloud_id=int(kwargs["bk_cloud_id"]))

        param = {
            "template_id": env.SA_CHECK_TEMPLATE_ID,
            "bk_biz_id": bk_biz_id,
            "template_source": "common",
            "name": _("空闲检查FOR_DBM"),
            "flow_type": "common",
            "constants": {
                "${biz_cc_id}": bk_biz_id,
                "${job_ip_list}": "\n".join(ips),
                "${job_account}": "root",
            },
        }
        rpdata = BkSopsApi.create_task(param)
        task_id = rpdata["task_id"]
        # start task
        self.log_info(f"job url:{env.BK_SOPS_URL}/taskflow/execute/{env.BK_SOPS_PROJECT_ID}/?instance_id={task_id}")
        param = {"bk_biz_id": bk_biz_id, "task_id": task_id}
        BkSopsApi.start_task(param)
        data.outputs.task_id = task_id
        data.inputs.kwargs["bk_biz_id"] = bk_biz_id
        return True


class CheckMachineIdleComponent(Component):
    name = _("sa空闲检查")
    code = "sa_idle_check"
    bound_service = CheckMachineIdleCheck
