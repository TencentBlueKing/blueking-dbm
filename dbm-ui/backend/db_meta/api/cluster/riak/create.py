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
from typing import List, Optional

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, ClusterMonitorTopo, StorageInstance
from backend.flow.consts import InstanceFuncAliasEnum
from backend.flow.utils.riak.riak_module_operate import (
    create_bk_module_for_cluster_id,
    init_instance_service,
    transfer_host_in_cluster_module,
)

logger = logging.getLogger("root")


@transaction.atomic
def create_precheck(bk_biz_id: int, name: str, immute_domain: str):
    precheck_errors = []

    if Cluster.objects.filter(bk_biz_id=bk_biz_id, name=name, cluster_type=ClusterType.Riak.value).exists():
        precheck_errors.append(_("集群名 {} 在 bk_biz_id:{} 已存在").format(name, bk_biz_id))

    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immute_domain).exists():
        precheck_errors.append(_("域名 {} 已存在").format(immute_domain))

    if precheck_errors:
        raise DBMetaException(message=", ".join(precheck_errors))


@transaction.atomic
def create(
    bk_cloud_id: int,
    bk_biz_id: int,
    name: str,
    alias: str,
    immute_domain: str,
    major_version: str,
    db_module_id: int,
    storages: Optional[List],
    creator: str = "",
):
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    cluster = Cluster.objects.create(
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        name=name,
        alias=alias,
        cluster_type=ClusterType.Riak.value,
        db_module_id=db_module_id,
        immute_domain=immute_domain,
        creator=creator,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        major_version=major_version,
    )

    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)

    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
    )
    cluster_entry.storageinstance_set.add(*storage_objs)

    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    # 生成CC 域名模块
    create_bk_module_for_cluster_id(cluster_id=cluster.id)

    # 主机转移模块、添加对应的服务实例
    machine_type = MachineType.RIAK.value
    ip_set = set([ins.machine.ip for ins in storage_objs.filter(machine__machine_type=machine_type)])
    transfer_host_in_cluster_module(
        cluster_id=cluster.id,
        ip_list=list(ip_set),
        machine_type=machine_type,
        bk_cloud_id=cluster.bk_cloud_id,
    )
    bk_module_id = ClusterMonitorTopo.objects.get(
        bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id, machine_type=machine_type
    ).bk_module_id
    for ins in storage_objs.filter(machine__machine_type=machine_type):
        init_instance_service(
            cluster=cluster,
            ins=ins,
            bk_module_id=bk_module_id,
            instance_role=ins.instance_role,
            func_name=InstanceFuncAliasEnum.RIAK_FUNC_ALIAS.value,
        )

    return cluster.id
