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
import traceback
from typing import List, Optional

from django.db import IntegrityError, transaction
from django.utils.translation import ugettext as _

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance
from backend.flow.utils.redis.redis_module_operate import RedisCCTopoOperator

from ....exceptions import ClusterEntryExistException, CreateTendisPreCheckException, ProxyBackendNotEmptyException

logger = logging.getLogger("flow")


@transaction.atomic
def create(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    proxies: Optional[List] = None,
    storages: Optional[List] = None,
    alias: str = "",
    major_version: str = "",
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    disaster_tolerance_level: str = "",
):
    """
    注册 TendisplusCluster 集群
    规则:
    1. 所有实例不能属于任何集群
    2. predixy 不能有已绑定的后端
    3. 必须只有 1 个 master

    所以
    1. predixy 的 backend 绑定是在这里做的
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)

    proxy_objs, storage_objs = create_precheck(immute_domain, proxies, storages)

    # 创建集群, 添加存储和接入实例
    try:
        cluster = Cluster.objects.create(
            bk_biz_id=bk_biz_id,
            name=name,
            alias=alias,
            major_version=major_version,
            cluster_type=ClusterType.TendisPredixyTendisplusCluster.value,
            db_module_id=db_module_id,
            immute_domain=immute_domain,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            disaster_tolerance_level=disaster_tolerance_level,
        )
        cluster.proxyinstance_set.add(*proxy_objs)
        cluster.storageinstance_set.add(*storage_objs)
        cluster.save()

        # 把slave 也写入 storageinstance_cluster.
        for storage_obj in storage_objs:
            slave = storage_obj.as_ejector.get().receiver
            cluster.storageinstance_set.add(slave)

            # 设置接入层后端,兼容DBHA接口
            storage_obj.proxyinstance_set.add(*proxy_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e

    # 注册访问入口
    try:
        ce = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
        )
        ce.proxyinstance_set.add(*proxy_objs)
        ce.save()
    except IntegrityError:
        logger.error(traceback.format_exc())
        raise ClusterEntryExistException(entry=immute_domain)

    # 更新 db module && cluster_type.
    for proxy_obj in proxy_objs:
        proxy_obj.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        proxy_obj.save(update_fields=["cluster_type"])

        m = proxy_obj.machine
        m.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        m.save(update_fields=["cluster_type"])

    # 更新 master，slave 模块ID 和集群类型
    slave_objs = []
    for storage_obj in storage_objs:
        storage_obj.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        storage_obj.save(update_fields=["cluster_type"])

        m = storage_obj.machine
        m.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        m.save(update_fields=["cluster_type"])

        # update slave ..
        slave = storage_obj.as_ejector.get().receiver
        slave_objs.append(slave)
        slave_machine = slave.machine
        slave.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        slave.save(update_fields=["cluster_type"])

        slave_machine.cluster_type = ClusterType.TendisPredixyTendisplusCluster
        slave_machine.save(update_fields=["cluster_type"])

    cc_topo_operator = RedisCCTopoOperator(cluster)
    cc_topo_operator.transfer_instances_to_cluster_module(slave_objs)
    cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)
    cc_topo_operator.transfer_instances_to_cluster_module(proxy_objs)


def create_precheck(domain, proxies, storages):
    """TODO: common中的函数需要推敲下,逻辑写的不够直观"""

    # 检查域名是否已存在
    if Cluster.objects.filter(immute_domain=domain).exists():
        raise Exception(_("域名 {} 已存在").format(domain))

    # proxy 不能属于任何集群
    proxy_objs = common.filter_out_instance_obj(proxies, ProxyInstance.objects.all())

    in_obj = common.in_another_cluster(proxy_objs)
    if in_obj:
        raise CreateTendisPreCheckException(msg=_("proxy {} 已属于其他集群").format(in_obj))

    # storage 不能属于任何集群
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    in_obj = common.in_another_cluster(storage_objs)
    if in_obj:
        raise CreateTendisPreCheckException(msg=_("storage {} 已属于其他集群").format(in_obj))

    # 这里实际还检查了比如把一个 storage 当 proxy 传入
    no_obj = common.not_exists(proxies, proxy_objs)
    if no_obj:
        raise CreateTendisPreCheckException(msg=_("proxy {} 未注册").format(no_obj))

    no_obj = common.not_exists(storages, storage_objs)
    if no_obj:
        raise CreateTendisPreCheckException(msg=_("storage {} 未注册").format(no_obj))

    for proxy_obj in proxy_objs:
        if proxy_obj.storageinstance.exists():
            raise ProxyBackendNotEmptyException(proxy="{}:{}".format(proxy_obj.machine.ip, proxy_obj.port))

    # 检查结束
    return proxy_objs, storage_objs
