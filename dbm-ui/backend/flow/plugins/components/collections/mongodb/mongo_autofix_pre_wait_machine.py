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

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend.db_meta.models import Machine
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import _probe_gse_alive_once

logger = logging.getLogger("flow")

POLL_INTERVAL_SEC = 120
DEFAULT_MAX_WAIT_SEC = 4 * 60 * 60
I_SERIES_MAX_WAIT_SEC = 30 * 60
WAIT_FOREVER_SEC = 0
HIGH_IO_LABEL = _("高IO")
STANDARD_LABEL = _("标准类")
MONGOS_LABEL = _("mongos")
FOREVER_LABEL = _("一直等")


def _get_device_class(info: dict) -> str:
    """优先按 bk_host_id 定位机器，缺失时回退到云区域 + IP。"""
    bk_host_id = int(info.get("bk_host_id") or 0)
    machine = None
    if bk_host_id:
        machine = Machine.objects.filter(bk_host_id=bk_host_id).only("bk_svr_device_cls_name").first()
    if machine is None:
        machine = (
            Machine.objects.filter(
                ip=info.get("ip"),
                bk_cloud_id=int(info.get("bk_cloud_id") or 0),
            )
            .only("bk_svr_device_cls_name")
            .first()
        )
    return (machine.bk_svr_device_cls_name or "").strip() if machine else ""


def _is_high_io(device_class: str) -> bool:
    """I 开头的机型为高 IO，其余为标准类。"""
    return (device_class or "").strip().upper().startswith("I")


def _max_wait_seconds(device_class: str) -> int:
    return I_SERIES_MAX_WAIT_SEC if _is_high_io(device_class) else DEFAULT_MAX_WAIT_SEC


def wait_gse_forever(info: dict) -> bool:
    """mongos PRE：GSE/uptime 探测一直等到机器起来，不按机型超时。"""
    if info.get("wait_gse_forever"):
        return True
    if str(info.get("machine_type") or "").lower() == "mongos":
        return True
    return any(str(role).lower() == "mongos" for role in (info.get("roles") or []))


def resolve_max_wait_seconds(info: dict, device_class: str) -> int:
    if wait_gse_forever(info):
        return WAIT_FOREVER_SEC
    return _max_wait_seconds(device_class)


def _format_duration(seconds: int) -> str:
    if seconds >= 3600 and seconds % 3600 == 0:
        return "{}h".format(seconds // 3600)
    if seconds >= 60 and seconds % 60 == 0:
        return "{}m".format(seconds // 60)
    return "{}s".format(seconds)


def wait_machine_act_name(info: dict, device_class: str | None = None) -> str:
    """等待机器启动-{ip}-(高IO/30m/2m) 或 等待机器启动-{ip}-(标准类/4h/2m)；mongos 为一直等。"""
    ip = info.get("ip") or ""
    poll = _format_duration(POLL_INTERVAL_SEC)
    if wait_gse_forever(info):
        return _("等待机器启动-{}-({}/{}/{})").format(ip, MONGOS_LABEL, FOREVER_LABEL, poll)
    if device_class is None:
        device_class = _get_device_class(info)
    kind = HIGH_IO_LABEL if _is_high_io(device_class) else STANDARD_LABEL
    wait = _format_duration(_max_wait_seconds(device_class))
    return _("等待机器启动-{}-({}/{}/{})").format(ip, kind, wait, poll)


def _probe_uptime_once(ip: str, bk_cloud_id: int, log_fn=None):
    return _probe_gse_alive_once(
        ip,
        bk_cloud_id,
        log_fn=log_fn,
        script="uptime",
        task_name_prefix="mongo_autofix_pre_wait_uptime",
    )


class MongoAutofixPreWaitMachineService(BaseService):
    """每两分钟执行一次 uptime，机器启动或达到等待上限后继续 PRE 分叉。"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLL_INTERVAL_SEC)

    def _execute(self, data, parent_data) -> bool:
        info = data.get_one_of_inputs("kwargs") or {}
        ip = info["ip"]
        bk_cloud_id = int(info.get("bk_cloud_id") or 0)
        device_class = _get_device_class(info)
        max_wait_sec = resolve_max_wait_seconds(info, device_class)

        data.outputs.started_at = timezone.now().isoformat()
        data.outputs.machine_started = 0
        data.outputs.timed_out = 0
        data.outputs.poll_rounds = 1
        data.outputs.device_class = device_class
        data.outputs.max_wait_sec = max_wait_sec

        self.log_info(
            "wait machine start ip={} device_class={} max_wait_sec={} poll_interval_sec={}".format(
                ip, device_class or "-", max_wait_sec, POLL_INTERVAL_SEC
            )
        )
        if _probe_uptime_once(ip, bk_cloud_id, log_fn=self.log_info) is True:
            data.outputs.machine_started = 1
            self.log_info("machine already started ip={} uptime probe succeeded".format(ip))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        if int(getattr(data.outputs, "machine_started", 0) or 0) == 1:
            self.finish_schedule()
            return True

        info = data.get_one_of_inputs("kwargs") or {}
        ip = info["ip"]
        bk_cloud_id = int(info.get("bk_cloud_id") or 0)
        started = timezone.datetime.fromisoformat(data.outputs.started_at)
        if timezone.is_naive(started):
            started = timezone.make_aware(started, timezone.get_current_timezone())
        elapsed_sec = (timezone.now() - started).total_seconds()
        max_wait_sec = int(data.outputs.max_wait_sec)

        if max_wait_sec > 0 and elapsed_sec >= max_wait_sec:
            data.outputs.timed_out = 1
            self.log_warning(
                "wait machine start timeout ip={} elapsed_sec={:.0f} max_wait_sec={}, continue triage".format(
                    ip, elapsed_sec, max_wait_sec
                )
            )
            self.finish_schedule()
            return True

        rounds = int(getattr(data.outputs, "poll_rounds", 0) or 0) + 1
        data.outputs.poll_rounds = rounds
        alive = _probe_uptime_once(ip, bk_cloud_id, log_fn=self.log_info)
        self.log_info(
            "wait machine start poll round={} ip={} uptime_alive={} elapsed_sec={:.0f}".format(
                rounds, ip, alive, elapsed_sec
            )
        )
        if alive is True:
            data.outputs.machine_started = 1
            self.finish_schedule()
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoAutofixPreWaitMachineComponent(Component):
    name = __name__
    code = "mongo_autofix_pre_wait_machine"
    bound_service = MongoAutofixPreWaitMachineService
