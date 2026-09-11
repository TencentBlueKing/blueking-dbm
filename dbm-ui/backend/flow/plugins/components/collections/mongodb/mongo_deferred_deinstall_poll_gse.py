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
import time
from typing import List

from django.utils import timezone
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import _probe_gse_alive

logger = logging.getLogger("flow")

DEFAULT_POLL_INTERVAL_SEC = 300
DEFAULT_MAX_WAIT_HOURS = 168


class MongoDeferredDeinstallPollGse(BaseService):
    """每 poll_interval_sec 用 GSE/Job 探活，直到可达或超时。"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(DEFAULT_POLL_INTERVAL_SEC)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        poll_interval = int(kwargs.get("poll_interval_sec") or DEFAULT_POLL_INTERVAL_SEC)
        self.interval = StaticIntervalGenerator(max(poll_interval, 30))
        data.outputs.poll_started_at = timezone.now().isoformat()
        data.outputs.poll_rounds = 0
        ip = kwargs["ip"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        if _probe_gse_alive(ip, bk_cloud_id):
            self.log_info("gse already alive ip={} bk_cloud_id={}".format(ip, bk_cloud_id))
            data.outputs.gse_alive = 1
            return True
        data.outputs.gse_alive = 0
        self.log_info("gse not alive yet, start polling ip={} interval={}".format(ip, poll_interval))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs") or {}
        if getattr(data.outputs, "gse_alive", 0) == 1:
            self.finish_schedule()
            return True

        ip = kwargs["ip"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        max_wait_hours = int(kwargs.get("max_wait_hours") or DEFAULT_MAX_WAIT_HOURS)
        started_raw = getattr(data.outputs, "poll_started_at", None)
        rounds = int(getattr(data.outputs, "poll_rounds", 0) or 0) + 1
        data.outputs.poll_rounds = rounds

        if started_raw:
            started = timezone.datetime.fromisoformat(started_raw)
            if timezone.is_naive(started):
                started = timezone.make_aware(started, timezone.get_current_timezone())
            elapsed_h = (timezone.now() - started).total_seconds() / 3600.0
            if elapsed_h >= max_wait_hours:
                self.log_error(
                    "gse poll timeout ip={} elapsed_h={:.2f} max_wait_hours={}".format(ip, elapsed_h, max_wait_hours)
                )
                self.finish_schedule()
                return False

        alive = _probe_gse_alive(ip, bk_cloud_id)
        self.log_info("gse poll round={} ip={} alive={}".format(rounds, ip, alive))
        if alive:
            data.outputs.gse_alive = 1
            self.finish_schedule()
            return True
        time.sleep(0.1)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoDeferredDeinstallPollGseComponent(Component):
    name = __name__
    code = "mongo_deferred_deinstall_poll_gse"
    bound_service = MongoDeferredDeinstallPollGse
