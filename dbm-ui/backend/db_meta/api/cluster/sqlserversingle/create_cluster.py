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
from typing import Dict

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.utils.sqlserver.sqlserver_db_function import get_instance_time_zone

logger = logging.getLogger("root")


@transaction.atomic
def create_pre_check(bk_biz_id: int, name: str, immute_domain: str, db_module_id: int):
    pre_check_errors = []

    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, name=name, cluster_type=ClusterType.SqlserverSingle.value, db_module_id=db_module_id
    ).exists():
        pre_check_errors.append(_("集群名 {} 在 bk_biz_id:{} db_module_id:{} 已存在").format(name, bk_biz_id, db_module_id))

    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immute_domain).exists():
        pre_check_errors.append(_("域名 {} 已存在").format(immute_domain))

    if pre_check_errors:
        raise DBMetaException(message=", ".join(pre_check_errors))


@transaction.atomic
def create(
    bk_biz_id: int,
    major_version: str,
    name: str,
    immute_domain: str,
    db_module_id: int,
    storage: Dict,
    bk_cloud_id: int,
    region: str,
    creator: str = "",
) -> Cluster:
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    storage = request_validator.validated_storage(storage)

    storage_objs = common.filter_out_instance_obj([storage], StorageInstance.objects.all())

    cluster = Cluster.objects.create(
        bk_biz_id=bk_biz_id,
        name=name,
        cluster_type=ClusterType.SqlserverSingle.value,
        db_module_id=db_module_id,
        immute_domain=immute_domain,
        creator=creator,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        bk_cloud_id=bk_cloud_id,
        time_zone=get_instance_time_zone(storage_objs[0]),
        major_version=major_version,
        region=region,
    )
    cluster.storageinstance_set.add(*storage_objs)

    ce = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
    )
    ce.storageinstance_set.add(*storage_objs)

    # 其实就一台
    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        # 保存最新的time_zone
        ins.time_zone = get_instance_time_zone(ins)
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])
    return cluster
