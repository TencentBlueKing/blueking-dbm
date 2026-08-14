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
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from math import floor
from typing import Dict, List, Optional, Set, Tuple, Union

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import AffinityEnum, DBType, SystemSettingsEnum
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_meta.models.city_map import BKSubzone
from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_abnormal_cluster_rows
from backend.flow.utils.redis.redis_report_utils import (
    META_CHECK_CLUSTER_PAGE_SIZE,
    RedisReportWriter,
    _chunked,
    delete_old_meta_check_reports,
    is_cluster_labeled_with,
    safe_write_meta_reports,
)
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import SystemSettings
from backend.ticket.models.ticket import ClusterOperateRecord

logger = logging.getLogger("root")


DEFAULT_CLUSTER_TYPES = [
    ClusterType.TendisTwemproxyRedisInstance.value,  # TendisCache 集群
    ClusterType.TwemproxyTendisSSDInstance.value,  # TendisSSD 集群
    ClusterType.TendisPredixyRedisCluster.value,  # RedisCluster 集群
    ClusterType.TendisPredixyTendisplusCluster.value,  # Tendisplus 集群
    ClusterType.TendisRedisInstance.value,  # Redis 主从
]


@dataclass
class RedisAffinityCheckConfig:
    """
    Configuration for Redis affinity check task
    """

    enabled: bool = True
    cluster_types: Optional[List[str]] = field(default_factory=lambda: list(DEFAULT_CLUSTER_TYPES))
    bizs_ignored: Optional[List[int]] = field(default_factory=list)
    clusters_ignored: Optional[List[int]] = field(default_factory=list)
    # Empty list means all cloud areas; when set (e.g. [0]), only check matching bk_cloud_id.
    bk_cloud_ids: Optional[List[int]] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "RedisAffinityCheckConfig":
        """Load config from SystemSettings with dataclass defaults for missing keys."""
        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_AFFINITY_CHECK.value, default={})
        if not isinstance(raw, dict):
            if raw:
                logger.warning("RedisAffinityCheckConfig: expected dict, got %s", type(raw).__name__)
            return cls()

        valid_keys = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in valid_keys})

    def save_to_settings(self, user: str = "admin") -> None:
        """Persist this config to SystemSettings for shell_plus maintenance."""
        SystemSettings.insert_setting_value(
            key=SystemSettingsEnum.REDIS_AFFINITY_CHECK.value,
            value=asdict(self),
            value_type="dict",
            user=user,
        )


def _get_candidate_cluster_ids(config: RedisAffinityCheckConfig) -> List[int]:
    query = Cluster.objects.filter(cluster_type__in=config.cluster_types)

    if config.bizs_ignored:
        query = query.exclude(bk_biz_id__in=config.bizs_ignored)

    if config.clusters_ignored:
        query = query.exclude(id__in=config.clusters_ignored)

    if config.bk_cloud_ids:
        query = query.filter(bk_cloud_id__in=config.bk_cloud_ids)

    return list(query.values_list("id", flat=True))


def _load_affinity_clusters_page(cluster_ids: List[int]) -> List[Cluster]:
    if not cluster_ids:
        return []
    # as_ejector + receiver__machine: used by _check_master_machine_affinity for master→slave pairs
    storage_qs = StorageInstance.objects.select_related("machine").prefetch_related(
        Prefetch("as_ejector", queryset=StorageInstanceTuple.objects.select_related("receiver__machine")),
    )
    return list(
        Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
            Prefetch("proxyinstance_set", queryset=ProxyInstance.objects.select_related("machine")),
            Prefetch("storageinstance_set", queryset=storage_qs),
            "tags",
        )
    )


def _fetch_affinity_ignore_cluster_ids(cluster_ids: List[int], ignore_tickets: List[str]) -> Set[int]:
    if not cluster_ids:
        return set()
    return set(
        ClusterOperateRecord.objects.filter(
            ticket__ticket_type__in=ignore_tickets,
            ticket__status__in=TICKET_RUNNING_STATUS_SET,
            cluster_id__in=cluster_ids,
        ).values_list("cluster_id", flat=True)
    )


def check_redis_affinity():
    """
    检查集群中的主从机器是否满足集群亲和性要求
    """
    config = RedisAffinityCheckConfig.from_settings()

    if not config.enabled:
        logger.info(_("Redis affinity check is disabled, exiting"))
        return

    RedisAffinityChecker(config).check_all_clusters()


class RedisAffinityChecker:
    """
    Validates Redis cluster topology against disaster tolerance affinity requirements.

    This checker ensures that Redis clusters maintain proper physical separation between
    components (proxies, masters, and slaves) to minimize the impact of hardware failures.

    Supported Affinity Levels:
    ---------------------------
    1. SAME_SUBZONE_CROSS_SWTICH: Components within the same subzone but on different racks
    2. CROS_SUBZONE: Components distributed across different subzones
    3. CROSS_RACK: Components on different racks (subzone placement is flexible)

    Validation Rules:
    -----------------

    A. Proxy Distribution (for clusters with proxies):
       Validates that proxy instances are properly distributed to avoid single points of failure.

       Subzone requirements:
       - SAME_SUBZONE_CROSS_SWTICH: All proxies must be in a single subzone
       - CROS_SUBZONE: No subzone may contain more than 2/3 of total proxies
       - CROSS_RACK: No subzone restrictions

       Rack distribution (applies within each subzone):
       - Given n proxies in a subzone across m racks, requires: m >= floor(n/2) + 1
       - This ensures no single rack failure can take down more than half the proxies

    B. Master-Slave Pairs (backend storage):
       Validates each master-slave replication pair for proper physical separation.

       - SAME_SUBZONE_CROSS_SWTICH:
         * Master and slave MUST be in the same subzone
         * Master and slave MUST be on different racks

       - CROS_SUBZONE:
         * Master and slave MUST be in different subzones
         * Rack placement is not validated (different subzones provide sufficient separation)

       - CROSS_RACK:
         * If in different subzones: automatically compliant
         * If in the same subzone: MUST be on different racks

       Masters without configured slaves generate warnings but do not fail the check.
    """

    PROXY_DISTRIBUTION_CHECK = "proxy_distribution"
    BACKEND_PAIRS_CHECK = "backend_pairs_location"

    SKIP_PROXY_CHECK_LABEL = {"directmode": "true"}
    _subzone_map_cache: Dict[int, str] = {}

    def __init__(self, config: Optional[RedisAffinityCheckConfig] = None):
        """Initialize the affinity checker"""
        self._config = config or RedisAffinityCheckConfig.from_settings()
        self._writer = RedisReportWriter()
        self._supported_cluster_types = list(self._config.cluster_types)
        # Ignore cluster if it has machines changing
        self._ignore_tickets = [
            TicketType.REDIS_PROXY_CLOSE.value,
            TicketType.REDIS_DESTROY.value,
            TicketType.REDIS_INSTANCE_CLOSE.value,
            TicketType.REDIS_INSTANCE_DESTROY.value,
            TicketType.REDIS_CLUSTER_AUTOFIX.value,
            TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
        ]
        self._supported_levels = {
            AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
            AffinityEnum.CROS_SUBZONE.value,
            AffinityEnum.CROSS_RACK.value,
            AffinityEnum.NONE.value,
        }

    def debug_check_cluster(self, cluster_domain: str) -> None:
        """
        Debug check a single cluster
        """
        self.__class__._subzone_map_cache = BKSubzone.get_subzone_map(get_cache=True)
        clusters = _load_affinity_clusters_page(
            list(Cluster.objects.filter(immute_domain=cluster_domain).values_list("id", flat=True))
        )
        if not clusters:
            logger.error("affinity_check: cluster %s not found", cluster_domain)
            return
        rows = self._check_cluster_affinity(clusters[0])
        if rows:
            safe_write_meta_reports(self._writer, rows, context=f"debug cluster={cluster_domain}")

    def check_all_clusters(self) -> None:
        """
        Check affinity for all Redis clusters
        """
        self.__class__._subzone_map_cache = BKSubzone.get_subzone_map(get_cache=True)

        delete_old_meta_check_reports(
            MetaCheckSubType.AffinityViolation,
            self._supported_cluster_types,
            self._writer.retention_days,
        )

        all_cluster_ids = _get_candidate_cluster_ids(self._config)
        ignore_cluster_ids = _fetch_affinity_ignore_cluster_ids(all_cluster_ids, self._ignore_tickets)
        dba_cache: Dict[int, str] = {}

        for page_ids in _chunked(all_cluster_ids, META_CHECK_CLUSTER_PAGE_SIZE):
            page_rows: List[dict] = []
            for cluster in _load_affinity_clusters_page(page_ids):
                try:
                    if self._should_ignore_cluster(cluster, ignore_cluster_ids):
                        continue
                    page_rows.extend(self._check_cluster_affinity(cluster, dba_cache))
                except Exception as e:
                    logger.error(
                        "affinity_check: error checking cluster %s: %s",
                        cluster.immute_domain,
                        e,
                        exc_info=True,
                    )
            if page_rows:
                safe_write_meta_reports(self._writer, page_rows, context="affinity_check page")
                ingest_abnormal_cluster_rows(
                    page_rows,
                    dimension=RedisPortraitDimensionCode.TOPOLOGY_SCALE,
                    prefix="[亲和性]",
                )

    def _check_cluster_affinity(self, cluster: Cluster, dba_cache: Optional[Dict[int, str]] = None) -> List[dict]:
        """
        Check master-slave affinity for a single cluster
        """
        logger.info("affinity_check: start checking cluster %s", cluster.immute_domain)

        dba_cache = dba_cache if dba_cache is not None else {}
        if cluster.bk_biz_id not in dba_cache:
            dba_list = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.Redis.value)
            dba_cache[cluster.bk_biz_id] = dba_list[0] if dba_list else "admin"
        creator = dba_cache[cluster.bk_biz_id]
        affinity_level = cluster.disaster_tolerance_level

        if affinity_level not in self._supported_levels:
            supported_levels_str = ", ".join(self._supported_levels)
            msg = _(
                "Cannot perform affinity check: Unsupported affinity level '{}' for Redis. Supported levels are: {}"
            ).format(affinity_level, supported_levels_str)
            logger.warning("affinity_check: %s", msg)
            return [
                {
                    "cluster": cluster,
                    "ip": "none",
                    "port": None,
                    "subtype": MetaCheckSubType.AffinityViolation,
                    "msg": msg,
                    "state": ReportStateType.WARNING,
                    "creator": creator,
                }
            ]

        check_results = []
        expected_subzone_id = self._resolve_expected_subzone_id(cluster.zone_list or [])

        # Skip proxy check if cluster is RedisInstance or labeled
        skip_proxy_check = cluster.cluster_type == ClusterType.RedisInstance.value or is_cluster_labeled_with(
            cluster,
            self.SKIP_PROXY_CHECK_LABEL,
        )

        # For proxies, we check the stats of their locations
        if not skip_proxy_check:
            proxy_instances = list(cluster.proxyinstance_set.all())
            proxy_result = self._validate_proxies_affinity(
                proxy_instances=proxy_instances,
                affinity_level=affinity_level,
                expected_subzone_id=expected_subzone_id,
            )
            proxy_result["result_type"] = RedisAffinityChecker.PROXY_DISTRIBUTION_CHECK
            proxy_result["identifier"] = "proxies"
            check_results.append(proxy_result)

        # For backends, we check each master-slave pair
        master_instances = [
            inst for inst in cluster.storageinstance_set.all() if inst.instance_role == InstanceRole.REDIS_MASTER.value
        ]
        backend_results = self._validate_backends_affinity(
            master_instances=master_instances,
            affinity_level=affinity_level,
            expected_subzone_id=expected_subzone_id,
        )
        for identifier, result in backend_results.items():
            result["result_type"] = RedisAffinityChecker.BACKEND_PAIRS_CHECK
            result["identifier"] = identifier
            check_results.append(result)

        return self._build_affinity_report_rows(
            cluster=cluster,
            affinity_level=affinity_level,
            check_results=check_results,
            creator=creator,
        )

    def _should_ignore_cluster(self, cluster: Cluster, ignore_cluster_ids: Set[int]) -> bool:
        """
        Check if cluster should be ignored (being destroyed, disabled, or has active operations)
        """
        if cluster.disaster_tolerance_level == AffinityEnum.NONE.value:
            logger.info("affinity_check: will ignore cluster %s, affinity level is NONE", cluster.immute_domain)
            return True

        if cluster.phase != ClusterPhase.ONLINE.value:
            logger.info(
                f"affinity_check: will ignore cluster {cluster.immute_domain}, "
                f"cluster phase is {cluster.phase} (not online)"
            )
            return True

        if cluster.id in ignore_cluster_ids:
            logger.info(
                "affinity_check: will ignore cluster %s, it has active destroy/disable ticket",
                cluster.immute_domain,
            )
            return True

        return False

    @classmethod
    def _resolve_expected_subzone_id(cls, zone_list: List[Union[int, str]]) -> Optional[int]:
        """
        Resolve expected subzone from cluster meta zone_list.
        For SAME_SUBZONE style checks we use the first configured subzone.
        """
        if not zone_list:
            return None

        first_zone = zone_list[0]
        try:
            return int(first_zone)
        except (TypeError, ValueError):
            logger.warning("affinity_check: invalid zone_list value: %s", first_zone)
            return None

    @classmethod
    def _validate_proxies_affinity(
        cls,
        proxy_instances,
        affinity_level: AffinityEnum,
        expected_subzone_id: Optional[int] = None,
    ) -> Dict[str, any]:
        """
        Check if proxies fulfill the affinity requirement

        Returns:
            dict: {msg: str, state: ReportStateType, machine_type: MachineType, proxy_count: int}
        """
        subzones_racks_map = defaultdict(set)
        subzones_machines_map = defaultdict(int)
        subzones_ips_map = defaultdict(list)  # Track IPs per (subzone_id, rack_id)
        machine_type: MachineType = None
        for proxy_obj in proxy_instances:
            subzone_id = proxy_obj.machine.bk_sub_zone_id
            rack_id = proxy_obj.machine.bk_rack_id

            subzones_racks_map[subzone_id].add(rack_id)  # record rack in a subzone
            subzones_machines_map[subzone_id] += 1  # record subzone heatmap
            subzones_ips_map[(subzone_id, rack_id)].append(proxy_obj.machine.ip)  # collect location -> ip
            machine_type = proxy_obj.machine_type

        result = {
            "state": ReportStateType.NORMAL.value,
            "msg": "",
            "machine_type": machine_type,
            "proxy_count": len(proxy_instances),
        }

        msg, state = None, ReportStateType.NORMAL
        match affinity_level:
            case AffinityEnum.SAME_SUBZONE_CROSS_SWTICH:
                msg, state = cls._check_proxies_same_subzone(
                    racks_map=subzones_racks_map,
                    machines_map=subzones_machines_map,
                    ips_map=subzones_ips_map,
                    expected_subzone_id=expected_subzone_id,
                )
            case AffinityEnum.CROS_SUBZONE:
                msg, state = cls._check_proxies_cross_subzone(
                    subzones_racks_map, subzones_machines_map, subzones_ips_map
                )
            case AffinityEnum.CROSS_RACK:
                msg, state = cls._check_proxies_cross_rack(subzones_racks_map, subzones_machines_map, subzones_ips_map)

        if msg:
            result["state"] = state
            result["msg"] = msg

        return result

    @classmethod
    def _append_suggestion(cls, violation_msg: str, suggestion: str) -> str:
        """Append a normalized suggestion suffix to a violation message."""
        normalized_violation_msg = str(violation_msg).rstrip("。")
        return "{}。{}。".format(normalized_violation_msg, str(_("建议：{}").format(suggestion)))

    @classmethod
    def _get_subzone_display(cls, subzone_id: Union[int, str]) -> str:
        """Get human readable subzone display name with id fallback."""
        subzone_name = cls._subzone_map_cache.get(subzone_id)
        if subzone_name is None:
            subzone_name = cls._subzone_map_cache.get(str(subzone_id))
        if subzone_name is None:
            # Fallback in case helper is used before check initialization.
            subzone_map = BKSubzone.get_subzone_map(get_cache=True)
            subzone_name = subzone_map.get(subzone_id) or subzone_map.get(str(subzone_id))
        return subzone_name or _("园区ID:{}").format(subzone_id)

    @classmethod
    def _pick_ips_from_subzone(
        cls,
        ips_map: dict,
        target_subzone_id: int,
        pick_count: int,
    ) -> List[str]:
        """
        Pick IPs from a target subzone, prioritizing racks with more instances first.
        """
        if pick_count <= 0:
            return []

        candidate_racks = []
        for (subzone_id, rack_id), ips in ips_map.items():
            if subzone_id != target_subzone_id:
                continue
            sorted_ips = sorted(ips)
            candidate_racks.append((rack_id, sorted_ips))

        candidate_racks.sort(key=lambda item: (-len(item[1]), str(item[0])))

        selected_ips: List[str] = []
        for _i, rack_ips in candidate_racks:
            for ip in rack_ips:
                selected_ips.append(ip)
                if len(selected_ips) == pick_count:
                    return selected_ips

        return selected_ips

    @classmethod
    def _build_proxy_same_subzone_multi_subzone_suggestion(
        cls,
        machines_map: dict,
        ips_map: dict,
        expected_subzone_id: Optional[int] = None,
    ) -> str:
        """
        Suggest moving proxies into target subzone from cluster meta if provided.
        Otherwise fallback to majority subzone.
        """
        target_subzone_id = expected_subzone_id
        if target_subzone_id is None:
            target_subzone_id, _x = max(
                sorted(machines_map.items(), key=lambda item: str(item[0])),
                key=lambda item: item[1],
            )

        total_proxy_count = sum(machines_map.values())
        target_subzone_count = machines_map.get(target_subzone_id, 0)
        replace_count = total_proxy_count - target_subzone_count

        non_target_ips = []
        for (subzone_id, _x), ips in sorted(ips_map.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
            if subzone_id != target_subzone_id:
                non_target_ips.extend(sorted(ips))

        selected_ips = non_target_ips[:replace_count]
        target_subzone_display = cls._get_subzone_display(target_subzone_id)
        return _("替换或迁移 {} 台 proxy 机器 [{}]（不在目标园区({})），使所有 proxy 位于同一园区").format(
            replace_count, ", ".join(selected_ips), target_subzone_display
        )

    @classmethod
    def _build_proxy_cross_subzone_suggestion(
        cls,
        subzone_id: int,
        replace_count: int,
        ips_map: dict,
    ) -> str:
        """
        Suggest moving minimal proxies out of an overloaded subzone.
        """
        selected_ips = cls._pick_ips_from_subzone(
            ips_map=ips_map, target_subzone_id=subzone_id, pick_count=replace_count
        )
        subzone_display = cls._get_subzone_display(subzone_id)
        return _("将 {} 台 proxy 机器 [{}]（位于过载园区({})）迁移到其他园区，以满足园区分布要求").format(
            replace_count, ", ".join(selected_ips), subzone_display
        )

    @classmethod
    def _build_proxy_cross_rack_suggestion(
        cls,
        subzone_id: int,
        replace_count: int,
        ips_map: dict,
    ) -> str:
        """
        Suggest moving minimal proxies to different racks/switches in the same subzone.
        """
        selected_ips = cls._pick_ips_from_subzone(
            ips_map=ips_map, target_subzone_id=subzone_id, pick_count=replace_count
        )
        subzone_display = cls._get_subzone_display(subzone_id)
        return _("将 {} 台 proxy 机器 [{}]（位于园区({})）替换或迁移到不同机架，以满足机架分布要求").format(
            replace_count, ", ".join(selected_ips), subzone_display
        )

    @classmethod
    def _build_backend_replace_slave_suggestion(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
        affinity_level: str,
        target_rule_desc: str,
        machines_to_move: Optional[List[Tuple[str, StorageInstance]]] = None,
    ) -> str:
        """
        Suggest replacing/migrating the wrongly placed machine for master-slave topology violations.
        """
        machines_to_move = machines_to_move or [(_("副节点"), slave_obj)]
        machine_desc = str(_(" 和 ")).join(
            _("{}机器 {}").format(role, storage_obj.machine.ip) for role, storage_obj in machines_to_move
        )
        return _("后端主从对 ({}, {}) 不满足亲和级别 '{}'，请将{} 替换或迁移到 {}").format(
            master_obj.machine.ip,
            slave_obj.machine.ip,
            affinity_level,
            machine_desc,
            target_rule_desc,
        )

    @classmethod
    def _check_proxies_same_subzone(
        cls,
        racks_map: dict,
        machines_map: dict,
        ips_map: dict,
        expected_subzone_id: Optional[int] = None,
    ) -> Optional[str]:
        """Check SAME_SUBZONE_CROSS_SWTICH for proxies"""
        proxy_count = sum(machines_map.values())
        subzone_count = len(racks_map.keys())
        if subzone_count != 1:
            all_ips = [ip for ips in ips_map.values() for ip in ips]
            ips_str = ", ".join(all_ips)
            if expected_subzone_id is None:
                violation_msg = _("亲和性违规：Proxy [{}] 分布在 {} 个不同园区，期望为 1 个园区").format(ips_str, subzone_count)
            else:
                expected_subzone_display = cls._get_subzone_display(expected_subzone_id)
                violation_msg = _("亲和性违规：Proxy [{}] 分布在 {} 个不同园区，期望位于集群元数据指定的园区({})").format(
                    ips_str, subzone_count, expected_subzone_display
                )
            suggestion = cls._build_proxy_same_subzone_multi_subzone_suggestion(
                machines_map=machines_map,
                ips_map=ips_map,
                expected_subzone_id=expected_subzone_id,
            )
            return (cls._append_suggestion(violation_msg, suggestion), ReportStateType.ABNORMAL)

        subzone_id = list(racks_map.keys())[0]
        if expected_subzone_id is not None and subzone_id != expected_subzone_id:
            all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
            ips_str = ", ".join(all_ips_in_subzone)
            current_subzone_display = cls._get_subzone_display(subzone_id)
            expected_subzone_display = cls._get_subzone_display(expected_subzone_id)
            violation_msg = _("亲和性违规：Proxy [{}] 位于园区({})，期望位于集群元数据指定的园区({})").format(
                ips_str, current_subzone_display, expected_subzone_display
            )
            suggestion = cls._build_proxy_same_subzone_multi_subzone_suggestion(
                machines_map=machines_map,
                ips_map=ips_map,
                expected_subzone_id=expected_subzone_id,
            )
            return cls._append_suggestion(violation_msg, suggestion), ReportStateType.ABNORMAL

        rack_count = len(list(racks_map.values())[0])
        ok, min_required_racks = cls._cross_rack_check_and_get_limits(proxy_count, rack_count)
        if not ok:
            # Collect all IPs for this subzone across all racks
            all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
            ips_str = ", ".join(all_ips_in_subzone)
            subzone_display = cls._get_subzone_display(subzone_id)
            violation_msg = _("亲和性违规：Proxy [{}] 在园区({}) 内仅分布在 {} 个机架，期望至少 {} 个机架").format(
                ips_str, subzone_display, rack_count, min_required_racks
            )
            replace_count = max(0, min_required_racks - rack_count)
            suggestion = cls._build_proxy_cross_rack_suggestion(
                subzone_id=subzone_id,
                replace_count=replace_count,
                ips_map=ips_map,
            )
            return cls._append_suggestion(violation_msg, suggestion), ReportStateType.WARNING
        return None, ReportStateType.NORMAL

    @classmethod
    def _check_proxies_cross_subzone(cls, racks_map: dict, machines_map: dict, ips_map: dict) -> Optional[str]:
        """Check CROS_SUBZONE for proxies"""
        proxy_count = sum(machines_map.values())
        max_proxies_per_subzone = floor(
            proxy_count / 3 * 2
        )  # We expect each subzone contains no more than 2/3 of all proxies

        for subzone_id in racks_map.keys():
            sub_proxy_count = machines_map[subzone_id]
            # Collect all IPs for this subzone across all racks
            all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
            ips_str = ", ".join(all_ips_in_subzone)

            if sub_proxy_count > max_proxies_per_subzone:
                subzone_display = cls._get_subzone_display(subzone_id)
                violation_msg = _("亲和性违规：{} 个 proxy [{}] 在园区({}) 内超过上限 {}").format(
                    sub_proxy_count, ips_str, subzone_display, max_proxies_per_subzone
                )
                replace_count = sub_proxy_count - max_proxies_per_subzone
                suggestion = cls._build_proxy_cross_subzone_suggestion(
                    subzone_id=subzone_id,
                    replace_count=replace_count,
                    ips_map=ips_map,
                )
                return cls._append_suggestion(violation_msg, suggestion), ReportStateType.ABNORMAL

        return None, ReportStateType.NORMAL

    @classmethod
    def _check_proxies_cross_rack(cls, racks_map: dict, machines_map: dict, ips_map: dict) -> Optional[str]:
        """Check CROSS_RACK for proxies"""
        msg = ""
        for subzone_id, rack_set in racks_map.items():
            rack_count = len(rack_set)
            sub_proxy_count = machines_map[subzone_id]
            ok, min_required_racks = cls._cross_rack_check_and_get_limits(sub_proxy_count, rack_count)
            if not ok:
                # Collect all IPs for this subzone across all racks
                all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
                ips_str = ", ".join(all_ips_in_subzone)
                subzone_display = cls._get_subzone_display(subzone_id)
                violation_msg = _("亲和性违规：{} 个 proxy [{}] 在园区({}) 内仅分布在 {} 个机架，期望至少 {} 个机架\n").format(
                    sub_proxy_count, ips_str, subzone_display, rack_count, min_required_racks
                )
                replace_count = max(0, min_required_racks - rack_count)
                suggestion = cls._build_proxy_cross_rack_suggestion(
                    subzone_id=subzone_id,
                    replace_count=replace_count,
                    ips_map=ips_map,
                )
                msg += cls._append_suggestion(violation_msg.rstrip("\n"), suggestion) + "\n"
        return msg, ReportStateType.ABNORMAL if msg else ReportStateType.NORMAL

    @classmethod
    def _cross_rack_check_and_get_limits(cls, n_proxy, n_rack) -> Tuple[bool, int]:
        """Based on the #proxy and #rack in a subzone, determine if it's acceptable"""
        min_required_racks = floor(n_proxy / 2 + 1)
        return n_rack >= min_required_racks, min_required_racks

    @classmethod
    def _validate_backends_affinity(
        cls,
        master_instances,
        affinity_level: AffinityEnum,
        expected_subzone_id: Optional[int] = None,
    ) -> Dict[str, Dict[str, any]]:
        """
        Check if the master-slave pairs in cluster fulfill the affinity level

        Return:
            Dict {<master_ip>: {msg: str, state: ReportStateType, machine_type: MachineType}}
        """
        machine_instances = defaultdict(list)
        for master_obj in master_instances:
            master_ip = master_obj.machine.ip
            machine_instances[master_ip].append(master_obj)

        backend_results = {}
        for master_ip, instances in machine_instances.items():
            backend_result, slave_ips = cls._check_master_slave_affinity(
                master_instances=instances,
                affinity_level=affinity_level,
                expected_subzone_id=expected_subzone_id,
            )
            identifier = master_ip if slave_ips is None else ", ".join(slave_ips)
            backend_results[identifier] = backend_result

        return backend_results

    @classmethod
    def _check_master_slave_affinity(
        cls,
        master_instances: List[StorageInstance],
        affinity_level: str,
        expected_subzone_id: Optional[int] = None,
    ) -> Tuple[Dict[str, any], List[str]]:
        """
        Check affinity for all instances on a master machine
        Collects slaves from all instances on the machine and checks affinity once per machine

        Returns:
            Dict: {msg: str, state: ReportStateType, machine_type: MachineType}
            List: list of unique slave machine IPs
        """
        first_master = master_instances[0]
        master_ip = first_master.machine.ip

        result = {
            "msg": "",
            "state": ReportStateType.NORMAL.value,
            "machine_type": first_master.machine_type,
        }

        all_slave_machines = {}  # {slave_machine_ip: slave_obj}
        instances_without_slaves = []

        for master_obj in master_instances:
            try:
                slave_tuples = list(master_obj.as_ejector.all())
                if not slave_tuples:
                    instances_without_slaves.append(master_obj.ip_port)
                    continue
                for slave_tuple in slave_tuples:
                    slave_obj = slave_tuple.receiver
                    slave_machine_ip = slave_obj.machine.ip
                    if slave_machine_ip not in all_slave_machines:
                        all_slave_machines[slave_machine_ip] = slave_obj
            except Exception as e:
                warning_msg = _("Error getting slaves for instance {}: {}").format(master_obj.ip_port, str(e))
                logger.warning("affinity_check: %s", warning_msg, exc_info=True)
                instances_without_slaves.append(master_obj.ip_port)

        if not all_slave_machines:
            warning_msg = _("Master machine {} has no slave configured").format(master_ip)
            if instances_without_slaves:
                warning_msg += _(" (instances: {})").format(", ".join(instances_without_slaves))
            logger.warning("affinity_check: %s", warning_msg)
            result["msg"] = warning_msg
            result["state"] = ReportStateType.WARNING.value
            return result, None

        violating_slaves = []
        compliant_slaves = []
        violation_msgs = []

        for slave_machine_ip, slave_obj in all_slave_machines.items():
            msg = None
            match affinity_level:
                case AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value:
                    msg = cls._check_backend_same_subzone(
                        first_master,
                        slave_obj,
                        expected_subzone_id=expected_subzone_id,
                    )
                case AffinityEnum.CROS_SUBZONE.value:
                    msg = cls._check_backend_cross_subzone(first_master, slave_obj)
                case AffinityEnum.CROSS_RACK.value:
                    msg = cls._check_backend_cross_rack(first_master, slave_obj)

            if msg:  # Has violation
                violation_msgs.append(msg)
                violating_slaves.append(slave_machine_ip)
            else:
                compliant_slaves.append(slave_machine_ip)

        if violation_msgs:
            result["msg"] = "; ".join(str(msg) for msg in violation_msgs)
            result["state"] = ReportStateType.ABNORMAL.value
        else:
            slaves_str = ", ".join(compliant_slaves)
            result["msg"] = _("Master machine: {} and slave machines: {} comply with affinity level '{}'").format(
                master_ip, slaves_str, affinity_level
            )

        return result, violating_slaves

    @classmethod
    def _check_backend_same_subzone(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
        expected_subzone_id: Optional[int] = None,
    ) -> Optional[str]:
        """Check SAME_SUBZONE_CROSS_SWTICH affinity for master-slave pair"""
        master_subzone_id = master_obj.machine.bk_sub_zone_id
        slave_subzone_id = slave_obj.machine.bk_sub_zone_id

        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            expected_display = (
                cls._get_subzone_display(expected_subzone_id) if expected_subzone_id is not None else None
            )
            master_subzone_display = cls._get_subzone_display(master_subzone_id)
            slave_subzone_display = cls._get_subzone_display(slave_subzone_id)
            violation_msg = _("亲和性违规：主节点 {} 位于园区({})，副节点 {} 位于园区({})，期望位于同一园区").format(
                master_obj.machine.ip,
                master_subzone_display,
                slave_obj.machine.ip,
                slave_subzone_display,
            )
            target_rule_desc = (
                _("园区({}) 且不同机架").format(expected_display)
                if expected_display
                else _("与主节点 {} 位于同一园区且不同机架").format(master_obj.machine.ip)
            )
            machines_to_move = None
            if expected_subzone_id is not None:
                machines_to_move = []
                if master_subzone_id != expected_subzone_id:
                    machines_to_move.append((_("主节点"), master_obj))
                if slave_subzone_id != expected_subzone_id:
                    machines_to_move.append((_("副节点"), slave_obj))
            suggestion = cls._build_backend_replace_slave_suggestion(
                master_obj=master_obj,
                slave_obj=slave_obj,
                affinity_level=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
                target_rule_desc=target_rule_desc,
                machines_to_move=machines_to_move,
            )
            return cls._append_suggestion(violation_msg, suggestion)

        if expected_subzone_id is not None and master_subzone_id != expected_subzone_id:
            current_subzone_display = cls._get_subzone_display(master_subzone_id)
            expected_subzone_display = cls._get_subzone_display(expected_subzone_id)
            violation_msg = _("亲和性违规：主节点 {} 与副节点 {} 位于园区({})，期望位于集群元数据指定的园区({})").format(
                master_obj.machine.ip,
                slave_obj.machine.ip,
                current_subzone_display,
                expected_subzone_display,
            )
            suggestion = cls._build_backend_replace_slave_suggestion(
                master_obj=master_obj,
                slave_obj=slave_obj,
                affinity_level=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
                target_rule_desc=_("园区({}) 且不同机架").format(expected_subzone_display),
                machines_to_move=[(_("主节点"), master_obj), (_("副节点"), slave_obj)],
            )
            return cls._append_suggestion(violation_msg, suggestion)

        return cls._check_backend_cross_rack(
            master_obj=master_obj,
            slave_obj=slave_obj,
            affinity_level=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
            target_rule_desc=_("与主节点 {} 位于同一园区且不同机架").format(master_obj.machine.ip),
        )

    @classmethod
    def _check_backend_cross_subzone(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """Check CROS_SUBZONE affinity for master-slave pair"""
        if master_obj.machine.bk_sub_zone_id == slave_obj.machine.bk_sub_zone_id:
            violation_msg = _("亲和性违规：主节点 {} 与副节点 {} 位于同一园区，期望位于不同园区").format(
                master_obj.machine.ip, slave_obj.machine.ip
            )
            suggestion = cls._build_backend_replace_slave_suggestion(
                master_obj=master_obj,
                slave_obj=slave_obj,
                affinity_level=AffinityEnum.CROS_SUBZONE.value,
                target_rule_desc=_("与主节点 {} 不同的园区").format(master_obj.machine.ip),
            )
            return cls._append_suggestion(violation_msg, suggestion)
        return None

    @classmethod
    def _check_backend_cross_rack(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
        affinity_level: str = AffinityEnum.CROSS_RACK.value,
        target_rule_desc: Optional[str] = None,
    ) -> Optional[str]:
        """Check CROSS_RACK affinity for master-slave pair"""
        # If they are in different subzones, CROSS_RACK is satisfied regardless of rack
        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            return None

        # Same subzone (or subzone unknown) - must be in different racks
        if master_obj.machine.bk_rack_id == slave_obj.machine.bk_rack_id:
            violation_msg = _("亲和性违规：主节点 {} 与副节点 {} 位于同一机架，期望位于不同机架").format(
                master_obj.machine.ip, slave_obj.machine.ip
            )
            final_target_rule = target_rule_desc or _("与主节点 {} 不同的机架（或不同园区）").format(master_obj.machine.ip)
            suggestion = cls._build_backend_replace_slave_suggestion(
                master_obj=master_obj,
                slave_obj=slave_obj,
                affinity_level=affinity_level,
                target_rule_desc=final_target_rule,
            )
            return cls._append_suggestion(violation_msg, suggestion)
        return None

    def _build_affinity_report_rows(
        self,
        cluster: Cluster,
        affinity_level: str,
        check_results: list[Dict],
        creator: str = "admin",
    ) -> List[dict]:
        """
        Build affinity check report rows for bulk write.
        """
        failed_checks = [result for result in check_results if result["state"] != ReportStateType.NORMAL.value]
        has_violations = len(failed_checks) > 0

        total_machines = 0
        backend_pair_count = 0
        for result in check_results:
            if result["result_type"] == RedisAffinityChecker.PROXY_DISTRIBUTION_CHECK:
                total_machines += result.get("proxy_count", 0)
            elif result["result_type"] == RedisAffinityChecker.BACKEND_PAIRS_CHECK:
                backend_pair_count += 1
        total_machines += backend_pair_count * 2

        if not has_violations:
            msg = _("Affinity check passed: All {} machines comply with affinity level '{}'").format(
                total_machines, affinity_level
            )
            logger.info("affinity_check: cluster %s passed affinity check", cluster.immute_domain)
            return [
                {
                    "cluster": cluster,
                    "ip": "all",
                    "port": None,
                    "subtype": MetaCheckSubType.AffinityViolation,
                    "msg": msg,
                    "state": ReportStateType.NORMAL,
                    "creator": creator,
                }
            ]

        total_warnings = sum(1 for result in failed_checks if result["state"] == ReportStateType.WARNING.value)
        total_violations = len(failed_checks) - total_warnings
        logger.warning(
            "affinity_check: cluster %s has %s affinity violations and %s warnings",
            cluster.immute_domain,
            total_violations,
            total_warnings,
        )

        rows = []
        for result in failed_checks:
            rows.append(
                {
                    "cluster": cluster,
                    "ip": result["identifier"],
                    "port": None,
                    "subtype": MetaCheckSubType.AffinityViolation,
                    "msg": result["msg"],
                    "state": result["state"],
                    "machine_type": result.get("machine_type"),
                    "creator": creator,
                }
            )
        return rows

    def _create_affinity_reports(
        self,
        cluster: Cluster,
        affinity_level: str,
        check_results: list[Dict],
        creator: str = "admin",
    ) -> None:
        """Backward-compatible wrapper for single-cluster debug flows."""
        rows = self._build_affinity_report_rows(cluster, affinity_level, check_results, creator)
        if rows:
            safe_write_meta_reports(self._writer, rows, context=f"cluster={cluster.immute_domain}")
