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
import ipaddress
import logging
from typing import Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import App, BKCity, Cluster, ClusterEntry, DBModule, LogicalCity, Machine, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def fake_create_tendbsingle(
    storage_instance: str,
    immute_domain: str,
    name: Optional[str] = None,
    bk_biz_id: Optional[int] = None,
    db_module_id: Optional[int] = None,
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
):
    if bk_biz_id and not App.objects.filter(bk_biz_id=bk_biz_id).exists():
        App.objects.create(bk_biz_id=1, bk_set_id=1)

    if bk_biz_id:
        if not App.objects.filter(bk_biz_id=bk_biz_id).exists():
            app = App.objects.create(bk_biz_id=bk_biz_id)
        else:
            app = App.objects.get(bk_biz_id=bk_biz_id)
    else:
        if not App.objects.exists():
            app = App.objects.create(bk_biz_id=1)
        else:
            app = App.objects.first()

    if db_module_id:
        if not DBModule.objects.filter(db_module_id=db_module_id).exists():
            db_module = DBModule.objects.create(
                bk_biz_id=app.bk_biz_id,
                db_module_name="fake_dbmodule_app_{}".format(app.bk_biz_id),
                db_module_id=db_module_id,
                cluster_type=ClusterType.TenDBSingle,
            )
        else:
            db_module = DBModule.objects.get(db_module_id=db_module_id)
    else:
        if not DBModule.objects.exists():
            db_module = DBModule.objects.create(
                bk_biz_id=app.bk_biz_id,
                db_module_name="fake_dbmodule_app_{}".format(app.bk_biz_id),
                cluster_type=ClusterType.TenDBSingle,
            )
        else:
            db_module = DBModule.objects.first()

    if not LogicalCity.objects.exists():
        LogicalCity.objects.create(name="阿希佳德")

    lc = LogicalCity.objects.first()

    if not BKCity.objects.exists():
        BKCity.objects.create(bk_idc_city_id=1, bk_idc_city_name=lc.name, logical_city=lc)

    bk_city = BKCity.objects.first()

    [ip, port] = storage_instance.split(":")
    m = Machine.objects.create(
        ip=ip,
        bk_biz_id=app.bk_biz_id,
        db_module_id=db_module.db_module_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.SINGLE,
        cluster_type=ClusterType.TenDBSingle,
        bk_city=bk_city,
        bk_host_id=int(ipaddress.IPv4Address(ip)),
    )

    ins_obj = StorageInstance.objects.create(
        machine=m,
        port=int(port),
        db_module_id=db_module.db_module_id,
        bk_biz_id=app.bk_biz_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.SINGLE,
        instance_role=InstanceRole.ORPHAN,
        instance_inner_role=InstanceInnerRole.ORPHAN,
        cluster_type=ClusterType.TenDBSingle,
        status=InstanceStatus.RUNNING,
    )

    if name:
        cluster_name = name
    else:
        cluster_name = immute_domain
    cluster = Cluster.objects.create(
        bk_biz_id=app.bk_biz_id,
        name=cluster_name,
        cluster_type=ClusterType.TenDBSingle,
        db_module_id=db_module.db_module_id,
        immute_domain=immute_domain,
        bk_cloud_id=bk_cloud_id,
    )
    cluster.storageinstance_set.add(ins_obj)

    ce = ClusterEntry.objects.create(cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain)
    ce.storageinstance_set.add(ins_obj)
