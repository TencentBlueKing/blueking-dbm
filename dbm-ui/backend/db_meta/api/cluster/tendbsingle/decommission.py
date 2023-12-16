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

from django.db import transaction

from backend.components import DBPrivManagerApi
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import MySQLPrivComponent, UserName
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


@transaction.atomic
def decommission(cluster: Cluster):
    cc_manage = CcManage(cluster.bk_biz_id)
    for storage in cluster.storageinstance_set.all():
        # 删除存储在密码服务的密码元信息
        DBPrivManagerApi.delete_password(
            {
                "instances": [{"ip": storage.machine.ip, "port": storage.port, "bk_cloud_id": cluster.bk_cloud_id}],
                "users": [{"username": UserName.ADMIN.value, "component": MySQLPrivComponent.MYSQL.value}],
            }
        )
        storage.delete(keep_parents=True)
        # MySQL 可能存在单机多集群/多实例的场景，因此下架时，需判断主机的所有实例是否都被下架了
        if not storage.machine.storageinstance_set.exists():
            # 转移主机到待回收
            cc_manage.recycle_host([storage.machine.bk_host_id])
            storage.machine.delete(keep_parents=True)
        else:
            # 删除服务实例
            cc_manage.delete_service_instance(bk_instance_ids=[storage.bk_instance_id])

    for ce in ClusterEntry.objects.filter(cluster=cluster).all():
        ce.delete(keep_parents=True)

    # 删除集群在bkcc对应的模块
    # cc_manage.delete_cluster_modules(db_type=DBType.MySQL.value, cluster=cluster)
    cluster.delete(keep_parents=True)
