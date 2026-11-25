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

from django.utils.translation import gettext as _
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


def decide_replace_alive(gse_status: Optional[bool], ports_reachable: Optional[bool]) -> Optional[bool]:
    """True 活机，False 故障机，None 无法判断（调用方不当故障机）。

    控制面没有明确探活成功时，必须看数据面。端口全部连不上就是故障机，
    不能因为 GSE 超时（None）跳过端口检查后当成活机。
    只有数据面也给不出结论时，才保持不确定。
    """
    if gse_status is True or ports_reachable is True:
        return True
    if ports_reachable is False:
        return False
    return None


def explain_replace_decision(gse_status: Optional[bool], ports_reachable: Optional[bool]) -> Optional[str]:
    """容易误判时返回一段说明，写入流程日志。GSE 已明确探活成功则不记。"""
    if gse_status is True:
        return None
    alive = decide_replace_alive(gse_status, ports_reachable)
    if ports_reachable is False:
        return _(
            "replace probe ambiguous: gse={} ports=unreachable decision=down. " "GSE 超时或失败不能单独忽略，端口全部连不上按故障机"
        ).format(gse_status)
    if ports_reachable is True:
        return _(
            "replace probe ambiguous: gse={} ports=reachable decision=alive. "
            "控制面失败但 ping.ok=1，Agent 不可用时 mongod 仍可能在服务"
        ).format(gse_status)
    return _(
        "replace probe ambiguous: gse={} ports=unknown decision={} (keep alive path). "
        "无实例、缺 cluster_id 或组 DRS 参数失败时无法确认端口，仍走活机；机器若已关机会误判"
    ).format(gse_status, alive)


def _preview_text(value, limit: int = 300) -> str:
    text = str(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def drs_ping_ok(rpc_results) -> bool:
    """DRS 回包必须解析出 ping.ok==1。连接失败的文本也是正常返回，不能当成可达。"""
    from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import _parse_drs_is_master_ok

    return _parse_drs_is_master_ok(rpc_results) == 1.0


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
            ip,
            bk_cloud_id,
            log_fn=log_fn,
            script="echo alive",
            task_name_prefix="mongo_replace_ssh",
            attempt=attempt,
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
        log_fn(
            _(
                "replace probe ambiguous: ip={} gse inconclusive (timeout or api error). " "控制面不确定，不能据此单独判死，继续看端口"
            ).format(ip)
        )
        return None
    log_fn("replace probe ip={} gse all attempts failed, check ports before marking down".format(ip))
    return False


def _log_probe(log_fn, msg: str, warning: bool = False) -> None:
    if warning:
        logger.warning(msg)
    else:
        logger.info(msg)
    if log_fn:
        log_fn(msg)


def _mongo_port_reachable(ip: str, port, cluster_id, log_fn=None) -> Optional[bool]:
    """DRS 能连上该端口返回 True，连不上返回 False，参数不够无法判断返回 None。"""
    if not cluster_id or port in (None, ""):
        _log_probe(
            log_fn,
            "replace probe ambiguous: skip port ip={} port={} cluster_id={} reason=missing_cluster_or_port".format(
                ip, port, cluster_id
            ),
            warning=True,
        )
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
            command="db.runCommand({ping:1}).ok",
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001
        _log_probe(
            log_fn,
            "replace probe ambiguous: skip port ip={} port={} cluster_id={} reason=build_drs_args_failed err={}".format(
                ip, port, cluster_id, exc
            ),
            warning=True,
        )
        return None
    try:
        rpc_results = DRSApi.mongodb_rpc(param)
    except Exception as exc:  # noqa: BLE001
        # DRS 网关异常、鉴权失败等属于"无法完成探测"，不是端口不可达。
        # 返回 None（未知），避免把仍在线的机器按宕机路径替换。
        _log_probe(
            log_fn,
            "replace probe ambiguous: port drs exception ip={} port={} cluster_id={} err={}".format(
                ip, port, cluster_id, exc
            ),
            warning=True,
        )
        return None
    ping_ok = drs_ping_ok(rpc_results)
    _log_probe(
        log_fn,
        "replace probe port drs result ip={} port={} cluster_id={} ping_ok={} result={}".format(
            ip, port, cluster_id, ping_ok, _preview_text(rpc_results)
        ),
    )
    if ping_ok:
        return True
    _log_probe(
        log_fn,
        _(
            "replace probe ambiguous: ip={} port={} ping.ok!=1, treat as unreachable. " "DRS 未抛异常也会返回连接失败文本，不能当成端口活着"
        ).format(ip, port),
    )
    return False


def mongo_ports_reachable(ip: str, instances: list, log_fn=None) -> Optional[bool]:
    """任一端口可达即活。全部明确不可达才是死。没有端口或无法判断时返回 None。"""
    if not instances:
        _log_probe(log_fn, "replace probe ambiguous: ip={} no instances, data plane unknown".format(ip), warning=True)
        return None
    ports = [
        "port={} cluster_id={}".format(inst.get("port"), inst.get("cluster_id"))
        for inst in instances
        if isinstance(inst, dict)
    ]
    _log_probe(log_fn, "replace probe data plane start ip={} instances={}".format(ip, ports or instances))
    saw_false = False
    saw_unknown = False
    for inst in instances:
        if not isinstance(inst, dict):
            saw_unknown = True
            continue
        status = _mongo_port_reachable(ip, inst.get("port"), inst.get("cluster_id") or 0, log_fn=log_fn)
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
            # GSE 明确探活成功才直接当活机。超时/失败都要再看端口，避免死机被当成活机。
            if gse_status is True:
                return True
            ports_reachable = mongo_ports_reachable(ip, instances, log_fn=self.log_info)
            decision = decide_replace_alive(gse_status, ports_reachable)
            reason = explain_replace_decision(gse_status, ports_reachable)
            if reason:
                self.log_info("ip={} {}".format(ip, reason))
            return decision

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
