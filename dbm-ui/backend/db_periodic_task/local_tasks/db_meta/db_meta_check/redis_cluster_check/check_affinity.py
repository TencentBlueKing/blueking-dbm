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
from math import floor
from typing import Dict, Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import AffinityEnum, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models.ticket import ClusterOperateRecord

from .base import create_meta_check_report, delete_old_meta_check_reports, is_cluster_labeled_with

logger = logging.getLogger("root")


def check_redis_affinity():
    """
    检查集群中的主从机器是否满足集群亲和性要求
    """
    RedisAffinityChecker().check_all_clusters()


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

    def __init__(self):
        """Initialize the affinity checker"""
        # ClusterTypes that need to check
        self._supported_cluster_types = [
            ClusterType.TendisTwemproxyRedisInstance.value,  # TendisCache 集群
            ClusterType.TwemproxyTendisSSDInstance.value,  # TendisSSD 集群
            ClusterType.TendisPredixyRedisCluster.value,  # RedisCluster 集群
            ClusterType.TendisPredixyTendisplusCluster.value,  # Tendisplus 集群
            ClusterType.TendisRedisInstance.value,  # Redis 主从
        ]
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
        }

    def check_all_clusters(self) -> None:
        """
        Check affinity for all Redis clusters
        """
        delete_old_meta_check_reports(MetaCheckSubType.AffinityViolation, self._supported_cluster_types, 30)
        for cluster in Cluster.objects.filter(Q(cluster_type__in=self._supported_cluster_types)):
            try:
                self._check_cluster_affinity(cluster)
            except Exception as e:
                logger.error(f"affinity_check: error checking cluster {cluster.immute_domain}: {e}", exc_info=True)

    def _check_cluster_affinity(self, cluster: Cluster) -> None:
        """
        Check master-slave affinity for a single cluster
        """
        logger.info(f"affinity_check: start checking cluster {cluster.immute_domain}")

        if self._should_ignore_cluster(cluster):
            return

        dba_list = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.Redis.value)
        creator = dba_list[0] if dba_list else "admin"

        affinity_level = cluster.disaster_tolerance_level
        if affinity_level not in self._supported_levels:
            supported_levels_str = ", ".join(self._supported_levels)
            msg = _(
                "Cannot perform affinity check: Unsupported affinity level '{}' for Redis. " "Supported levels are: {}"
            ).format(affinity_level, supported_levels_str)
            logger.warning(f"affinity_check: {msg}")
            create_meta_check_report(
                cluster=cluster,
                ip="none",
                port=None,
                subtype=MetaCheckSubType.AffinityViolation,
                msg=msg,
                state=ReportStateType.WARNING,
                creator=creator,
            )
            return

        check_results = []

        # Skip proxy check if cluster is RedisInstance or labeled
        skip_proxy_check = cluster.cluster_type == ClusterType.RedisInstance.value or is_cluster_labeled_with(
            cluster,
            self.SKIP_PROXY_CHECK_LABEL,
        )

        # For proxies, we check the stats of their locations
        if not skip_proxy_check:
            proxy_instances = cluster.proxyinstance_set.filter()
            proxy_result = self._validate_proxies_affinity(proxy_instances, affinity_level)
            proxy_result["result_type"] = RedisAffinityChecker.PROXY_DISTRIBUTION_CHECK
            proxy_result["identifier"] = "proxies"
            check_results.append(proxy_result)

        # For backends, we check each master-slave pair
        master_instances = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
        backend_results = self._validate_backends_affinity(master_instances, affinity_level)
        for machine_ip, result in backend_results.items():
            result["result_type"] = RedisAffinityChecker.BACKEND_PAIRS_CHECK
            result["identifier"] = machine_ip
            check_results.append(result)

        # Create reports based on results
        self._create_affinity_reports(
            cluster=cluster,
            affinity_level=affinity_level,
            check_results=check_results,
            creator=creator,
        )

    def _should_ignore_cluster(self, cluster: Cluster) -> bool:
        """
        Check if cluster should be ignored (being destroyed, disabled, or has active operations)
        """
        if cluster.phase != ClusterPhase.ONLINE.value:
            logger.info(
                f"affinity_check: will ignore cluster {cluster.immute_domain}, "
                f"cluster phase is {cluster.phase} (not online)"
            )
            return True

        if ClusterOperateRecord.objects.filter(
            ticket__ticket_type__in=self._ignore_tickets,
            ticket__status__in=TICKET_RUNNING_STATUS_SET,
            cluster_id=cluster.id,
        ).exists():
            logger.info(
                f"affinity_check: will ignore cluster {cluster.immute_domain}, it has active destroy/disable ticket"
            )
            return True

        return False

    @classmethod
    def _validate_proxies_affinity(cls, proxy_instances, affinity_level: AffinityEnum) -> Dict[str, any]:
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
                    subzones_racks_map, subzones_machines_map, subzones_ips_map
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
    def _check_proxies_same_subzone(cls, racks_map: dict, machines_map: dict, ips_map: dict) -> Optional[str]:
        """Check SAME_SUBZONE_CROSS_SWTICH for proxies"""
        proxy_count = sum(machines_map.values())
        subzone_count = len(racks_map.keys())
        if subzone_count != 1:
            all_ips = [ip for ips in ips_map.values() for ip in ips]
            ips_str = ", ".join(all_ips)
            return (
                _("Affinity violation: proxies [{}] are in {} different subzones, expected 1").format(
                    ips_str, subzone_count
                ),
                ReportStateType.ABNORMAL,
            )

        subzone_id = list(racks_map.keys())[0]
        rack_count = len(list(racks_map.values())[0])
        ok, min_required_racks = cls._cross_rack_check_and_get_limits(proxy_count, rack_count)
        if not ok:
            # Collect all IPs for this subzone across all racks
            all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
            ips_str = ", ".join(all_ips_in_subzone)
            msg = _(
                "Affinity violation: proxies [{}] in subzone(id: {}) are in {} rack(s), expected at least {} racks"
            ).format(ips_str, subzone_id, rack_count, min_required_racks)
            return msg, ReportStateType.WARNING
        return None, ReportStateType.NORMAL

    @classmethod
    def _check_proxies_cross_subzone(cls, racks_map: dict, machines_map: dict, ips_map: dict) -> Optional[str]:
        """Check CROS_SUBZONE for proxies"""
        proxy_count = sum(machines_map.values())
        max_proxies_per_subzone = floor(
            proxy_count / 3 * 2
        )  # We expect each subzone contains no more than 2/3 of all proxies

        for subzone_id, rack_set in racks_map.items():
            sub_proxy_count = machines_map[subzone_id]
            # Collect all IPs for this subzone across all racks
            all_ips_in_subzone = [ip for (sz_id, _), ips in ips_map.items() if sz_id == subzone_id for ip in ips]
            ips_str = ", ".join(all_ips_in_subzone)

            if sub_proxy_count > max_proxies_per_subzone:
                msg = _("Affinity violation: {} proxies [{}] in subzone(id: {}) exceed the limit of {}").format(
                    sub_proxy_count, ips_str, subzone_id, max_proxies_per_subzone
                )
                return msg, ReportStateType.ABNORMAL

            rack_count = len(rack_set)
            ok, min_required_racks = cls._cross_rack_check_and_get_limits(sub_proxy_count, rack_count)
            if not ok:
                msg = _(
                    "Affinity violation: {} proxies [{}] in subzone(id: {}) are in {} rack(s), expected at least {} racks"
                ).format(sub_proxy_count, ips_str, subzone_id, rack_count, min_required_racks)
                return msg, ReportStateType.WARNING

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
                msg += _(
                    "Affinity violation: {} proxies [{}] in subzone(id: {}) are in {} rack(s), expected at least {} racks\n"
                ).format(sub_proxy_count, ips_str, subzone_id, rack_count, min_required_racks)
        return msg, ReportStateType.ABNORMAL if msg else ReportStateType.NORMAL

    @classmethod
    def _cross_rack_check_and_get_limits(cls, n_proxy, n_rack) -> Tuple[bool, int]:
        """Based on the #proxy and #rack in a subzone, determine if it's acceptable"""
        min_required_racks = floor(n_proxy / 2 + 1)
        return n_rack >= min_required_racks, min_required_racks

    @classmethod
    def _validate_backends_affinity(cls, master_instances, affinity_level: AffinityEnum) -> Dict[str, Dict[str, any]]:
        """
        Check if the master-slave pairs in cluster fulfill the affinity level

        Return:
            Dict {<master_ip>: {msg: str, state: ReportStateType, machine_type: MachineType}}
        """
        backend_results = {}
        for master_obj in master_instances:
            machine_ip = master_obj.machine.ip
            if machine_ip in backend_results:
                continue

            backend_result = cls._check_master_slave_affinity(master_obj=master_obj, affinity_level=affinity_level)
            backend_results[machine_ip] = backend_result

        return backend_results

    @classmethod
    def _check_master_slave_affinity(cls, master_obj: StorageInstance, affinity_level: str) -> Dict[str, any]:
        """
        Check if a master-slave pair fulfills the affinity requirement

        Returns:
            Dict: {msg: str, state: ReportStateType, machine_type: MachineType}
        """
        result = {
            "msg": "",
            "state": ReportStateType.NORMAL.value,
            "machine_type": master_obj.machine_type,
        }

        try:
            slave_obj = master_obj.as_ejector.get().receiver
        except ObjectDoesNotExist:
            warning_msg = _("Master {} has no slave configured").format(master_obj.ip_port)
            logger.warning(f"affinity_check: {warning_msg}")
            result["msg"] = warning_msg
            result["state"] = ReportStateType.WARNING.value
            return result
        except Exception as e:
            warning_msg = _("Unknown error occurred when getting slave: {}").format(str(e))
            logger.warning(f"affinity_check: {warning_msg}", exc_info=True)
            result["msg"] = warning_msg
            result["state"] = ReportStateType.WARNING.value
            return result

        msg = None
        match affinity_level:
            case AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value:
                msg = cls._check_backend_same_subzone(master_obj, slave_obj)
            case AffinityEnum.CROS_SUBZONE.value:
                msg = cls._check_backend_cross_subzone(master_obj, slave_obj)
            case AffinityEnum.CROSS_RACK.value:
                msg = cls._check_backend_cross_rack(master_obj, slave_obj)

        if msg:  # Has violation
            result["msg"] = msg
            result["state"] = ReportStateType.ABNORMAL.value
        else:
            result["msg"] = _("Master: {} and slave: {} comply with affinity level '{}'").format(
                master_obj.machine.ip, slave_obj.machine.ip, affinity_level
            )

        return result

    @classmethod
    def _check_backend_same_subzone(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """Check SAME_SUBZONE_CROSS_SWTICH affinity for master-slave pair"""
        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            return _(
                "Affinity violation: master {} and slave {} " "are in different subzones, expected the same subzone"
            ).format(master_obj.machine.ip, slave_obj.machine.ip)

        return cls._check_backend_cross_rack(master_obj, slave_obj)

    @classmethod
    def _check_backend_cross_subzone(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """Check CROS_SUBZONE affinity for master-slave pair"""
        if master_obj.machine.bk_sub_zone_id == slave_obj.machine.bk_sub_zone_id:
            return _(
                "Affinity violation: master {} and slave {} " "are in the same subzone, expected different subzones"
            ).format(master_obj.machine.ip, slave_obj.machine.ip)
        return None

    @classmethod
    def _check_backend_cross_rack(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """Check CROSS_RACK affinity for master-slave pair"""
        # If they are in different subzones, CROSS_RACK is satisfied regardless of rack
        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            return None

        # Same subzone (or subzone unknown) - must be in different racks
        if master_obj.machine.bk_rack_id == slave_obj.machine.bk_rack_id:
            return _(
                "Affinity violation: master {} and slave {} " "are in the same rack, expected different racks"
            ).format(master_obj.machine.ip, slave_obj.machine.ip)
        return None

    @classmethod
    def _create_affinity_reports(
        cls,
        cluster: Cluster,
        affinity_level: str,
        check_results: list[Dict],
        creator: str = "admin",
    ) -> None:
        """
        Create affinity check reports

        Strategy:
        - If all checks pass: Create 1 cluster-level success record
        - If any violations/warnings: Create individual records for each failed check only

        Args:
            cluster: Cluster object
            affinity_level: Affinity level being checked
            check_results: List of check results, each containing:
                - result_type: str ('proxy_distribution', 'backend_pair', 'proxy_master_colocation')
                - identifier: str (IP address or identifier for the report)
                - state: ReportStateType
                - msg: str
                - machine_type: MachineType (optional, depends on result_type)
                - proxy_count: int (only for proxy_distribution)
        """
        # Count failed checks
        failed_checks = [result for result in check_results if result["state"] != ReportStateType.NORMAL.value]
        has_violations = len(failed_checks) > 0

        # Calculate total machines for success message
        total_machines = 0
        backend_pair_count = 0
        for result in check_results:
            if result["result_type"] == RedisAffinityChecker.PROXY_DISTRIBUTION_CHECK:
                total_machines += result.get("proxy_count", 0)
            elif result["result_type"] == RedisAffinityChecker.BACKEND_PAIRS_CHECK:
                backend_pair_count += 1
        total_machines += backend_pair_count * 2  # Each backend pair has 2 machines

        if not has_violations:
            msg = _("Affinity check passed: All {} machines comply with " "affinity level '{}'").format(
                total_machines, affinity_level
            )
            logger.info(f"affinity_check: cluster {cluster.immute_domain} passed affinity check")

            create_meta_check_report(
                cluster=cluster,
                ip="all",  # Cluster-level report
                port=None,
                subtype=MetaCheckSubType.AffinityViolation,
                msg=msg,
                state=ReportStateType.NORMAL,
                creator=creator,
            )
        else:
            total_warnings = sum(1 for result in failed_checks if result["state"] == ReportStateType.WARNING.value)
            total_violations = len(failed_checks) - total_warnings

            logger.warning(
                f"affinity_check: cluster {cluster.immute_domain} has {total_violations} "
                f"affinity violations and {total_warnings} warnings"
            )

            # Create individual report for each failed check
            for result in failed_checks:
                create_meta_check_report(
                    cluster=cluster,
                    ip=result["identifier"],
                    port=None,
                    subtype=MetaCheckSubType.AffinityViolation,
                    msg=result["msg"],
                    state=result["state"],
                    machine_type=result.get("machine_type"),
                    creator=creator,
                )
