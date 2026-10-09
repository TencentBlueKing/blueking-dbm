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
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.constants import SHARD_ROUTE_CONCURRENCY, SHARD_ROUTE_MAX_KEYS
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.locator import BackupLocator
from backend.db_services.redis.rollback.shards import ShardResolver, _ranges_intersect, ip_port, parse_shard_value
from backend.db_services.redis.util import is_redis_cluster_protocal, is_twemproxy_proxy_type
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_cluster_nodes import get_masters_with_slots

logger = logging.getLogger("root")

# getserver replies "<ip>:<port>:<weight> <app> <seg_start>-<seg_end> <status>".
_GETSERVER_REPLY = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){3}:\d+)(?::\d+)?\s+\S+\s+(\d+-\d+)(?:\s|$)")
# DRS splits the command on whitespace and strips `"` and `''`, so such keys would route as a different key.
_UNROUTABLE_KEY = re.compile(r"\s|\"|''")

Ranges = List[Tuple[int, int]]


@dataclass
class _Route:
    range: str
    backend: str
    # Cluster protocol only: the exact slot, matched against batch shards instead of `range`.
    slot: Optional[int] = None


class ShardRouter:
    """Find the range holding each key by asking the cluster, never by hashing locally.

    The current layout may differ from a batch's (shards split or merged since), so with a
    batch every batch shard the key may fall into is returned, never just one.
    """

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.resolver = ShardResolver(cluster)

    def route(self, keys: Sequence[str], backup_identify: str = "") -> Dict[str, Any]:
        keys = list(dict.fromkeys(keys))
        if len(keys) > SHARD_ROUTE_MAX_KEYS:
            raise RollbackPlanError(
                context={"message": _("一次最多路由 {} 个 key，当前 {} 个").format(SHARD_ROUTE_MAX_KEYS, len(keys))}
            )

        results = [{"key": key, "range": "", "backend": "", "error": ""} for key in keys]
        routable = []
        for result in results:
            if not result["key"] or _UNROUTABLE_KEY.search(result["key"]):
                result["error"] = str(_("key 为空或含空白、双引号，无法经 DRS 路由"))
            else:
                routable.append(result)

        hits: Dict[str, _Route] = {}
        masters = [ref for ref in self.resolver.from_db_meta() if ref.current_master]
        single_shard = len(masters) == 1
        if single_shard:
            for result in routable:
                hits[result["key"]] = _Route(masters[0].shard_value, masters[0].current_master)
        elif routable:
            if is_twemproxy_proxy_type(self.cluster.cluster_type):
                self._route_all(routable, self._twemproxy_router(), hits)
            elif is_redis_cluster_protocal(self.cluster.cluster_type):
                self._route_all(routable, self._cluster_router(), hits)
            else:
                raise RollbackPlanError(context={"message": _("集群类型 {} 不支持分片路由").format(self.cluster.cluster_type)})

        for result in results:
            hit = hits.get(result["key"])
            if hit:
                result["range"], result["backend"] = hit.range, hit.backend
        if not backup_identify:
            return {"results": results}

        batch, warnings = self._batch_shards(backup_identify)
        union: List[str] = []
        for result in results:
            hit = hits.get(result["key"])
            selected, uncovered = self._expand(hit, batch, single_shard) if hit else ([], [])
            result["batch_shard_values"] = selected
            result["is_covered"] = bool(selected) and not uncovered
            result["uncovered_ranges"] = uncovered
            union.extend(selected)
        return {"results": results, "batch_shard_values": list(dict.fromkeys(union)), "warnings": warnings}

    def _batch_shards(self, backup_identify: str) -> Tuple[List[Tuple[str, Ranges]], List[str]]:
        shards: Dict[str, Ranges] = {}
        warnings: List[str] = []
        for record in BackupLocator(self.cluster).locate_full_by_identify(backup_identify):
            shard_value = record.get("shard_value") or ""
            if not shard_value or shard_value in shards:
                continue
            parsed = parse_shard_value(shard_value)
            if parsed.parseable:
                shards[shard_value] = parsed.ranges
                continue
            warning = str(
                _("批次分片 {} 的 shard_value 无法解析，未参与匹配: {}").format(
                    ip_port(record.get("source_ip"), record.get("server_port")), parsed.reason
                )
            )
            if warning not in warnings:
                warnings.append(warning)
        return sorted(shards.items(), key=lambda item: item[1][0]), warnings

    @staticmethod
    def _expand(hit: _Route, batch: List[Tuple[str, Ranges]], single_shard: bool) -> Tuple[List[str], List[str]]:
        if single_shard:
            # The only shard holds every key, so the whole batch is needed.
            target: Ranges = []
            selected = batch
        else:
            if hit.slot is not None:
                target = [(hit.slot, hit.slot)]
            else:
                parsed = parse_shard_value(hit.range)
                target = parsed.ranges if parsed.parseable else []
            selected = [(value, ranges) for value, ranges in batch if _ranges_intersect(ranges, target)]
        covering = [item for _value, ranges in selected for item in ranges]
        return [value for value, _ranges in selected], [_format_range(gap) for gap in _uncovered(target, covering)]

    def _route_all(self, routable: List[dict], route_one: Callable[[str], _Route], hits: Dict[str, _Route]):
        def _run(result: dict):
            try:
                hits[result["key"]] = route_one(result["key"])
                return True
            except RollbackPlanError as exc:
                result["error"] = str(exc.message)
                return True
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("redis shard route failed cluster=%s key=%s: %s", self.cluster.id, result["key"], exc)
                result["error"] = str(_("DRS 调用失败: {}").format(exc))
                return False

        with ThreadPoolExecutor(max_workers=min(SHARD_ROUTE_CONCURRENCY, len(routable))) as pool:
            delivered = list(pool.map(_run, routable))
        if not any(delivered):
            raise RollbackPlanError(context={"message": _("DRS 不可用，全部 key 路由失败: {}").format(routable[0]["error"])})

    def _rpc(self, address: str, password: str, command: str) -> str:
        resp = DRSApi.redis_rpc(
            {
                "addresses": [address],
                "db_num": 0,
                "password": password,
                "command": command,
                "bk_cloud_id": self.cluster.bk_cloud_id,
            }
        )
        if not resp:
            raise RollbackPlanError(context={"message": _("DRS 无返回: {}").format(command)})
        return str(resp[0].get("result") or "")

    def _twemproxy_router(self) -> Callable[[str], _Route]:
        proxies = self.cluster.proxyinstance_set
        proxy = proxies.filter(status=InstanceStatus.RUNNING.value).first() or proxies.first()
        if not proxy:
            raise RollbackPlanError(context={"message": _("集群 {} 没有可用的 proxy").format(self.cluster.immute_domain)})
        address = proxy.ip_port
        password = PayloadHandler.redis_get_cluster_password(self.cluster).get("redis_proxy_password")

        def _route(key: str) -> _Route:
            reply = self._rpc(address, password, "getserver {}".format(key))
            matched = _GETSERVER_REPLY.match(reply)
            if not matched:
                raise RollbackPlanError(context={"message": _("getserver 返回无法解析: {}").format(reply.strip())})
            return _Route(range=matched.group(2), backend=matched.group(1))

        return _route

    def _cluster_router(self) -> Callable[[str], _Route]:
        # Predixy does not forward CLUSTER KEYSLOT. It is pure computation on the key name and
        # identical on every node, so ask a replica and leave the masters alone.
        storages = self.cluster.storageinstance_set
        slaves = storages.filter(instance_role=InstanceRole.REDIS_SLAVE.value)
        node = (
            slaves.filter(status=InstanceStatus.RUNNING.value).first()
            or slaves.first()
            or storages.filter(instance_role=InstanceRole.REDIS_MASTER.value).first()
        )
        if not node:
            raise RollbackPlanError(context={"message": _("集群 {} 没有存储实例").format(self.cluster.immute_domain)})
        address = node.ip_port
        password = PayloadHandler.redis_get_cluster_password(self.cluster).get("redis_password")
        # Live slot owners; backups report the same slot string, which db_meta does not always hold.
        try:
            owners = get_masters_with_slots(self._rpc(address, password, "cluster nodes"))
        except RollbackPlanError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            raise RollbackPlanError(context={"message": _("DRS 获取 cluster nodes 失败: {}").format(exc)})
        by_slot: Dict[int, Any] = {}
        for node in owners:
            for slot in node.slots:
                by_slot[slot] = node

        def _route(key: str) -> _Route:
            reply = self._rpc(address, password, "cluster keyslot {}".format(key)).strip()
            if not reply.isdigit():
                raise RollbackPlanError(context={"message": _("cluster keyslot 返回无法解析: {}").format(reply)})
            slot = int(reply)
            owner = by_slot.get(slot)
            if not owner:
                raise RollbackPlanError(context={"message": _("slot {} 当前无 master 持有").format(slot)})
            return _Route(range=owner.slot_src_str, backend=owner.addr, slot=slot)

        return _route


def _uncovered(target: Ranges, covering: Ranges) -> Ranges:
    """Parts of ``target`` outside every ``covering`` range, without expanding ranges into slots."""
    covering = sorted(covering)
    gaps: Ranges = []
    for start, end in target:
        cursor = start
        for cover_start, cover_end in covering:
            if cover_end < cursor:
                continue
            if cover_start > end:
                break
            if cover_start > cursor:
                gaps.append((cursor, cover_start - 1))
            cursor = cover_end + 1
            if cursor > end:
                break
        if cursor <= end:
            gaps.append((cursor, end))
    return gaps


def _format_range(span: Tuple[int, int]) -> str:
    start, end = span
    return str(start) if start == end else "{}-{}".format(start, end)
