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
from typing import List, Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api import machine as machine_api
from backend.db_meta.api import storage_instance as storage_instance_api
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper import (
    ProgressCallback,
    StageTimer,
    emit_progress,
    ensure_storage_tuples,
    find_reusable_cluster,
    get_storage_objs,
    partition_storage_inputs,
    storage_instance_keys,
)
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, StorageInstance
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator
from backend.flow.utils.mongodb.version_utils import apply_mongodb_metadata_versions_to_cluster

logger = logging.getLogger("flow")


def _ensure_replicaset_dns_entries(cluster: Cluster, storages: List[dict], bk_cloud_id: int, creator: str):
    for storage in storages:
        entry = ClusterEntry.objects.filter(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=storage["domain"]
        ).first()
        if not entry:
            other = ClusterEntry.objects.filter(
                cluster_entry_type=ClusterEntryType.DNS, entry=storage["domain"]
            ).first()
            if other and other.cluster_id != cluster.id:
                raise Exception("dns entry already exists {}".format(storage["domain"]))
            entry = ClusterEntry.objects.create(
                cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=storage["domain"], creator=creator
            )
        storage_obj = StorageInstance.objects.get(
            machine__ip=storage["ip"],
            port=storage["port"],
            machine__bk_cloud_id=bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
        )
        entry.storageinstance_set.add(storage_obj)
        entry.save()


def create_mongoset(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.MongoReplicaSet.value,
    disaster_tolerance_level: str = "",
    zone_list: list = None,
    progress_callback: ProgressCallback = None,
):
    """
    创建副本集 Meta，并同步 CMDB。
    集群关系提交时 phase=offline；CMDB 成功后改为 online。
    """
    storages = storages or []
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    for storage in storages:
        domain = request_validator.validated_domain(storage["domain"])
        if storage["role"] == InstanceRole.MONGO_M1:
            if domain != immute_domain:
                raise Exception("input domain not match {} <> {}:{}".format(immute_domain, storage["ip"], domain))

    expected_storage_keys = storage_instance_keys(storages, bk_cloud_id)

    timer = StageTimer(progress_callback, "create cluster relations", count=len(storages))
    with transaction.atomic():
        cluster = find_reusable_cluster(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            cluster_type=cluster_type,
            expected_storage_keys=expected_storage_keys,
        )
        storage_objs = get_storage_objs(storages, bk_cloud_id)

        if cluster is None:
            for storage in storages:
                if ClusterEntry.objects.filter(
                    cluster_entry_type=ClusterEntryType.DNS, entry=storage["domain"]
                ).exists():
                    raise Exception("dns entry already exists {}".format(storage["domain"]))
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

        cluster.storageinstance_set.add(*storage_objs)
        cluster.save()
        update_cluster_type(storage_objs, cluster_type)
        _ensure_replicaset_dns_entries(cluster, storages, bk_cloud_id, creator)
    timer.done()

    timer = StageTimer(progress_callback, "sync CMDB module/hosts/service instances", count=len(storage_objs))
    try:
        MongoDBCCTopoOperator(cluster).transfer_replicaset_deploy_instances_to_cluster_module(storage_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongoset sync CMDB failed {}".format(e))
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


def pkg_create_mongoset(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    spec_id: int = 0,
    spec_config: str = "",
    cluster_type=ClusterType.MongoReplicaSet.value,
    skip_machine: bool = False,
    disaster_tolerance_level: str = "",
    zone_list: list = None,
    progress_callback: ProgressCallback = None,
):
    """
    打包创建 Mongo 副本集 Meta。
    分阶段提交：实例 -> 集群关系(offline) -> CMDB -> phase=online。
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    domains = []
    for storage in storages:
        domain = request_validator.validated_domain(storage["domain"])
        domains.append(domain)
        if storage["role"] == InstanceRole.MONGO_M1:
            if domain != immute_domain:
                raise Exception("input domain not match {} <> {}:{}".format(immute_domain, storage["ip"], domain))

    timer = StageTimer(progress_callback, "validate inputs and check conflicts", count=len(storages))
    existing_cluster = find_reusable_cluster(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        cluster_type=cluster_type,
        expected_storage_keys=storage_instance_keys(storages, bk_cloud_id),
    )
    allowed_cluster_id = existing_cluster.id if existing_cluster else None
    timer.done()

    with transaction.atomic():
        timer = StageTimer(progress_callback, "create machines/instances/tuples", count=len(storages))
        missing, reusable, conflicts = partition_storage_inputs(
            storages, bk_cloud_id, allowed_cluster_id=allowed_cluster_id, cluster_name=name
        )
        if conflicts:
            raise Exception("; ".join(conflicts))

        if missing:
            machines = {}
            instances = []
            for storage in missing:
                if (not skip_machine) and (
                    not Machine.objects.filter(ip=storage["ip"], bk_cloud_id=bk_cloud_id).exists()
                ):
                    machines[storage["ip"]] = {
                        "ip": storage["ip"],
                        "bk_biz_id": bk_biz_id,
                        "bk_cloud_id": bk_cloud_id,
                        "machine_type": MachineType.MONGODB.value,
                        "spec_id": spec_id,
                        "spec_config": spec_config,
                    }
                instances.append(
                    {
                        "ip": storage["ip"],
                        "port": storage["port"],
                        "instance_role": storage["role"],
                        "name": name,
                    }
                )
            if machines:
                machine_api.create(machines=list(machines.values()), bk_cloud_id=bk_cloud_id)
            storage_instance_api.create(instances=instances)

        ensure_storage_tuples(storages, bk_cloud_id=bk_cloud_id)
        timer.done(skipped=len(reusable), created=len(missing))

    create_mongoset(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        storages=storages,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        region=region,
        cluster_type=cluster_type,
        disaster_tolerance_level=disaster_tolerance_level,
        zone_list=zone_list,
        progress_callback=progress_callback,
    )
