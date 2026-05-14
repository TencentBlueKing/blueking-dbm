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
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone import ABNORMAL, NORMAL, WARNING
from backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone import (
    check_affinity_rules as shared_check_affinity_rules,
)
from backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone import err
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import ClusterReport, RecordBatchOps, addr, dev_debug
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mongodb_check_sub_type import MongodbAffinityCheckSubType
from backend.db_report.repo.task_record_repo import get_report_day_from_time
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")


def is_shardsvr_set(set_name: str) -> bool:
    return set_name not in {"mongos", "configsvr"}


def build_shardsvr_group_key(nodes: list[dict]) -> str:
    machine_keys = sorted({f"{node.get('bk_cloud_id', '')}:{node.get('ip', '')}" for node in nodes if node.get("ip")})
    return f"shardsvr_group:{'|'.join(machine_keys)}"


def dedup_nodes_by_machine(nodes: list[dict]) -> list[dict]:
    deduped = {}
    for node in nodes:
        key = f"{node.get('bk_cloud_id', '')}:{node.get('ip', '')}"
        if key not in deduped:
            deduped[key] = node
    return list(deduped.values())


class CheckMongodbAffinityTask:
    """检查 MongoDB 集群亲和性定义与实际拓扑是否一致"""

    check_type: str

    def __init__(self):
        self.check_type = MongodbAffinityCheckSubType.ClusterAffinity.value

    def start(self, report_day: int = None, batch_size: int = 20) -> tuple[int, int, int, int]:
        if report_day is None:
            report_day = get_report_day_from_time(timezone.now())
        record_batch_ops = RecordBatchOps(self.check_type, report_day)
        deleted_count = record_batch_ops.delete_old_record(360)
        logger.info(
            f"CheckMongodbAffinityTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )
        deleted_count = record_batch_ops.delete_today_record()
        logger.info(
            f"CheckMongodbAffinityTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )

        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=1)
        )
        cluster_id_list = [cluster.id for cluster in Cluster.objects.filter(query)]
        total_num = 0
        success_num = 0
        warning_num = 0
        abnormal_num = 0

        for index in range(0, len(cluster_id_list), batch_size):
            for cluster_id in cluster_id_list[index : index + batch_size]:
                cluster = MongoRepository.fetch_one_cluster(with_tags=True, id=cluster_id)
                rows = self.check_cluster(cluster, report_day)
                total_num += 1
                if rows:
                    if rows[0].state == ReportStateType.NORMAL.value:
                        success_num += 1
                    elif rows[0].state == ReportStateType.WARNING.value:
                        warning_num += 1
                    elif rows[0].state == ReportStateType.ABNORMAL.value:
                        abnormal_num += 1
                    for record in rows:
                        record_batch_ops.append(record)
            record_batch_ops.bulk_create()
        logger.info(
            f"CheckMongodbAffinityTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"total_num: {total_num}, success_num: {success_num}, warning_num: {warning_num}, abnormal_num: {abnormal_num}"
        )
        return total_num, success_num, warning_num, abnormal_num

    def is_skip_check(self, cluster: MongoDBCluster) -> tuple[bool, str]:
        tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
        temporary = tags.get("temporary", "")
        if temporary in ["true", "yes", "True", "Yes", "1"]:
            return True, f"skipped by temporary:{temporary}"
        return False, ""

    def check_cluster(self, cluster: MongoDBCluster, report_day: int):
        last_error = None
        for retry in range(3):
            try:
                records = self._do_check_cluster_inner(cluster, report_day)
                if records is not None:
                    return records
            except Exception as exc:
                logger.error(f"check_cluster error: {exc}, retry {retry + 1} times, sleep {retry * 3 + 1} seconds")
                last_error = exc
                time.sleep(retry * 3 + 1)
        cluster_report = ClusterReport(cluster, report_day, self.check_type)
        return cluster_report.make_error_record(f"system error after 3 times retry: {last_error}")

    def _do_check_cluster_inner(self, cluster: MongoDBCluster, report_day: int):
        cluster_report = ClusterReport(cluster, report_day, self.check_type)
        skipped, reason = self.is_skip_check(cluster)
        if skipped:
            dev_debug(f"=== check_one {cluster.cluster_id} {cluster.immute_domain} {reason} === ")
            return cluster_report.make_skip_record(reason)

        nodes = get_all_nodes(cluster)
        if not nodes:
            cluster_report.append(ReportStateType.ABNORMAL.value, "all", "all", "no node")
            return cluster_report.make_records()

        cluster_def = (
            Cluster.objects.filter(id=cluster.cluster_id)
            .values("disaster_tolerance_level", "zone_list", "region")
            .first()
            or {}
        )
        disaster_tolerance_level = cluster_def.get("disaster_tolerance_level", "") or ""
        zone_list = normalize_to_str_set(cluster_def.get("zone_list") or [])
        cluster_region = str(cluster_def.get("region", "") or "")

        topology_result = collect_topology_by_set(nodes, is_sharded_cluster=cluster.is_sharded_cluster())
        skip_member_count_check = self.ignore_member_count_check(cluster)
        for set_name, result in topology_result.items():
            for missing_msg in result["missing_messages"]:
                cluster_report.append(
                    ReportStateType.ABNORMAL.value, set_name, missing_msg["instance"], missing_msg["msg"]
                )
            if result["missing_messages"]:
                continue

            if not skip_member_count_check:
                min_members = 2 if set_name == "mongos" else 3
                actual_members = len(result["nodes"])
                if actual_members < min_members:
                    cluster_report.append(
                        ReportStateType.ABNORMAL.value,
                        set_name,
                        result["set_sample"],
                        err(
                            "member_count_violation",
                            f"{set_name} requires at least {min_members} members, actual={actual_members}",
                        ),
                    )
                    continue

            check_result = self.check_affinity_rules(
                disaster_tolerance_level=disaster_tolerance_level,
                zone_list=zone_list,
                actual_sub_zone_set=result["sub_zone_set"],
                actual_region_set=result["region_set"],
                actual_rack_set=result["rack_set"],
                component_nodes=result["nodes"],
                cluster_region=cluster_region,
                # same as single_node tag: skip min sub_zone counts for CROS_SUBZONE /
                # CROSS_SUBZONE_STRONG / CROSS_SUBZONE_WEAK / MAJORITY_ELECTION_DISTRI
                has_single_node_tag=skip_member_count_check,
            )

            if check_result["msg"]:
                cluster_report.append(check_result["state"], set_name, result["set_sample"], check_result["msg"])
            else:
                cluster_report.append(ReportStateType.NORMAL.value, set_name, result["set_sample"], "ok")

        return cluster_report.make_records()

    def ignore_member_count_check(self, cluster: MongoDBCluster) -> bool:
        tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
        single_node = str(tags.get("single_node", "")).lower()
        return single_node == "true"

    def check_affinity_rules(  # noqa: C901
        self,
        disaster_tolerance_level: str,
        zone_list: set[str],
        actual_sub_zone_set: set[str],
        actual_rack_set: set[str],
        component_nodes: list[dict],
        actual_region_set: set[str] | None = None,
        cluster_region: str = "",
        has_single_node_tag: bool = False,
    ) -> dict:
        """Delegate to ``check_affinity_standalone.check_affinity_rules``.

        When ``has_single_node_tag`` is True, the shared rules skip minimum sub_zone count
        checks for ``CROS_SUBZONE``, ``CROSS_SUBZONE_STRONG``, ``CROSS_SUBZONE_WEAK``, and
        ``MAJORITY_ELECTION_DISTRI`` (see that function's docstring).
        """
        state, reasons = shared_check_affinity_rules(
            disaster_tolerance_level=disaster_tolerance_level,
            cluster_region=cluster_region,
            zone_list=zone_list,
            actual_sub_zone_set=actual_sub_zone_set,
            actual_region_set=actual_region_set or set(),
            actual_rack_set=actual_rack_set,
            component_nodes=component_nodes,
            has_single_node_tag=has_single_node_tag,
        )
        state_map = {
            NORMAL: ReportStateType.NORMAL.value,
            WARNING: ReportStateType.WARNING.value,
            ABNORMAL: ReportStateType.ABNORMAL.value,
        }
        return {"state": state_map.get(state, state), "msg": "; ".join(reasons)}


def get_all_nodes(cluster: MongoDBCluster) -> list:
    nodes = []
    for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
        for node in shard.members:
            node.__setattr__("set_name", shard.set_name)
            nodes.append(node)

    if cluster.is_sharded_cluster():
        for node in cluster.get_mongos():
            node.__setattr__("set_name", "mongos")
            nodes.append(node)
    return nodes


def normalize_to_str_set(values) -> set[str]:
    return {str(value) for value in values if value not in [None, ""]}


def collect_topology_by_set(nodes: list, is_sharded_cluster: bool = False) -> dict:
    topology_by_set = {}
    ip_list = list({node.ip for node in nodes})
    cloud_set = {node.bk_cloud_id for node in nodes}
    machine_map = {}
    for cloud_id in cloud_set:
        machine_rows = Machine.objects.filter(ip__in=ip_list, bk_cloud_id=cloud_id).values(
            "ip",
            "bk_sub_zone_id",
            "bk_rack_id",
            "bk_cloud_id",
            "bk_city__logical_city__name",
        )
        for row in machine_rows:
            machine_map[(row["ip"], row["bk_cloud_id"])] = row

    for node in nodes:
        set_name = node.set_name or "unknown"
        topology_by_set.setdefault(
            set_name,
            {
                "sub_zone_set": set(),
                "region_set": set(),
                "rack_set": set(),
                "set_sample": "",
                "missing_messages": [],
                "nodes": [],
            },
        )
        if not topology_by_set[set_name]["set_sample"]:
            topology_by_set[set_name]["set_sample"] = addr(node)
        machine = machine_map.get((node.ip, node.bk_cloud_id))
        if machine is None:
            topology_by_set[set_name]["missing_messages"].append(
                {"instance": addr(node), "msg": "machine not found in db_meta"}
            )
            continue
        if not machine.get("bk_sub_zone_id"):
            topology_by_set[set_name]["missing_messages"].append(
                {"instance": addr(node), "msg": "bk_sub_zone_id is empty"}
            )
            continue
        if not machine.get("bk_rack_id"):
            topology_by_set[set_name]["missing_messages"].append(
                {"instance": addr(node), "msg": "bk_rack_id is empty"}
            )
            continue
        sub_zone = str(machine.get("bk_sub_zone_id"))
        rack = str(machine.get("bk_rack_id"))
        region = str(machine.get("bk_city__logical_city__name") or "").strip()
        if not region:
            topology_by_set[set_name]["missing_messages"].append(
                {"instance": addr(node), "msg": "logical_city name is empty for machine bk_city"}
            )
            continue
        topology_by_set[set_name]["sub_zone_set"].add(sub_zone)
        topology_by_set[set_name]["region_set"].add(region)
        topology_by_set[set_name]["rack_set"].add(rack)
        topology_by_set[set_name]["nodes"].append(
            {
                "ip": node.ip,
                "bk_cloud_id": node.bk_cloud_id,
                "actual_sub_zone": sub_zone,
                "actual_rack": rack,
                "instance_role": str(getattr(node, "instance_role", "") or ""),
            }
        )

    if not is_sharded_cluster:
        return topology_by_set

    grouped_topology = {}
    for set_name, result in topology_by_set.items():
        if not is_shardsvr_set(set_name):
            grouped_topology[set_name] = result
            continue
        group_key = build_shardsvr_group_key(result["nodes"])
        grouped_topology.setdefault(
            group_key,
            {
                "sub_zone_set": set(),
                "region_set": set(),
                "rack_set": set(),
                "set_sample": "",
                "missing_messages": [],
                "nodes": [],
            },
        )
        grouped_topology[group_key]["sub_zone_set"].update(result["sub_zone_set"])
        grouped_topology[group_key]["region_set"].update(result["region_set"])
        grouped_topology[group_key]["rack_set"].update(result["rack_set"])
        grouped_topology[group_key]["missing_messages"].extend(result["missing_messages"])
        grouped_topology[group_key]["nodes"].extend(result["nodes"])
        grouped_topology[group_key]["nodes"] = dedup_nodes_by_machine(grouped_topology[group_key]["nodes"])
        if not grouped_topology[group_key]["set_sample"]:
            grouped_topology[group_key]["set_sample"] = result["set_sample"]

    return grouped_topology
