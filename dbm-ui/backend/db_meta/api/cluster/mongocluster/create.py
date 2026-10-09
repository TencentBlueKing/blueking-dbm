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
import traceback
from typing import Dict, List, Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api import machine as machine_api
from backend.db_meta.api import storage_instance as storage_instance_api
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.nosqlcomm.create_instances import create_proxies
from backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper import (
    ProgressCallback,
    StageTimer,
    emit_progress,
    ensure_storage_tuples,
    find_reusable_cluster,
    get_proxy_objs,
    get_storage_objs,
    partition_proxy_inputs,
    partition_shard_pairs,
    proxy_instance_keys,
    storage_instance_keys,
)
from backend.db_meta.api.cluster.nosqlcomm.precheck import before_create_domain_precheck
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator
from backend.flow.utils.mongodb.version_utils import apply_mongodb_metadata_versions_to_cluster

logger = logging.getLogger("flow")


def _flatten_nodes(pairs: List[dict]) -> List[dict]:
    nodes = []
    for pair in pairs:
        nodes.extend(pair["nodes"])
    return nodes


def _create_missing_shard_instances(
    bk_biz_id: int,
    bk_cloud_id: int,
    machine_type: str,
    inst_pairs: List[dict],
    machine_specs: dict,
    progress_callback: ProgressCallback,
    stage_name: str,
    allowed_cluster_id: Optional[int] = None,
    cluster_name: str = "",
):
    """只创建缺失节点，并补齐复制关系；已属于本次集群，或未绑定且 name 为本次集群名的节点复用。"""
    all_nodes = _flatten_nodes(inst_pairs)
    timer = StageTimer(progress_callback, stage_name, count=len(all_nodes))
    missing_pairs, reusable, conflicts = partition_shard_pairs(
        inst_pairs, bk_cloud_id, allowed_cluster_id=allowed_cluster_id, cluster_name=cluster_name
    )
    if conflicts:
        raise Exception("; ".join(conflicts))

    missing_nodes = []
    for pair in missing_pairs:
        missing_nodes.extend(pair["nodes"])
    created_count = len(missing_nodes)
    skipped_count = len(reusable)

    if missing_nodes:
        spec_id = machine_specs.get(machine_type, {}).get("spec_id", 0)
        spec_config = machine_specs.get(machine_type, {}).get("spec_config", {})
        machines = {}
        instances = []
        for node in missing_nodes:
            if not Machine.objects.filter(ip=node["ip"], bk_cloud_id=bk_cloud_id).exists():
                machines[node["ip"]] = {
                    "ip": node["ip"],
                    "bk_biz_id": bk_biz_id,
                    "bk_cloud_id": bk_cloud_id,
                    "machine_type": machine_type,
                    "spec_id": spec_id,
                    "spec_config": spec_config,
                }
            instances.append(
                {"ip": node["ip"], "port": node["port"], "instance_role": node["role"], "name": cluster_name}
            )
        if machines:
            machine_api.create(machines=list(machines.values()), bk_cloud_id=bk_cloud_id)
        storage_instance_api.create(instances=instances)

    for pair in inst_pairs:
        ensure_storage_tuples(pair["nodes"], bk_cloud_id=bk_cloud_id)

    timer.done(skipped=skipped_count, created=created_count)


def _bind_cluster_instances(cluster: Cluster, mongos_objs, config_objs, storage_objs, cluster_type: str):
    cluster.proxyinstance_set.add(*mongos_objs)
    cluster.storageinstance_set.add(*config_objs)
    cluster.storageinstance_set.add(*storage_objs)
    cluster.save()
    update_cluster_type(mongos_objs, cluster_type)
    update_cluster_type(config_objs, cluster_type)
    update_cluster_type(storage_objs, cluster_type)


def _ensure_shard_rules(
    cluster: Cluster,
    primaries: List[dict],
    mongos_objs,
    bk_biz_id: int,
    bk_cloud_id: int,
    creator: str,
):
    for primary in primaries:
        primary_obj = StorageInstance.objects.get(
            machine__ip=primary["ip"], port=primary["port"], machine__bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id
        )
        if not cluster.nosqlstoragesetdtl_set.filter(instance=primary_obj, seg_range=primary["shard"]).exists():
            cluster.nosqlstoragesetdtl_set.create(
                instance=primary_obj,
                bk_biz_id=bk_biz_id,
                seg_range=primary["shard"],
                creator=creator,
            )
        primary_obj.proxyinstance_set.add(*mongos_objs)


def _ensure_dns_entry(cluster: Cluster, immute_domain: str, mongos_objs, creator: str):
    cluster_entry = ClusterEntry.objects.filter(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain
    ).first()
    if not cluster_entry:
        # Domain may exist on another cluster
        other = ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain).first()
        if other and other.cluster_id != cluster.id:
            raise Exception("dns entry already exists {}".format(immute_domain))
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
        )
    cluster_entry.proxyinstance_set.add(*mongos_objs)
    return cluster_entry


def create_mongo_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    proxies: Optional[List] = None,
    configs: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.MongoShardedCluster.value,
    disaster_tolerance_level: str = "",
    zone_list: list = None,
    progress_callback: ProgressCallback = None,
):
    """
    创建分片集群 Meta，并同步 CMDB。
    集群关系提交时 phase=offline；CMDB 成功后改为 online。
    CMDB 不在数据库事务内，失败后可重跑补齐。
    """
    proxies = proxies or []
    configs = configs or []
    storages = storages or []

    all_storages, all_confies, primaries = [], [], []
    for storage in storages:
        all_storages.extend(storage["nodes"])
        for shard in storage["nodes"]:
            if shard["role"] == InstanceRole.MONGO_M1:
                primaries.append({"ip": shard["ip"], "port": shard["port"], "shard": storage["shard"]})
    for config in configs:
        all_confies.extend(config["nodes"])
        for shard in config["nodes"]:
            if shard["role"] == InstanceRole.MONGO_M1:
                primaries.append({"ip": shard["ip"], "port": shard["port"], "shard": config["shard"]})

    expected_storage_keys = storage_instance_keys(all_storages + all_confies, bk_cloud_id)
    expected_proxy_keys = proxy_instance_keys(proxies, bk_cloud_id)

    timer = StageTimer(progress_callback, "create cluster relations")
    with transaction.atomic():
        cluster = find_reusable_cluster(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            cluster_type=cluster_type,
            expected_storage_keys=expected_storage_keys,
            expected_proxy_keys=expected_proxy_keys,
        )
        mongos_objs = get_proxy_objs(proxies, bk_cloud_id)
        storage_objs = get_storage_objs(all_storages, bk_cloud_id)
        config_objs = get_storage_objs(all_confies, bk_cloud_id)

        if cluster is None:
            # Domain uniqueness for brand-new cluster
            before_create_domain_precheck([immute_domain])
            cluster = Cluster.objects.create(
                bk_biz_id=bk_biz_id,
                name=name,
                alias=alias,
                major_version=major_version,
                db_module_id=db_module_id,
                immute_domain=immute_domain,
                creator=creator,
                phase=ClusterPhase.OFFLINE.value,
                status=ClusterStatus.NORMAL.value,
                updater=creator,
                cluster_type=cluster_type,
                bk_cloud_id=bk_cloud_id,
                region=region,
                disaster_tolerance_level=disaster_tolerance_level,
                zone_list=zone_list,
            )
            emit_progress(progress_callback, f"created cluster id={cluster.id}, phase=offline")
        else:
            emit_progress(
                progress_callback,
                f"reuse existing cluster id={cluster.id}, phase={cluster.phase}",
            )
            if cluster.phase != ClusterPhase.OFFLINE.value:
                raise Exception("Cluster {} exists with unsupported phase {}".format(name, cluster.phase))

        _bind_cluster_instances(cluster, mongos_objs, config_objs, storage_objs, cluster_type)
        _ensure_shard_rules(cluster, primaries, mongos_objs, bk_biz_id, bk_cloud_id, creator)
        _ensure_dns_entry(cluster, immute_domain, mongos_objs, creator)

    timer.done()

    # CMDB outside DB transaction
    timer = StageTimer(
        progress_callback,
        "sync CMDB module/hosts/service instances",
        count=len(mongos_objs) + len(config_objs) + len(storage_objs),
    )
    try:
        cc_topo_operator = MongoDBCCTopoOperator(cluster)
        emit_progress(progress_callback, f"transfer mongos to cluster module, count={len(mongos_objs)}")
        cc_topo_operator.transfer_instances_to_cluster_module(mongos_objs)
        emit_progress(progress_callback, f"transfer config to cluster module, count={len(config_objs)}")
        cc_topo_operator.transfer_instances_to_cluster_module(config_objs)
        emit_progress(progress_callback, f"transfer shards to cluster module, count={len(storage_objs)}")
        cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongocluster sync CMDB failed {}".format(e))
    timer.done()

    if major_version:
        timer = StageTimer(progress_callback, "apply mongodb metadata versions")
        apply_mongodb_metadata_versions_to_cluster(cluster, major_version)
        timer.done()

    if cluster.phase != ClusterPhase.ONLINE.value:
        cluster.phase = ClusterPhase.ONLINE.value
        cluster.save(update_fields=["phase"])
        emit_progress(progress_callback, f"cluster id={cluster.id} phase set to online")

    return cluster


def pkg_create_mongo_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    proxies: Optional[List] = None,
    configs: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    machine_specs: Optional[Dict] = None,
    cluster_type=ClusterType.MongoShardedCluster.value,
    disaster_tolerance_level: str = "",
    zone_list: list = None,
    progress_callback: ProgressCallback = None,
):
    """
    打包创建分片集群 Meta。
    分阶段提交：实例 -> 集群关系(offline) -> CMDB -> phase=online。
    重跑时跳过已完成产出；冲突数据仍失败。
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_storage_list(proxies, allow_empty=False, allow_null=False)
    configs = configs or []
    storages = storages or []
    machine_specs = machine_specs or {}

    all_instances = []
    for storage in storages:
        all_instances.extend(storage["nodes"])
    for config in configs:
        all_instances.extend(config["nodes"])
    request_validator.validated_storage_list(all_instances, allow_empty=False, allow_null=False)

    timer = StageTimer(progress_callback, "validate inputs and check conflicts")
    # Soft conflict checks: allow reusable unbound instances/domains for this cluster.
    existing_cluster = find_reusable_cluster(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        cluster_type=cluster_type,
        expected_storage_keys=storage_instance_keys(all_instances, bk_cloud_id),
        expected_proxy_keys=proxy_instance_keys(proxies, bk_cloud_id),
    )
    allowed_cluster_id = existing_cluster.id if existing_cluster else None
    if existing_cluster is None:
        # Brand-new: domain must not exist
        domain_entry = ClusterEntry.objects.filter(
            cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain
        ).first()
        if domain_entry:
            raise Exception("dns entry already exists {}".format(immute_domain))
    timer.done()

    # Stage 1: machines / instances / tuples
    with transaction.atomic():
        timer = StageTimer(progress_callback, "create mongos machines/instances", count=len(proxies))
        missing_proxies, reusable_proxies, proxy_conflicts = partition_proxy_inputs(
            proxies, bk_cloud_id, allowed_cluster_id=allowed_cluster_id, cluster_name=name
        )
        if proxy_conflicts:
            raise Exception("; ".join(proxy_conflicts))
        if missing_proxies:
            spec_id, spec_config = 0, {}
            if machine_specs.get(MachineType.MONGOS.value):
                spec_id = machine_specs[MachineType.MONGOS.value]["spec_id"]
                spec_config = machine_specs[MachineType.MONGOS.value]["spec_config"]
            create_proxies(bk_biz_id, bk_cloud_id, MachineType.MONGOS.value, missing_proxies, spec_id, spec_config)
            for proxy in missing_proxies:
                ProxyInstance.objects.filter(
                    machine__ip=proxy["ip"], port=proxy["port"], machine__bk_cloud_id=bk_cloud_id
                ).update(name=name)
        timer.done(skipped=len(reusable_proxies), created=len(missing_proxies))

        _create_missing_shard_instances(
            bk_biz_id=bk_biz_id,
            bk_cloud_id=bk_cloud_id,
            machine_type=MachineType.MONOG_CONFIG.value,
            inst_pairs=configs,
            machine_specs=machine_specs,
            progress_callback=progress_callback,
            stage_name="create config machines/instances/tuples",
            allowed_cluster_id=allowed_cluster_id,
            cluster_name=name,
        )
        _create_missing_shard_instances(
            bk_biz_id=bk_biz_id,
            bk_cloud_id=bk_cloud_id,
            machine_type=MachineType.MONGODB.value,
            inst_pairs=storages,
            machine_specs=machine_specs,
            progress_callback=progress_callback,
            stage_name="create shard machines/instances/tuples",
            allowed_cluster_id=allowed_cluster_id,
            cluster_name=name,
        )

    # Stage 2+3: cluster relations + CMDB
    create_mongo_cluster(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        proxies=proxies,
        configs=configs,
        storages=storages,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        region=region,
        cluster_type=cluster_type,
        disaster_tolerance_level=disaster_tolerance_level,
        zone_list=zone_list,
        progress_callback=progress_callback,
    )
