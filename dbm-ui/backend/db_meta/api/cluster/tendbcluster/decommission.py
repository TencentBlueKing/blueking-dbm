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

from backend import env
from backend.components import CCApi
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import (
    Cluster,
    ClusterEntry,
    MySQLStorageInstanceExt,
    StorageInstance,
    StorageInstanceTuple,
)

logger = logging.getLogger("root")


@transaction.atomic
def decommission(cluster: Cluster):
    # 处理spider节点信息
    for spider in cluster.proxyinstance_set.all():
        # 先删除额外的spider关联信息，否则直接删除实例，会报ProtectedError 异常
        spider.tendbclusterspiderext.delete()
        spider.delete(keep_parents=True)
        if not spider.machine.proxyinstance_set.exists():

            # 这个 api 不需要检查返回值, 转移主机到空闲模块，转移模块这里会把服务实例删除
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [spider.machine.bk_host_id]}
            )
            spider.machine.delete(keep_parents=True)

    # 处理remote节点信息
    for remote in cluster.storageinstance_set.all():

        for info in StorageInstanceTuple.objects.filter(ejector=remote):
            # 先删除额外关联信息，否则会报ProtectedError 异常
            info.tendbclusterstorageset.delete()
            info.delete()
        for info in StorageInstanceTuple.objects.filter(receiver=remote):
            # 先删除额外关联信息，否则会报ProtectedError 异常
            info.tendbclusterstorageset.delete()
            info.delete()

        # 先删除额外的mysql关联信息，否则直接删除实例，会报ProtectedError 异常
        try:
            ext = remote.mysqlstorageinstanceext
        except MySQLStorageInstanceExt.DoesNotExist:
            ext = None
        if ext:
            ext.delete()

        remote.delete(keep_parents=True)
        if not remote.machine.storageinstance_set.exists():

            # 这个 api 不需要检查返回值, 转移主机到待回收模块，转移模块这里会把服务实例删除
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [remote.machine.bk_host_id]}
            )
            remote.machine.delete(keep_parents=True)

    for ce in ClusterEntry.objects.filter(cluster=cluster).all():
        ce.delete(keep_parents=True)

    # 删除集群在bkcc对应的模块
    # todo 目前cc没有封装移除主机模块接口,先保留写法
    # delete_cluster_modules(db_type=DBType.MySQL.value, del_cluster_id=cluster.id)
    cluster.delete(keep_parents=True)


@transaction.atomic
def decommission_precheck(cluster: Cluster):
    """
    Tendb cluster 不可能出现集群间访问关系, 只会有同步关系
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
