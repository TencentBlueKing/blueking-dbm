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
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_report.enums import ReportStateType
from backend.flow.utils.redis.redis_proxy_util import PredixyInfoServer, decode_predixy_info_servers
from backend.flow.utils.redis.redis_script_template import build_predixy_conf_check_snippet

from .base import BaseConfChecker, CheckTarget, ConfCheckResult
from .errors import is_host_collection_error
from .registry import redis_conf_checker

QUESTION_MARK_MEMORY_IP = "?"
IGNORE_QUESTION_IP_IN_MEMORY_KEY = "ignore_question_ip_in_memory"


def _memory_server_ip(server: str) -> str:
    return server.split(":", 1)[0]


def _apply_memory_server_filters(
    servers: List[PredixyInfoServer], ignore_question_ip_in_memory: bool
) -> List[PredixyInfoServer]:
    if not ignore_question_ip_in_memory:
        return servers
    return [item for item in servers if _memory_server_ip(item.server) != QUESTION_MARK_MEMORY_IP]


@redis_conf_checker
class PredixyServersChecker(BaseConfChecker):
    """
    For each predixy proxy, detect two problems:

    1. Backends with ``CurrentIsFail == 1`` (live `INFO Servers`): predixy keeps
       retrying these and floods the error log.
    2. Drift between the live (non-failed) server set and the servers configured
       in the on-disk ``predixy.conf``: on a predixy restart the stale file is
       reloaded, so drift predicts breakage.

    Live state comes from DRS (`INFO Servers`); the configured set is read by an
    on-host snippet (predixy hosts may not have redis-cli, but reading a file is
    always possible).
    """

    name = "predixy_servers"
    requires_host_script = True
    cluster_types = [
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisPredixyTendisplusInstance.value,
    ]

    def collect_targets(self, cluster) -> List[CheckTarget]:
        targets = []
        prefetched = getattr(cluster, "_prefetched_objects_cache", {})
        if "storageinstance_set" in prefetched:
            storages = cluster.storageinstance_set.all()
        else:
            storages = cluster.storageinstance_set.select_related("machine").all()
        meta_servers = sorted(
            {
                "{}:{}".format(storage.machine.ip, storage.port)
                for storage in storages
                if storage.status == InstanceStatus.RUNNING
            }
        )
        if "proxyinstance_set" in prefetched:
            proxies = cluster.proxyinstance_set.all()
        else:
            proxies = cluster.proxyinstance_set.select_related("machine").all()
        for proxy in proxies:
            if proxy.status != InstanceStatus.RUNNING:
                continue
            targets.append(
                CheckTarget(
                    cluster_id=cluster.id,
                    bk_cloud_id=cluster.bk_cloud_id,
                    ip=proxy.machine.ip,
                    port=proxy.port,
                    extra={"meta_servers": meta_servers},
                )
            )
        return targets

    def host_script_snippet(self, targets_on_host: List[CheckTarget]) -> Optional[str]:
        ports = [t.port for t in targets_on_host]
        if not ports:
            return None
        return build_predixy_conf_check_snippet(ports)

    def drs_request(self, target: CheckTarget) -> Optional[Tuple[str, str]]:
        return "info servers", "redis_proxy_password"

    def evaluate(
        self,
        target: CheckTarget,
        drs_result: Optional[str],
        host_block: Optional[Dict],
        checker_config: Optional[Dict] = None,
        drs_error: Optional[str] = None,
    ) -> List[ConfCheckResult]:
        """Combine CurrentIsFail + conf drift into a single row per proxy."""
        addr = target.address
        checker_config = checker_config or {}
        ignore_question_ip_in_memory = bool(checker_config.get(IGNORE_QUESTION_IP_IN_MEMORY_KEY, False))

        if not drs_result:
            reason = drs_error or "proxy_unreachable_or_empty"
            return [
                ConfCheckResult(
                    ip=target.ip,
                    port=target.port,
                    state=ReportStateType.ABNORMAL.value,
                    msg=_("Predixy {} INFO Servers 查询失败({})").format(addr, reason),
                )
            ]

        raw_servers = decode_predixy_info_servers(drs_result)
        if not raw_servers:
            return [
                ConfCheckResult(
                    ip=target.ip,
                    port=target.port,
                    state=ReportStateType.ABNORMAL.value,
                    msg=_("Predixy {} INFO Servers 返回为空(empty_drs_snapshot)").format(addr),
                )
            ]

        servers = _apply_memory_server_filters(raw_servers, ignore_question_ip_in_memory)
        in_memory = {s.server for s in servers}
        failed_in_memory = sorted({s.server for s in servers if s.current_is_fail == 1})
        meta_set = set(target.extra.get("meta_servers", []))

        issues = []
        if failed_in_memory:
            issues.append("failed_in_memory={}".format(failed_in_memory))

        if not host_block or "servers" not in host_block:
            err = host_block.get("error") if host_block else "no_host_data"
            if err and is_host_collection_error(err):
                issues.append(_("主机配置采集失败({})").format(err))
            else:
                issues.append(_("无法读取predixy.conf进行比对({})").format(err))
        else:
            conf_set = set(host_block["servers"])
            failed_in_conf = sorted(set(failed_in_memory) & conf_set)
            if failed_in_conf:
                issues.append("failed_in_conf={}".format(failed_in_conf))

            only_in_memory = sorted(in_memory - conf_set)
            only_in_conf = sorted(conf_set - in_memory)
            only_in_meta = sorted(meta_set - in_memory - conf_set)
            not_in_meta = sorted(conf_set - meta_set)
            if only_in_memory or only_in_conf or only_in_meta or not_in_meta:
                issues.append(
                    "servers_mismatch: only_in_memory={}, only_in_conf={}, only_in_meta={}, not_in_meta={}".format(
                        only_in_memory, only_in_conf, only_in_meta, not_in_meta
                    )
                )

        if issues:
            state = ReportStateType.ABNORMAL.value
            msg = _("Predixy {} 配置异常: {}").format(addr, "; ".join(issues))
        else:
            state = ReportStateType.NORMAL.value
            msg = _("Predixy {} Server正常: failed_in_memory=[], failed_in_conf=[], memory/conf/meta一致").format(addr)

        return [ConfCheckResult(ip=target.ip, port=target.port, state=state, msg=msg)]
