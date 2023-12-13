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
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkSopsService


class L5AgentInstall(BkSopsService):
    def _execute(self, data, parent_data) -> bool:
        """
        定义调用异步接口内容
        """
        kwargs = data.get_one_of_inputs("kwargs")
        ip = kwargs["ip"]
        bk_host_id = kwargs["bk_host_id"]

        # 先获取机器所在的bk_biz_id
        res = CCApi.find_host_biz_relations({"bk_host_id": [bk_host_id]})
        bk_biz_id = res[0]["bk_biz_id"]

        try:
            # 发起异步标准运维接口
            rp_data = BkSopsApi.create_task(
                {
                    "template_id": env.SA_L5_AGENT_TEMPLATE_ID,
                    "bk_biz_id": bk_biz_id,
                    "template_source": "common",
                    "name": _("安装L5 agent"),
                    "flow_type": "common",
                    "constants": {
                        "${biz_cc_id}": bk_biz_id,
                        "${job_ip_list}": ip,
                        "${job_account}": DBA_ROOT_USER,
                    },
                }
            )

            # 捕捉接口返回接口，判断是否创建任务正常
            task_id = rp_data["task_id"]
            # start task
            self.log_info(f"task_id: {task_id}")
            self.log_info(
                f"job url:{env.BK_SOPS_URL}/taskflow/execute/{env.BK_SOPS_PROJECT_ID}/?instance_id={task_id}"
            )
            param = {"bk_biz_id": bk_biz_id, "task_id": task_id}
            BkSopsApi.start_task(param)
            data.outputs.task_id = task_id
            data.outputs.bk_biz_id = bk_biz_id

        except Exception as err:
            self.log_error(f"create task is err : [{err}]")
        return True


class L5AgentInstallComponent(Component):
    name = _("L5agent安装")
    code = "L5_agent_install"
    bound_service = L5AgentInstall
