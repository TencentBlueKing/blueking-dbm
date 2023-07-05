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
from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
    TenDBClusterSpiderRole,
)
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import (
    Cluster,
    ClusterEntry,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
    TenDBClusterSpiderExt,
    TenDBClusterStorageSet,
)
from backend.flow.utils.spider.spider_act_dataclass import ShardInfo

logger = logging.getLogger("root")


@transaction.atomic
def create_pre_check(
    bk_biz_id: int,
    name: str,
    immutable_domain: str,
    db_module_id: int,
    spider_ctl_domain: str = None,
):
    """
    流程未执行不知道 ip, 也没有实例
    所以只做 name, 域名的唯一性检查
    """
    pre_check_errors = []

    # bk_biz_id, db_module_id, name 唯一性检查
    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, name=name, cluster_type=ClusterType.TenDBCluster.value, db_module_id=db_module_id
    ).exists():
        pre_check_errors.append(_("集群名 {} 在 bk_biz_id:{} db_module_id:{} 已存在").format(name, bk_biz_id, db_module_id))

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immutable_domain).exists():
        pre_check_errors.append(_("域名 {} 已存在").format(immutable_domain))

    if spider_ctl_domain:
        if ClusterEntry.objects.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, entry=spider_ctl_domain
        ).exists():
            pre_check_errors.append(_("域名 {} 已存在").format(immutable_domain))

    if pre_check_errors:
        raise DBMetaException(message=", ".join(pre_check_errors))


@transaction.atomic
def create(
    bk_biz_id: int,
    name: str,
    immutable_domain: str,
    major_version: str,
    db_module_id: int,
    bk_cloud_id: int,
    shard_infos: Optional[List[ShardInfo]],
    time_zone: str,
    spiders: Optional[List],
    storages: Optional[List],
    creator: str = "",
    region: str = "",
):
    """
    注册 TenDBCluster 集群
    """
    # 检验传入的参数是否合法
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immutable_domain = request_validator.validated_domain(immutable_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    spiders = request_validator.validated_proxy_list(spiders, allow_empty=False, allow_null=False)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)

    # 获取相关的spider节点orm对象以storage节点对象
    spiders_objs = common.filter_out_instance_obj(spiders, ProxyInstance.objects.all())
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())

    # 增加所有的spider实例角色属性，集群部署只能先有spider_master角色
    for obj in spiders_objs:
        TenDBClusterSpiderExt.objects.create(instance=obj, spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)

    # 根据信息创建spider集群元信息

    cluster = Cluster.objects.create(
        bk_biz_id=bk_biz_id,
        name=name,
        cluster_type=ClusterType.TenDBCluster.value,
        db_module_id=db_module_id,
        immute_domain=immutable_domain,
        creator=creator,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        bk_cloud_id=bk_cloud_id,
        time_zone=time_zone,
        major_version=major_version,  # 这里存储集群的主版本信息，主要是为展示，存储mysql版本
        region=region,  # 这里保存申请资源的地域信息
    )

    # 添加 cluster 与所有spider实例和storage实例的映射关系
    cluster.proxyinstance_set.add(*spiders_objs)
    cluster.storageinstance_set.add(*storage_objs)

    # 对所有的分片的master实例，添加与spider实例的映射关系
    for obj in storage_objs.filter(instance_inner_role=InstanceInnerRole.MASTER):
        obj.proxyinstance_set.add(*spiders_objs)

    # 根据传入的shard分片信息，保存对应实例主从对和分片信息, 增加额外mysql实例关联信息
    for info in shard_infos:
        master_storage_obj = storage_objs.get(
            machine__ip=info.instance_tuple.master_ip, port=info.instance_tuple.mysql_port, cluster=cluster
        )
        slave_storage_obj = storage_objs.get(
            machine__ip=info.instance_tuple.slave_ip, port=info.instance_tuple.mysql_port, cluster=cluster
        )
        storage_inst_tuple = StorageInstanceTuple.objects.create(
            ejector=master_storage_obj, receiver=slave_storage_obj
        )
        TenDBClusterStorageSet.objects.create(
            storage_instance_tuple=storage_inst_tuple, shard_id=info.shard_key, cluster=cluster
        )

    # 添加域名映射
    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immutable_domain, creator=creator
    )
    cluster_entry.proxyinstance_set.add(*spiders_objs)

    # 直到这里才有明确的 db module
    for ins in spiders_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    return cluster.id
