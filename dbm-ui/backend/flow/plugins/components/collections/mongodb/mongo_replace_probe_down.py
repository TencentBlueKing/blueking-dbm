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
from typing import List, Optional

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


def collect_probe_instances(host: dict) -> List[dict]:
    """从替换主机上收集端口和集群，供数据面确认。"""
    found = []
    for inst in (host or {}).get("instances") or []:
        if not isinstance(inst, dict) or inst.get("port") in (None, ""):
            continue
        found.append({"port": inst["port"], "cluster_id": inst.get("cluster_id") or 0})
    return found


def gse_confirmed_down(results) -> bool:
    """每一次都是明确失败才算 GSE 确认不可达。出现 True 或 None 都不算。"""
    return bool(results) and all(item is False for item in results)


def source_down_decision(gse_results, ports_reachable: Optional[bool]) -> bool:
    """GSE 全部失败，且数据面也确认连不上，才走 sourceDown。"""
    if not gse_confirmed_down(gse_results):
        return False
    return ports_reachable is False


def _gse_probe_status(ip: str, bk_cloud_id: int, log_fn) -> Optional[bool]:
    """多次 GSE 探测。任一次成功即活；全部失败才是死；中间夹杂不确定则保持不确定。"""
    from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import (
        GSE_PROBE_ATTEMPTS,
        GSE_PROBE_INTERVAL_SEC,
        _probe_gse_alive_once,
    )

    saw_none = False
    for attempt in range(1, GSE_PROBE_ATTEMPTS + 1):
        result = _probe_gse_alive_once(
            ip, bk_cloud_id, script="echo alive", task_name_prefix="mongo_replace_ssh", attempt=attempt
        )
        log_fn(
            "machine replace probe ip={} bk_cloud_id={} attempt={} result={}".format(ip, bk_cloud_id, attempt, result)
        )
        if result is True:
            return True
        if result is None:
            saw_none = True
        if attempt < GSE_PROBE_ATTEMPTS:
            time.sleep(GSE_PROBE_INTERVAL_SEC)
    if saw_none:
        return None
    return False


def _mongo_port_reachable(ip: str, port, cluster_id) -> Optional[bool]:
    """DRS 能连上该端口返回 True，连不上返回 False，参数不够无法判断返回 None。"""
    if not cluster_id or port in (None, ""):
        return None
    from datetime import datetime, timezone

    from backend.components import DRSApi
    from backend.flow.utils.mongodb.mongodb_util import MongoUtil

    session_time = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        param = MongoUtil.get_mongodb_DRS_args_direct(
            cluster_id=int(cluster_id),
            addr="{}:{}".format(ip, port),
            session="replace_probe:{}".format(session_time),
            command="db.runCommand({ping:1})",
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("replace probe skip port %s:%s cluster=%s err=%s", ip, port, cluster_id, exc)
        return None
    try:
        DRSApi.mongodb_rpc(param)
    except Exception as exc:  # noqa: BLE001
        logger.info("replace probe port unreachable %s:%s err=%s", ip, port, exc)
        return False
    return True


def mongo_ports_reachable(ip: str, instances: list) -> Optional[bool]:
    """任一端口可达即活。全部明确不可达才是死。没有端口或无法判断时返回 None。"""
    if not instances:
        return None
    saw_false = False
    saw_unknown = False
    for inst in instances:
        if not isinstance(inst, dict):
            saw_unknown = True
            continue
        status = _mongo_port_reachable(ip, inst.get("port"), inst.get("cluster_id") or 0)
        if status is True:
            return True
        if status is False:
            saw_false = True
        else:
            saw_unknown = True
    if saw_unknown or not saw_false:
        return None
    return False


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

        instances = kwargs.get("instances") or []

        def probe(ip, bk_cloud_id):
            gse_status = _gse_probe_status(ip, bk_cloud_id, self.log_info)
            if gse_status is not False:
                return gse_status
            ports_reachable = mongo_ports_reachable(ip, instances)
            self.log_info("machine replace data plane ip={} reachable={}".format(ip, ports_reachable))
            if source_down_decision([False], ports_reachable):
                return False
            return True if ports_reachable is True else None

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
