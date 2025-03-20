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
from django.utils.translation import ugettext as _

from backend.components import DBPrivManagerApi
from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterDBHAExt, ClusterEntry, StorageInstanceTuple
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.flow.consts import MySQLPrivComponent, UserName
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


@transaction.atomic
def decommission(cluster: Cluster):
    cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)
    for proxy in cluster.proxyinstance_set.all():

        proxy.delete(keep_parents=True)
        if not proxy.machine.proxyinstance_set.exists():
            # 这个 api 不需要检查返回值, 转移主机到空闲模块，转移模块这里会把服务实例删除
            cc_manage.recycle_host([proxy.machine.bk_host_id])
            proxy.machine.delete(keep_parents=True)
        else:
            # 删除服务实例
            cc_manage.delete_service_instance(bk_instance_ids=[proxy.bk_instance_id])

    for storage in cluster.storageinstance_set.all():

        # 删除存储在密码服务的密码元信息
        DBPrivManagerApi.delete_password(
            {
                "instances": [{"ip": storage.machine.ip, "port": storage.port, "bk_cloud_id": cluster.bk_cloud_id}],
                "users": [{"username": UserName.ADMIN.value, "component": MySQLPrivComponent.MYSQL.value}],
            }
        )

        StorageInstanceTuple.objects.filter(ejector=storage).delete()
        StorageInstanceTuple.objects.filter(receiver=storage).delete()
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():

            # 这个 api 不需要检查返回值, 转移主机到待回收模块，转移模块这里会把服务实例删除
            CcManage(storage.bk_biz_id, cluster.cluster_type).recycle_host([storage.machine.bk_host_id])
            storage.machine.delete(keep_parents=True)

        else:
            # 删除服务实例
            cc_manage.delete_service_instance(bk_instance_ids=[storage.bk_instance_id])

    for ce in ClusterEntry.objects.filter(cluster=cluster).all():
        ce.delete(keep_parents=True)

    # 删除dbha配置信息
    ClusterDBHAExt.objects.filter(cluster=cluster).delete()
    # 删除集群相关的配置模板
    TendbOpenAreaConfig.objects.filter(source_cluster_id=cluster.id).delete()
    try:
        DBPartitionApi.cluster_del_conf(
            params={"cluster_type": cluster.cluster_type, "bk_biz_id": cluster.bk_biz_id, "cluster_ids": [cluster.id]}
        )
    except Exception as e:  # noqa
        logger.error(e)

    # 删除集群在bkcc对应的模块
    # TODO CC 目前没有把主机移出当前模块的接口，主机还在模块下，无法删除
    # cc_manage.delete_cluster_modules(db_type=DBType.MySQL.value, cluster=cluster)
    cluster.delete(keep_parents=True)


@transaction.atomic
def decommission_precheck(cluster: Cluster):
    """
    TenDBHA 不可能出现集群间访问关系, 只会有同步关系
    """

    precheck_err = []
    for s in cluster.storageinstance_set.all():
        # 作为 ejector 向集群外抛出日志不允许下架
        for tp in StorageInstanceTuple.objects.filter(ejector=s):
            recv = tp.receiver
            if recv.cluster.first() != cluster:
                precheck_err.append(_("{} 与 {} 的 {} 有同步关系").format(s, recv.cluster.first(), recv))

    if precheck_err:
        raise DBMetaException(message=", ".join(precheck_err))
