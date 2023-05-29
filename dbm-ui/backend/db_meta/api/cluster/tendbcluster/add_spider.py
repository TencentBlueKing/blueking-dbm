"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List, Optional

from django.db import transaction

from backend.db_meta.api import common
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, TenDBClusterSpiderExt


@transaction.atomic
def add_spiders(
    cluster: Optional[Cluster],
    spiders: Optional[List],
    spider_role: Optional[TenDBClusterSpiderRole],
    domain_entry: Optional[ClusterEntry] = None,
):
    """
    添加spider节点元信息, 包括spider不同角色的添加
    """
    # 获取相关的spider节点orm对象
    spiders_objs = common.filter_out_instance_obj(spiders, ProxyInstance.objects.all())

    # 对所有的spider实例角色属性
    for obj in spiders_objs:
        TenDBClusterSpiderExt.objects.create(instance=obj, spider_role=spider_role)

    # 添加 cluster 与所有spider实例的映射关系
    cluster.proxyinstance_set.add(*spiders_objs)

    # 对所有的分片的实例，添加与spider实例的映射关系
    for shard_info in cluster.tendbclusterstorageset_set.exclude(
        storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.REPEATER
    ):
        if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
            # ejector是代表master实例对象
            shard_info.storage_instance_tuple.ejector.proxyinstance_set.add(*spiders_objs)

        if spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
            # receiver是代表slave实例对象
            shard_info.storage_instance_tuple.receiver.proxyinstance_set.add(*spiders_objs)

    if not spider_role == TenDBClusterSpiderRole.SPIDER_MNT:
        # 非运维节点添加域名映射
        domain_entry.proxyinstance_set.add(*spiders_objs)

    # 直到这里才有明确的 db module
    for ins in spiders_objs:
        m = ins.machine
        ins.db_module_id = cluster.db_module_id
        m.db_module_id = cluster.db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])
