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
from django.utils.translation import ugettext as _

from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, TenDBClusterSpiderExt


@transaction.atomic
def slave_cluster_create_pre_check(slave_domain: str):
    """
    添加从集群的元信息前置检测
    """
    pre_check_errors = []

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=slave_domain).exists():
        pre_check_errors.append(_("域名 {} 已存在").format(slave_domain))

    if pre_check_errors:
        raise DBMetaException(message=", ".join(pre_check_errors))


@transaction.atomic
def slave_cluster_create(
    cluster: Optional[Cluster],
    spiders: Optional[List],
    slave_domain: str,
    creator: str = "",
):
    """
    添加从集群元信息
    """
    # 获取相关的spider节点orm对象
    spiders_objs = common.filter_out_instance_obj(spiders, ProxyInstance.objects.all())

    # 对所有的spider slave实例角色属性
    for obj in spiders_objs:
        TenDBClusterSpiderExt.objects.create(instance=obj, spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE)

    # 添加 cluster 与所有spider slave 实例的映射关系
    cluster.proxyinstance_set.add(*spiders_objs)

    # 对所有的分片的slave实例，添加与spider slave实例的映射关系
    for shard_info in cluster.tendbclusterstorageset_set.exclude(
        storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.REPEATER
    ):
        # receiver是代表slave实例对象
        shard_info.storage_instance_tuple.receiver.proxyinstance_set.add(*spiders_objs)

    # 添加从域名映射
    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS,
        entry=slave_domain,
        creator=creator,
        role=ClusterEntryRole.SLAVE_ENTRY.value,
    )
    cluster_entry.proxyinstance_set.add(*spiders_objs)

    # 直到这里才有明确的 db module
    for ins in spiders_objs:
        m = ins.machine
        ins.db_module_id = cluster.db_module_id
        m.db_module_id = cluster.db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])
