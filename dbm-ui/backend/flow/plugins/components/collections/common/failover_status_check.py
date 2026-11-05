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
from datetime import datetime, timedelta, timezone
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service, StaticIntervalGenerator

import backend.flow.utils.common_act_dataclass as flow_context
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_report.models.failover_drill_report import FailoverDrillReport
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.failover_drill_dbha import query_switch_queue

logger = logging.getLogger("flow")

# Timeout = 3 min
SCHEDULE_INTERVAL = 6  # sec
MAX_SCHEDULE_COUNT = 30
# 单次查询只试一次、短超时：接口挂起时不能让轮询窗口（期间演练主机处于屏蔽状态）被拉长
QUERY_TIMEOUT = 10  # sec
QUERY_RETRY_TIMES = 1


class FailoverStatusCheckService(BaseService):
    """
    容灾演练 DBHA 监测
    一旦发生切换或超时就结束任务
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(SCHEDULE_INTERVAL)

    def report_trigger_time(self, main_task_id, instance_type):
        utc8_timezone = timezone(timedelta(hours=8))
        trigger_time = datetime.now().astimezone(utc8_timezone)
        FailoverDrillReport.objects.filter(main_task_id=main_task_id, instance_type=instance_type).update(
            trigger_dbha_time=trigger_time
        )

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["trans_data_dataclass"])()

        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        dbha_version = kwargs.get("dbha_version", FailoverDrillVersion.V1.value)
        finished_time = datetime.now().astimezone(timezone.utc)
        start_time = finished_time - timedelta(minutes=10)
        kwargs["switch_start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        kwargs["switch_finished_time"] = finished_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        loop_count = data.get_one_of_outputs("loop_count")
        if not loop_count:
            loop_count = 0

        if loop_count == 0:
            # 第一次轮询，记录开始触发dbha时间，这个时间点比较靠近触发dbha的时间点
            self.report_trigger_time(kwargs["main_task_id"], kwargs["instance_role"])

        self.log_info(
            "schedule:{}/{},schedule interval:{} seconds".format(loop_count, MAX_SCHEDULE_COUNT, SCHEDULE_INTERVAL)
        )
        try:
            self.log_info(_("Start checking DBHA service status."))
            code, msg, resp_data = query_switch_queue(
                dbha_version=dbha_version,
                app=kwargs["app"],
                start_time=kwargs["switch_start_time"],
                finished_time=kwargs["switch_finished_time"],
                extra_v1_args=kwargs,
                timeout=QUERY_TIMEOUT,
                retry_times=QUERY_RETRY_TIMES,
            )

            if code == 0:
                self.log_info("HADB({}) service query success!".format(dbha_version))
                self.log_info("query_args: {}".format(kwargs))
                self.log_info("dbha switch info: {}".format(resp_data))
                for d in resp_data:
                    if d.get("ip") == kwargs["ip"]:
                        self.finish_schedule()
                        return True
                self.log_info("Status has not changed yet!")
            else:
                self.log_error("HADB service query failed. code:{} msg:{}".format(code, msg))

        except Exception as e:
            self.log_exception("HADB service query error: {}".format(e))

        if loop_count >= MAX_SCHEDULE_COUNT:
            self.log_info("HADB service query timeout! Exiting polling state...")
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
