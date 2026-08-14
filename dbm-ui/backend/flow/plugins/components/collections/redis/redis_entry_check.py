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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_abnormal_cluster_rows
from backend.db_services.redis.util import is_have_proxy
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils import dns_manage
from backend.flow.utils.clb_manage import get_clb_by_ip
from backend.flow.utils.polaris_manage import GetPolarisManageByName
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter, safe_write_meta_reports
from backend.utils.redis import RedisConn

# Default batch size and interval for scheduled processing
DEFAULT_BATCH_SIZE = 15
DEFAULT_BATCH_INTERVAL = 2  # seconds between batches


class RedisEntryCheckService(BaseService):
    """
    Service for checking Redis cluster entry consistency using scheduled component pattern.

    This service retrieves cluster_ids from Redis and processes them in batches.
    Each schedule iteration processes one batch of clusters.
    """

    __need_schedule__ = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Interval will be set dynamically in _execute based on batch_interval parameter
        self.interval = StaticIntervalGenerator(DEFAULT_BATCH_INTERVAL)

    @staticmethod
    def _get_cluster_proxy_ips(cluster: Cluster) -> Set[str]:
        return {proxy.machine.ip for proxy in cluster.proxyinstance_set.all()}

    @staticmethod
    def _get_cluster_storage_ips(cluster: Cluster) -> Set[str]:
        return {storage.machine.ip for storage in cluster.storageinstance_set.all()}

    @staticmethod
    def _get_cluster_master_ips(cluster: Cluster) -> Set[str]:
        return {
            storage.machine.ip
            for storage in cluster.storageinstance_set.all()
            if storage.instance_inner_role == InstanceInnerRole.MASTER
        }

    @staticmethod
    def _get_cluster_slave_ips(cluster: Cluster) -> Set[str]:
        return {
            storage.machine.ip
            for storage in cluster.storageinstance_set.all()
            if storage.instance_inner_role == InstanceInnerRole.SLAVE
        }

    @staticmethod
    def _load_batch_clusters(cluster_ids: List[int]) -> Dict[int, Cluster]:
        if not cluster_ids:
            return {}
        return {
            cluster.id: cluster
            for cluster in Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
                "proxyinstance_set__machine",
                "storageinstance_set__machine",
                "clusterentry_set",
            )
        }

    def _get_dns_ips(self, cluster: Cluster, entry: ClusterEntry) -> Tuple[Set[str], Optional[str]]:
        """
        Get IPs registered in DNS for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with DNS type

        Returns:
            Tuple of (Set of IP addresses in DNS, error message if any)
        """
        try:
            if entry.forward_to:
                return set(), None

            dns_results = dns_manage.DnsManage(
                bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id
            ).get_domain(domain_name=entry.entry)

            return {result["ip"] for result in dns_results}, None
        except Exception as e:
            error_msg = _("Failed to get DNS records: {}").format(str(e))
            self.log_exception(
                _("Failed to get DNS records for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set(), error_msg

    def _get_clb_ips(self, cluster: Cluster, entry: ClusterEntry) -> Tuple[Set[str], Optional[str]]:
        """
        Get IPs registered in CLB for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with CLB type

        Returns:
            Tuple of (Set of IP addresses in CLB (ports stripped), error message if any)
        """
        try:
            clb_detail = entry.detail
            # Use helper function to get CLBManage instance
            clb_manager = get_clb_by_ip(clb_detail["clb_ip"])

            # Use CLBManage to get registered IPs
            raw_ips = clb_manager.get_clb_rs()
            # CLB returns IPs with ports (e.g., "1.1.1.1:30000"), strip the port
            return {ip.split(":")[0] for ip in raw_ips}, None

        except Exception as e:
            error_msg = _("Failed to get CLB targets: {}").format(str(e))
            self.log_exception(
                _("Failed to get CLB targets for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set(), error_msg

    def _get_polaris_ips(self, cluster: Cluster, entry: ClusterEntry) -> Tuple[Set[str], Optional[str]]:
        """
        Get IPs registered in Polaris for a given entry

        Args:
            cluster: Cluster object
            entry: ClusterEntry object with POLARIS type

        Returns:
            Tuple of (Set of IP addresses in Polaris (ports stripped), error message if any)
        """
        try:
            polaris_detail = entry.detail
            # Use helper function to get PolarisManage instance
            polaris_manager = GetPolarisManageByName(polaris_detail["polaris_name"])

            # Use PolarisManage to get registered IPs
            raw_ips = polaris_manager.get_polaris_rs()
            # Polaris returns IPs with ports (e.g., "1.1.1.1:30000"), strip the port
            return {ip.split(":")[0] for ip in raw_ips}, None

        except Exception as e:
            error_msg = _("Failed to get Polaris targets: {}").format(str(e))
            self.log_exception(
                _("Failed to get Polaris targets for cluster {} entry {}: {}").format(
                    cluster.immute_domain, entry.entry, str(e)
                )
            )
            return set(), error_msg

    def _check_entry_consistency(
        self,
        cluster: Cluster,
        entry: ClusterEntry,
    ) -> Optional[Dict]:
        """
        Check if an entry has the exact same IPs as expected

        Args:
            cluster: Cluster object
            entry: ClusterEntry object

        Returns:
            Dict with error details if inconsistent, None if consistent
        """
        entry_type = entry.cluster_entry_type

        has_proxy = is_have_proxy(cluster.cluster_type)
        is_slave_entry = entry.entry.split(".")[0].endswith("-slave")
        is_nodes_entry = entry.entry.startswith("nodes.")

        # Logic:
        # - Non-proxy clusters: Check master/slave entries separately (xxx.domain vs xxx-slave.domain)
        # - Proxy clusters: Check proxy IPs for regular entries
        # - Cluster protocol: Check storage IPs for an extra nodes.* dns entry
        if is_nodes_entry:
            # Cluster protocol with nodes.* prefix: use all storage IPs (master + slave)
            expected_ips = RedisEntryCheckService._get_cluster_storage_ips(cluster)
        elif not has_proxy:
            # Non-proxy clusters: use master or slave IPs based on entry name
            if is_slave_entry:
                expected_ips = RedisEntryCheckService._get_cluster_slave_ips(cluster)
            else:
                expected_ips = RedisEntryCheckService._get_cluster_master_ips(cluster)
        else:
            # Proxy-based clusters: use proxy IPs for regular entries
            expected_ips = RedisEntryCheckService._get_cluster_proxy_ips(cluster)

        # Get actual IPs from the entry system
        actual_ips = set()
        fetch_error = None

        match entry_type:
            case ClusterEntryType.DNS.value:
                if entry.forward_to:
                    # DNS is forwarding to CLB ip, skip this condition
                    return None
                actual_ips, fetch_error = self._get_dns_ips(cluster, entry)
            case ClusterEntryType.CLB.value:
                actual_ips, fetch_error = self._get_clb_ips(cluster, entry)
            case ClusterEntryType.POLARIS.value:
                actual_ips, fetch_error = self._get_polaris_ips(cluster, entry)
            case ClusterEntryType.CLBDNS.value:
                # CLBDNS is just a pointer, skip checking
                return None
            case _:
                self.log_warning(
                    _("Unknown entry type {} for cluster {} entry {}").format(entry_type, cluster.immute_domain, entry)
                )
                return None

        # If there was an error fetching IPs, report it
        if fetch_error:
            error_detail = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.immute_domain,
                "entry_type": entry_type,
                "entry_name": entry.entry,
                "error": fetch_error,
            }
            return error_detail

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
    def _build_entry_report_row(cluster: Cluster, all_error_details: list) -> Dict:
        if not all_error_details:
            return {
                "cluster": cluster,
                "ip": None,
                "port": None,
                "subtype": MetaCheckSubType.EntryInconsistent,
                "msg": _("All entries are consistent."),
                "state": ReportStateType.NORMAL,
                "creator": "system",
            }

        description_parts = []
        for error_detail in all_error_details:
            entry_type = error_detail["entry_type"]
            entry_name = error_detail["entry_name"]

            if "error" in error_detail:
                description_parts.append(_("{}  ({}): {}").format(entry_type, entry_name, error_detail["error"]))
                continue

            missing_ips = error_detail.get("missing_ips", [])
            extra_ips = error_detail.get("extra_ips", [])

            entry_desc_parts = []
            if missing_ips:
                entry_desc_parts.append(_("missing: {}").format(", ".join(missing_ips)))
            if extra_ips:
                entry_desc_parts.append(_("extra: {}").format(", ".join(extra_ips)))

            if entry_desc_parts:
                description_parts.append(_("{}  ({}): {}").format(entry_type, entry_name, "; ".join(entry_desc_parts)))

        return {
            "cluster": cluster,
            "ip": None,
            "port": None,
            "subtype": MetaCheckSubType.EntryInconsistent,
            "msg": "; ".join(description_parts),
            "state": ReportStateType.ABNORMAL,
            "creator": "system",
        }

    def _check_single_cluster(self, cluster: Cluster) -> Dict:
        """
        Check entries for a single preloaded cluster (external I/O only; no ORM).
        """
        try:
            entries = list(cluster.clusterentry_set.all())
            checked_count = 0
            all_error_details = []

            for entry in entries:
                checked_count += 1
                error_detail = self._check_entry_consistency(cluster, entry)
                if error_detail:
                    all_error_details.append(error_detail)

            report_row = self._build_entry_report_row(cluster, all_error_details)
            inconsistent_count = len(all_error_details)
            if inconsistent_count:
                self.log_warning(
                    _("Entry inconsistencies detected for cluster {}: {}").format(
                        cluster.immute_domain, report_row["msg"]
                    )
                )

            return {
                "cluster_id": cluster.id,
                "checked": checked_count,
                "inconsistent": inconsistent_count,
                "report_row": report_row,
            }

        except Exception as e:
            self.log_exception(_("Failed to check entries for cluster id={}: {}").format(cluster.id, str(e)))
            return {"cluster_id": cluster.id, "checked": 0, "inconsistent": 0, "error": str(e)}

    def _pop_batch_from_redis(self, candidates_key: str, batch_size: int) -> List[int]:
        """
        Pop a batch of cluster_ids from Redis list using RPOP.

        Args:
            candidates_key: Redis key where candidates are stored as a list
            batch_size: Number of cluster_ids to pop

        Returns:
            List of cluster_ids (up to batch_size)
        """
        try:
            batch_cluster_ids = []
            for _i in range(batch_size):
                cluster_id = RedisConn.rpop(candidates_key)
                if cluster_id is None:
                    # No more items in the list
                    break
                # Convert bytes to int if necessary
                if isinstance(cluster_id, bytes):
                    cluster_id = int(cluster_id.decode())
                else:
                    cluster_id = int(cluster_id)
                batch_cluster_ids.append(cluster_id)

            return batch_cluster_ids

        except Exception as e:
            self.log_exception(_("Failed to pop batch from Redis: {}").format(e))
            return []

    @staticmethod
    def _requeue_batch_to_redis(candidates_key: str, batch_cluster_ids: List[int]) -> None:
        """Put popped cluster ids back on the Redis list tail so a failed write can be retried."""
        if not batch_cluster_ids:
            return
        # Candidates are LPUSHed then RPOPped; restore original order via reversed RPUSH.
        RedisConn.rpush(candidates_key, *reversed(batch_cluster_ids))

    def _execute(self, data, parent_data) -> bool:
        """
        Initialize the entry check process.
        Metadata will be loaded lazily in the first _schedule() call.

        Args:
            data: Component data
            parent_data: Parent pipeline data

        Returns:
            True if successful, False otherwise
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # Get candidates_key from kwargs
        candidates_key = kwargs.get("candidates_key", "")
        if not candidates_key:
            self.log_error("No candidates_key provided in kwargs")
            return False

        # Get batch configuration
        batch_size = kwargs.get("batch_size", DEFAULT_BATCH_SIZE)
        batch_interval = kwargs.get("batch_interval", DEFAULT_BATCH_INTERVAL)

        # Set the interval dynamically based on batch_interval parameter
        self.interval = StaticIntervalGenerator(batch_interval)

        # Get total count from Redis list length
        try:
            total_clusters = RedisConn.llen(candidates_key)
            if total_clusters == 0:
                self.log_warning("No cluster_ids found in Redis list, nothing to check")
                return False
        except Exception as e:
            self.log_exception(_("Failed to get list length from Redis: {}").format(e))
            return False

        total_batches = (total_clusters + batch_size - 1) // batch_size

        # Store configuration in outputs for persistence across scheduled iterations
        data.outputs["candidates_key"] = candidates_key
        data.outputs["batch_size"] = batch_size
        data.outputs["current_batch"] = 0
        data.outputs["total_checked"] = 0
        data.outputs["total_inconsistent"] = 0
        data.outputs["total_clusters"] = total_clusters
        data.outputs["total_batches"] = total_batches

        self.log_info(
            _("Initialized entry check with {} clusters in {} batches, " "batch_size={}, batch_interval={}s").format(
                total_clusters, total_batches, batch_size, batch_interval
            )
        )

        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        """
        Process one batch of clusters in each schedule iteration.

        Args:
            data: Component data
            parent_data: Parent pipeline data
            callback_data: Callback data (unused)

        Returns:
            True to continue scheduling, False on error
        """
        # Retrieve state from outputs (persisted across scheduled iterations)
        candidates_key = data.outputs["candidates_key"]
        batch_size = data.outputs["batch_size"]
        current_batch = data.outputs["current_batch"]
        total_checked = data.outputs["total_checked"]
        total_inconsistent = data.outputs["total_inconsistent"]
        total_batches = data.outputs["total_batches"]

        # Pop a batch of cluster_ids from Redis list
        batch_cluster_ids = self._pop_batch_from_redis(candidates_key, batch_size)
        batch_num = current_batch + 1

        if not batch_cluster_ids:
            # No more clusters to pop, we're done
            self.log_info("No more clusters to process, finishing")

            # Clean up the Redis key (should be empty now, but just in case)
            try:
                RedisConn.delete(candidates_key)
                self.log_info(_("Cleaned up Redis key: {}").format(candidates_key))
            except Exception as e:
                self.log_warning(_("Failed to cleanup Redis key {}: {}").format(candidates_key, e))

            self.finish_schedule()
            return True

        self.log_info(
            _("Processing batch {}/{}: popped {} clusters from Redis list").format(
                batch_num, total_batches, len(batch_cluster_ids)
            )
        )

        cluster_map = self._load_batch_clusters(batch_cluster_ids)
        writer = RedisReportWriter()
        batch_checked = 0
        batch_inconsistent = 0
        report_rows = []

        clusters_to_check = []
        for cluster_id in batch_cluster_ids:
            cluster = cluster_map.get(cluster_id)
            if cluster is None:
                self.log_warning(_("Cluster id={} not found, skipping").format(cluster_id))
                continue
            clusters_to_check.append(cluster)

        max_workers = min(15, len(clusters_to_check))
        if max_workers > 0:
            # Workers use preloaded cluster objects and external I/O only (no Django ORM / DB writes).
            # ORM prefetch and report writes stay on this thread to avoid connection leaks.
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_cluster = {
                    executor.submit(self._check_single_cluster, cluster): cluster.id for cluster in clusters_to_check
                }

                for future in as_completed(future_to_cluster):
                    cluster_id = future_to_cluster[future]
                    try:
                        result = future.result()
                        batch_checked += result.get("checked", 0)
                        batch_inconsistent += result.get("inconsistent", 0)
                        report_row = result.get("report_row")
                        if report_row:
                            report_rows.append(report_row)
                    except Exception as e:
                        self.log_exception(_("Exception checking cluster id={}: {}").format(cluster_id, e))

        write_ok = True
        if report_rows:
            write_ok = safe_write_meta_reports(
                writer,
                report_rows,
                context=f"entry_check batch={batch_num} key={candidates_key}",
            )
            if write_ok:
                ingest_abnormal_cluster_rows(
                    report_rows,
                    dimension=RedisPortraitDimensionCode.TOPOLOGY_SCALE,
                    prefix=_("[入口]"),
                )
            if not write_ok:
                try:
                    self._requeue_batch_to_redis(candidates_key, batch_cluster_ids)
                    self.log_warning(
                        _("Re-queued {} cluster ids after report write failure").format(len(batch_cluster_ids))
                    )
                except Exception as e:
                    self.log_exception(_("Failed to re-queue batch after write failure: {}").format(e))

        # Update totals in outputs
        total_checked += batch_checked
        total_inconsistent += batch_inconsistent
        data.outputs["total_checked"] = total_checked
        data.outputs["total_inconsistent"] = total_inconsistent

        self.log_info(
            _("Batch {}/{} completed: {} entries checked, {} inconsistencies found").format(
                batch_num, total_batches, batch_checked, batch_inconsistent
            )
        )

        if not write_ok:
            return True

        # Update state for next iteration
        current_batch += 1
        data.outputs["current_batch"] = current_batch

        # Check if all batches are processed (or if we got fewer items than expected)
        if current_batch >= total_batches or len(batch_cluster_ids) < batch_size:
            # If we got fewer items than batch_size, we've reached the end
            if len(batch_cluster_ids) < batch_size and current_batch < total_batches:
                self.log_info(
                    _("Reached end of list early (got {} items in final batch)").format(len(batch_cluster_ids))
                )

            self.log_info(
                _("All batches completed: {} total entries checked, {} total inconsistencies found").format(
                    total_checked, total_inconsistent
                )
            )

            # Clean up the Redis key after all processing is done
            try:
                RedisConn.delete(candidates_key)
                self.log_info(_("Cleaned up Redis key: {}").format(candidates_key))
            except Exception as e:
                self.log_warning(_("Failed to cleanup Redis key {}: {}").format(candidates_key, e))

            self.finish_schedule()
            return True

        # Continue to next batch
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [
            Service.OutputItem(name="total_checked", key="total_checked", type="int"),
            Service.OutputItem(name="total_inconsistent", key="total_inconsistent", type="int"),
        ]


class RedisEntryCheckComponent(Component):
    """
    Component for Redis entry consistency check
    """

    name = __name__
    code = "redis_entry_check"
    bound_service = RedisEntryCheckService
