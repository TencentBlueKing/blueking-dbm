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

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


def replace_down_flag(hosts, probe) -> int:
    """1: 已标记故障，或 GSE 明确失败。探测不确定（None）或成功不改成故障。"""
    down = False
    for host in hosts or []:
        if not isinstance(host, dict):
            continue
        if host.get("down"):
            down = True
            continue
        ip = host.get("ip")
        if not ip:
            continue
        try:
            cloud = int(host.get("bk_cloud_id") or 0)
        except (TypeError, ValueError):
            cloud = 0
        if probe(ip, cloud) is False:
            down = True
    return 1 if down else 0


class MongoReplaceProbeDown(BaseService):
    """整机替换前探测故障机。输出 replace_down=1/0，供条件分支选择故障路径或活机路径。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        hosts = kwargs.get("hosts")
        if not hosts:
            hosts = [
                {
                    "ip": kwargs.get("ip"),
                    "bk_cloud_id": kwargs.get("bk_cloud_id") or 0,
                    "down": bool(kwargs.get("down")),
                }
            ]

        def probe(ip, bk_cloud_id):
            from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import (
                _probe_gse_alive_once,
            )

            result = _probe_gse_alive_once(ip, bk_cloud_id, script="echo alive", task_name_prefix="mongo_replace_ssh")
            self.log_info("machine replace probe ip={} bk_cloud_id={} result={}".format(ip, bk_cloud_id, result))
            return result

        flag = replace_down_flag(hosts, probe)
        data.outputs.replace_down = flag
        if flag:
            self.log_info("machine replace probe marked down hosts={}".format([host.get("ip") for host in hosts]))
        else:
            self.log_info("machine replace probe keep alive hosts={}".format([host.get("ip") for host in hosts]))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoReplaceProbeDownComponent(Component):
    name = __name__
    code = "mongo_replace_probe_down"
    bound_service = MongoReplaceProbeDown


class MongoReplaceLiveUnavailable(BaseService):
    """活机替换子流程在编排时失败。只有探测结果为活机时才会执行到这里。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        self.log_error("live machine replace was not built: {}".format(kwargs.get("message") or "unknown"))
        return False

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoReplaceLiveUnavailableComponent(Component):
    name = __name__
    code = "mongo_replace_live_unavailable"
    bound_service = MongoReplaceLiveUnavailable
