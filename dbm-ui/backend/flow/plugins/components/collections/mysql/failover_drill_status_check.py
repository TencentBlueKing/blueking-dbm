"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service, StaticIntervalGenerator

import backend.flow.utils.mysql.mysql_context_dataclass as flow_context
from backend.components.hadb.client import HADBApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

# 设置30秒轮询一次
SCHEDULE_INTERVAL = 6
# dbha状态检查为10分钟，超时必然有问题
CHECK_TIMEOUT = 10 * 60
# MAX_SCHEDULE_COUNT = math.ceil(CHECK_TIMEOUT / SCHEDULE_INTERVAL)
MAX_SCHEDULE_COUNT = 20


class FailoverStatusCheckService(BaseService):
    """
    用于轮询检查dbha切换状态
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(SCHEDULE_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["trans_data_dataclass"])()

        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        loop_count = data.get_one_of_outputs("loop_count")
        if not loop_count:
            loop_count = 0

        self.log_info(
            "schedule:{}/{},schedule interval:{} seconds".format(loop_count, MAX_SCHEDULE_COUNT, SCHEDULE_INTERVAL)
        )
        try:
            self.log_info(_("Start checking DBHA service status."))
            resp = HADBApi.switch_queue(params={"name": "query_switch_queue", "query_args": kwargs}, raw=True)
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                resp_data = resp["data"]
                for d in resp_data:
                    if d["ip"] == kwargs["ip"]:
                        self.finish_schedule()
                        return True
                self.log_info("waiting for the status change!")
            else:
                self.log_error("HADB service query failed. code:{} msg:{}".format(code, msg))

        except Exception as e:
            self.log_exception("HADB service query error:{}".format(e))
            # 异常不做处理，跳过进行下一次请求
            # self.finish_schedule()
            # return False

        if loop_count >= MAX_SCHEDULE_COUNT:
            self.log_info("HADB service query timeout!Exit polling state.")
            # 超时只结束当前节点，不去报错，继续下一步
            self.finish_schedule()
        else:
            loop_count += 1
            data.set_outputs("loop_count", loop_count)

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class FailoverStatusCheckComponent(Component):
    name = __name__
    code = "failover_status_check"
    bound_service = FailoverStatusCheckService
