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

from backend.db_meta.api import common
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, TenDBClusterSpiderExt

logger = logging.getLogger("root")


@transaction.atomic
def add_spider_mnt(
    cluster: Optional[Cluster],
    spiders: Optional[List],
):
    """
    添加运维节点的集群相关信息
    与集群进行关联
    """
    # 获取相关的spider节点orm对象
    spiders_objs = common.filter_out_instance_obj(spiders, ProxyInstance.objects.all())

    # TenDBClusterSpiderExt是对ProxyInstance的延伸，使用一对一关系来补充信息，主要补充了spider节点的类别
    for obj in spiders_objs:
        TenDBClusterSpiderExt.objects.create(instance=obj, spider_role=TenDBClusterSpiderRole.SPIDER_MNT)

    # 添加 cluster 与所有spider云维实例的映射关系
    cluster.proxyinstance_set.add(*spiders_objs)

    # 对所有的分片的slave实例，添加与spider slave实例的映射关系
    for shard_info in cluster.tendbclusterstorageset_set.exclude(
        storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.REPEATER
    ):
        # receiver是代表slave实例对象
        # shard_info是db_meta_tendbclusterstorageset对象
        # db_meta_tendbclusterstorageset.storage_instance_tuple（id）指向db_meta_storageinstancetuple
        # shard_info.storage_instance_tuple.receiver指向db_meta_storageinstance
        # shard_info.storage_instance_tuple.receiver.proxyinstance_set  proxyinstance_set为多对多表反向操作关联管理器
        shard_info.storage_instance_tuple.ejector.proxyinstance_set.add(*spiders_objs)

    # 添加从域名映射
    cluster_entry = cluster.clusterentry_set.first()
    cluster_entry.proxyinstance_set.add(*spiders_objs)

    # 直到这里才有明确的 db module
    for ins in spiders_objs:
        m = ins.machine
        ins.db_module_id = cluster.db_module_id
        m.db_module_id = cluster.db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])
