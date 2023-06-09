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
from bamboo_engine import states
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend import env
from backend.components.sops.client import BkSopsApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class SaInit(BaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)
    """_summary_
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        iplist = kwargs["ips"]
        bk_biz_id = kwargs["bk_biz_id"]
        param = {
            "template_id": env.SA_INIT_TEMPLATE_ID,
            "bk_biz_id": bk_biz_id,
            "template_source": "common",
            "name": _("SA初始化"),
            "flow_type": "common",
            "constants": {
                "${biz_cc_id}": bk_biz_id,
                "${job_ip_list}": "\n".join(iplist),
            },
        }
        rpdata = BkSopsApi.create_task(param)
        task_id = rpdata["task_id"]
        # start task
        self.log_info(f"task_id: {task_id}")
        self.log_info(f"job url:{env.BK_SOPS_URL}/askflow/home/list/{task_id}")
        param = {"bk_biz_id": bk_biz_id, "task_id": task_id}
        BkSopsApi.start_task(param)
        data.outputs.task_id = task_id
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = kwargs["bk_biz_id"]
        task_id = data.get_one_of_outputs("task_id")
        param = {"bk_biz_id": bk_biz_id, "task_id": task_id}
        rpdata = BkSopsApi.query_task_status(param)
        state = rpdata["state"]
        children = rpdata["children"]
        if state == states.FINISHED:
            self.finish_schedule()
            self.log_info("run success~")
            return True
        if state in [states.FAILED, states.REVOKED, states.SUSPENDED]:
            if state == states.FAILED:
                self.log_error(_("空闲检查失败"))
            else:
                self.log_error(_("任务状态异常{}").format(state))
            # 查询异常日志
            for nodeid in children:
                param["node_id"] = nodeid
                rpdata = BkSopsApi.task_node_detail(param)
                ouput = rpdata["outputs"]
                ex_data = rpdata["ex_data"]
                self.log_error(f"ex_data:{ex_data}")
                for ele in ouput:
                    self.log_error(f"ouput:{ele}")
            return False


class SaInitComponent(Component):
    name = _("sa初始化")
    code = "sa_machine_init"
    bound_service = SaInit
