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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Set

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils import dns_manage
from backend.flow.utils.clb_manage import get_clb_by_ip
from backend.flow.utils.polaris_manage import GetPolarisManageByName
from backend.flow.utils.redis.redis_meta_report import create_meta_check_report

logger = logging.getLogger("flow")


class RedisEntryCheckService(BaseService):
    """
    Service for checking Redis cluster entry consistency
    """

    @staticmethod
    def _get_cluster_proxy_ips(cluster: Cluster) -> Set[str]:
        """
        Get all proxy IPs from cluster metadata

        Args:
            cluster: Cluster object

        Returns:
            Set of proxy IP addresses
        """
        return set(cluster.proxyinstance_set.values_list("machine__ip", flat=True))

    @staticmethod
    def _get_dns_proxy_ips(cluster: Cluster, entry: ClusterEntry) -> Set[str]:
        """
        Get proxy IPs registered in DNS for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with DNS type

        Returns:
            Set of proxy IP addresses in DNS
        """
        try:
            if entry.forward_to:
                return set()

            dns_results = dns_manage.DnsManage(
                bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id
            ).get_domain(domain_name=entry.entry)

            return {result["ip"] for result in dns_results}
        except Exception as e:
            logger.exception(
                _("Failed to get DNS records for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set()

    @staticmethod
    def _get_clb_proxy_ips(cluster: Cluster, entry: ClusterEntry) -> Set[str]:
        """
        Get proxy IPs registered in CLB for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with CLB type

        Returns:
            Set of proxy IP addresses in CLB (ports stripped)
        """
        try:
            clb_detail = entry.detail
            # Use helper function to get CLBManage instance
            clb_manager = get_clb_by_ip(clb_detail["clb_ip"])

            # Use CLBManage to get registered IPs
            raw_ips = clb_manager.get_clb_rs()
            # CLB returns IPs with ports (e.g., "1.1.1.1:30000"), strip the port
            return {ip.split(":")[0] for ip in raw_ips}

        except Exception as e:
            logger.exception(
                _("Failed to get CLB targets for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set()

    @staticmethod
    def _get_polaris_proxy_ips(cluster: Cluster, entry: ClusterEntry) -> Set[str]:
        """
        Get proxy IPs registered in Polaris for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with POLARIS type

        Returns:
            Set of proxy IP addresses in Polaris (ports stripped)
        """
        try:
            polaris_detail = entry.detail
            # Use helper function to get PolarisManage instance
            polaris_manager = GetPolarisManageByName(polaris_detail["polaris_name"])

            # Use PolarisManage to get registered IPs
            raw_ips = polaris_manager.get_polaris_rs()
            # Polaris returns IPs with ports (e.g., "1.1.1.1:30000"), strip the port
            return {ip.split(":")[0] for ip in raw_ips}

        except Exception as e:
            logger.exception(
                _("Failed to get Polaris targets for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set()

    @staticmethod
    def _check_entry_consistency(cluster: Cluster, entry: ClusterEntry, expected_ips: Set[str]) -> Optional[Dict]:
        """
        Check if an entry has the exact same proxies as expected

        Args:
            cluster: Cluster object
            entry: ClusterEntry object
            expected_ips: Expected set of proxy IPs

        Returns:
            Dict with error details if inconsistent, None if consistent
        """
        entry_type = entry.cluster_entry_type

        # Get actual IPs from the entry system
        match entry_type:
            case ClusterEntryType.DNS.value:
                actual_ips = RedisEntryCheckService._get_dns_proxy_ips(cluster, entry)
                if entry.forward_to:
                    # DNS is forwarding to CLB ip, skip this condition
                    return None
            case ClusterEntryType.CLB.value:
                actual_ips = RedisEntryCheckService._get_clb_proxy_ips(cluster, entry)
            case ClusterEntryType.POLARIS.value:
                actual_ips = RedisEntryCheckService._get_polaris_proxy_ips(cluster, entry)
            case ClusterEntryType.CLBDNS.value:
                # CLBDNS is just a pointer, skip checking
                return None
            case _:
                logger.warning(
                    _("Unknown entry type {} for cluster {} entry {}").format(
                        entry_type, cluster.immute_domain, entry.entry
                    )
                )
                return None

        # Compare expected vs actual
        missing_ips = expected_ips - actual_ips
        extra_ips = actual_ips - expected_ips

        if missing_ips or extra_ips:
            error_detail = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.immute_domain,
                "entry_type": entry_type,
                "entry_name": entry.entry,
                "expected_ips": sorted(list(expected_ips)),
                "actual_ips": sorted(list(actual_ips)),
                "missing_ips": sorted(list(missing_ips)),
                "extra_ips": sorted(list(extra_ips)),
            }
            return error_detail

        return None

    @staticmethod
    def _create_cluster_report(cluster: Cluster, all_error_details: list):
        """
        Create a single meta check report for all entry inconsistencies in a cluster

        Args:
            cluster: Cluster object
            all_error_details: List of error detail dicts from all entries
        """
        if not all_error_details:
            # No inconsistencies, create a NORMAL report
            create_meta_check_report(
                cluster=cluster,
                ip=None,
                port=None,
                subtype=MetaCheckSubType.EntryInconsistent,
                msg=_("All entries are consistent."),
                state=ReportStateType.NORMAL,
            )
            return

        # Build a comprehensive description for all inconsistencies
        description_parts = []
        for error_detail in all_error_details:
            entry_type = error_detail["entry_type"]
            entry_name = error_detail["entry_name"]
            missing_ips = error_detail["missing_ips"]
            extra_ips = error_detail["extra_ips"]

            entry_desc_parts = []
            if missing_ips:
                entry_desc_parts.append(_("missing: {}").format(", ".join(missing_ips)))
            if extra_ips:
                entry_desc_parts.append(_("extra: {}").format(", ".join(extra_ips)))

            if entry_desc_parts:
                description_parts.append(_("{} ({}): {}").format(entry_type, entry_name, "; ".join(entry_desc_parts)))

        description = "; ".join(description_parts)

        create_meta_check_report(
            cluster=cluster,
            ip=None,
            port=None,
            subtype=MetaCheckSubType.EntryInconsistent,
            msg=description,
            state=ReportStateType.ABNORMAL,
        )

        logger.warning(
            _("Entry inconsistencies detected for cluster {}: {}").format(cluster.immute_domain, description)
        )

    @staticmethod
    def _check_single_cluster(cluster_id: int) -> Dict:
        """
        Check entries for a single cluster

        Args:
            cluster_id: ID of the cluster to check
            bk_cloud_id: BK cloud ID for the cluster

        Returns:
            Dict with check results
        """
        try:
            cluster = Cluster.objects.prefetch_related("proxyinstance_set", "clusterentry_set").get(id=cluster_id)
            cluster_domain = cluster.immute_domain

            # Get expected proxy IPs from cluster metadata
            expected_proxy_ips = RedisEntryCheckService._get_cluster_proxy_ips(cluster)

            if not expected_proxy_ips:
                logger.warning(_("Cluster {} has no proxies in metadata, skipping").format(cluster_domain))
                return {"cluster_id": cluster_id, "checked": 0, "inconsistent": 0}

            # Check each entry and collect all error details
            entries = cluster.clusterentry_set.all()
            checked_count = 0
            all_error_details = []

            for entry in entries:
                checked_count += 1
                error_detail = RedisEntryCheckService._check_entry_consistency(cluster, entry, expected_proxy_ips)

                if error_detail:
                    all_error_details.append(error_detail)

            # Create a single report for the cluster (success or failure)
            RedisEntryCheckService._create_cluster_report(cluster, all_error_details)

            inconsistent_count = len(all_error_details)
            return {"cluster_id": cluster_id, "checked": checked_count, "inconsistent": inconsistent_count}

        except Cluster.DoesNotExist:
            logger.warning(_("Cluster id={} not found, skipping").format(cluster_id))
            return {"cluster_id": cluster_id, "checked": 0, "inconsistent": 0, "error": "Cluster not found"}
        except Exception as e:
            logger.exception(_("Failed to check entries for cluster id={}: {}").format(cluster_id, str(e)))
            return {"cluster_id": cluster_id, "checked": 0, "inconsistent": 0, "error": str(e)}

    def _execute(self, data, parent_data) -> bool:
        """
        Execute entry check for a batch of clusters

        Args:
            data: Component data
            parent_data: Parent pipeline data

        Returns:
            True if successful, False otherwise
        """
        kwargs = data.get_one_of_inputs("kwargs")
        # cluster_ids is a list of cluster IDs
        cluster_ids = kwargs["cluster_ids"]

        logger.info(_("Starting entry check for {} clusters").format(len(cluster_ids)))

        # Track statistics
        total_checked = 0
        total_inconsistent = 0

        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(20, len(cluster_ids))  # Limit to 20 concurrent threads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all cluster checks
            future_to_cluster = {
                executor.submit(self._check_single_cluster, cluster_id): cluster_id for cluster_id in cluster_ids
            }

            # Process results as they complete
            for future in as_completed(future_to_cluster):
                cluster_id = future_to_cluster[future]
                try:
                    result = future.result()
                    total_checked += result.get("checked", 0)
                    total_inconsistent += result.get("inconsistent", 0)
                except Exception as e:
                    logger.exception(_("Exception checking cluster id={}: {}").format(cluster_id, str(e)))

        # Log summary
        logger.info(
            _("Entry check completed for batch: {} entries checked, {} inconsistencies found").format(
                total_checked, total_inconsistent
            )
        )

        self.log_info(_("Entry check completed successfully"))
        return True


class RedisEntryCheckComponent(Component):
    """
    Component for Redis entry consistency check
    """

    name = __name__
    code = "redis_entry_check"
    bound_service = RedisEntryCheckService
