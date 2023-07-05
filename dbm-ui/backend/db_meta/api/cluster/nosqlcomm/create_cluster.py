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
from typing import Dict, List, Optional

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils.translation import ugettext as _

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    DBCCModule,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER

from ....exceptions import (
    ClusterEntryExistException,
    CreateTendisPreCheckException,
    DBMetaBaseException,
    ProxyBackendNotEmptyException,
)
from .cc_ops import cc_add_instance, cc_add_instances
from .create_instances import create_proxies, create_tendis_instances
from .precheck import before_create_domain_precheck, before_create_proxy_precheck, before_create_storage_precheck

logger = logging.getLogger("flow")


@transaction.atomic
def create_twemproxy_cluster(
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
    cluster_type: str = ClusterType.TendisTwemproxyRedisInstance.value,
):
    """
    兼容 TendisCache/TendisSSD 集群
    规则:
    1. 所有实例不能属于任何集群
    2. proxy 不能有已绑定的后端
    3. 必须只有 1 个 master
    """

    ip_port_storages = {"{}{}{}".format(s["ip"], IP_PORT_DIVIDER, s["port"]): s for s in storages}

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)

    proxy_objs, storage_objs = create_precheck(bk_biz_id, name, immute_domain, cluster_type, proxies, storages)

    # 创建集群, 添加存储和接入实例
    try:
        cluster = Cluster.objects.create(
            bk_biz_id=bk_biz_id,
            name=name,
            alias=alias,
            major_version=major_version,
            cluster_type=cluster_type,
            db_module_id=db_module_id,
            immute_domain=immute_domain,
            creator=creator,
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
            updater=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
        )
        cluster.proxyinstance_set.add(*proxy_objs)
        cluster.storageinstance_set.add(*storage_objs)
        cluster.save()

        for storage_obj in storage_objs:
            slave_obj = storage_obj.as_ejector.get().receiver
            cluster.storageinstance_set.add(slave_obj)

        update_cluster_type(storage_objs, cluster_type)
        update_cluster_type(proxy_objs, cluster_type)

        # 写入twemproxy分片规则
        for storage_obj in storage_objs:
            ins_key = "{}{}{}".format(storage_obj.machine.ip, IP_PORT_DIVIDER, storage_obj.port)
            meta = ip_port_storages.get(ins_key)
            if not meta:
                raise DBMetaBaseException(_("{} 实例未分片规则").format(ins_key))

            cluster.nosqlstoragesetdtl_set.create(
                instance=storage_obj,
                bk_biz_id=bk_biz_id,
                seg_range=meta["seg_range"],
                creator=creator,
            )

            # 设置接入层后端,兼容DBHA接口
            storage_obj.proxyinstance_set.add(*proxy_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e

        # 注册访问入口
    try:
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
        )
        cluster_entry.proxyinstance_set.add(*proxy_objs)
        cluster_entry.save()
    except IntegrityError:
        raise ClusterEntryExistException(entry=immute_domain)

    receivers = []
    for storage_obj in storage_objs:
        slave_obj = storage_obj.as_ejector.get().receiver
        receivers.append(slave_obj)

    cc_add_instances(cluster, proxy_objs, DBCCModule.REDIS.value)
    cc_add_instances(cluster, storage_objs, DBCCModule.REDIS.value)
    cc_add_instances(cluster, receivers, DBCCModule.REDIS.value)


@transaction.atomic
def pkg_create_twemproxy_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    proxies: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
    machine_specs: Optional[Dict] = None,
):
    """
    这里打包从头开始创建一个 MongoSet
    包括 machine、storage、tuple、cluster、cluster_entry等
    proxies  [{"ip":,"port":},{}]
    storages [{"shard":"","nodes":{"master":{"ip":"","port":1],"slave":{}}}, {}, {}]
    machine_specs {"proxy":{"spec_id":0,"spec_config":""},"redis":{"spec_id":0,"spec_config":""}}
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)

    all_instances, seg_instances = [], []
    for storage in storages:
        shard = storage["nodes"]
        all_instances.append(shard["master"])
        all_instances.append(shard["slave"])
        seg_instances.append(
            {"seg_range": storage["shard"], "ip": shard["master"]["ip"], "port": shard["master"]["port"]}
        )
    request_validator.validated_storage_list(all_instances, allow_empty=False, allow_null=False)

    before_create_domain_precheck([immute_domain])
    before_create_proxy_precheck(proxies)
    before_create_storage_precheck(all_instances)

    machine_specs = machine_specs or {}
    spec_id, spec_config = 0, ""
    if machine_specs.get("proxy"):
        spec_id, spec_config = machine_specs["proxy"]["spec_id"], machine_specs["proxy"]["spec_config"]
    create_proxies(
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        machine_type=MachineType.TWEMPROXY.value,
        proxies=proxies,
        spec_id=spec_id,
        spec_config=spec_config,
    )

    spec_id, spec_config = 0, ""
    if machine_specs.get("redis"):
        spec_id, spec_config = machine_specs["redis"]["spec_id"], machine_specs["redis"]["spec_config"]
    if cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
        create_tendis_instances(bk_biz_id, bk_cloud_id, MachineType.TENDISCACHE.value, storages, spec_id, spec_config)
    elif cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
        create_tendis_instances(bk_biz_id, bk_cloud_id, MachineType.TENDISSSD.value, storages, spec_id, spec_config)
    else:
        raise Exception("unspourted cluster type : {}".format(cluster_type))

    create_twemproxy_cluster(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        porxies=proxies,
        storages=seg_instances,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        region=region,
        cluster_type=cluster_type,
    )


@transaction.atomic
def update_storage_cluster_type(ins_obj: StorageInstance, cluster_type: str):
    slave_obj = ins_obj.as_ejector.get().receiver

    slave_obj.cluster_type = cluster_type
    ins_obj.cluster_type = cluster_type
    slave_obj.save(update_fields=["cluster_type"])
    ins_obj.save(update_fields=["cluster_type"])

    master_machine = ins_obj.machine
    slave_machine = slave_obj.machine
    master_machine.cluster_type = cluster_type
    slave_machine.cluster_type = cluster_type
    master_machine.save(update_fields=["cluster_type"])
    slave_machine.save(update_fields=["cluster_type"])


@transaction.atomic
def update_cluster_type(objs: QuerySet, cluster_type: str):
    """兼容 Storage 和 proxy 修改 cluster_type字段 （instance，machine）

    Args:
        objs (QuerySet): 实例集合
        cluster_type (str): 目标集群类型
    """
    for ins_obj in objs:
        if ins_obj.access_layer == AccessLayer.STORAGE:
            update_storage_cluster_type(ins_obj, cluster_type)
        # 更新 proxy cluster_type.
        else:
            ins_obj.cluster_type = cluster_type
            ins_obj.save(update_fields=["cluster_type"])

            proxy_machine = ins_obj.machine
            proxy_machine.cluster_type = cluster_type
            proxy_machine.save(update_fields=["cluster_type"])


def create_precheck(bk_biz_id: int, name: str, immute_domain: str, cluster_type: str, proxies: list, storages: list):
    """校验逻辑：集群名、域名、proxy和storage可用性"""

    if Cluster.objects.filter(bk_biz_id=bk_biz_id, name=name, cluster_type=cluster_type).exists():
        raise CreateTendisPreCheckException(msg=_("集群名 {} 在 bk_biz_id:{} 已存在").format(name, bk_biz_id))

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immute_domain).exists():
        raise CreateTendisPreCheckException(msg=_("域名 {} 已存在").format(immute_domain))

    # 检查域名是否已存在
    if Cluster.objects.filter(immute_domain=immute_domain).exists():
        raise Exception(_("域名 {} 已存在").format(immute_domain))

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

    # proxy已经绑定了存储节点
    for proxy_obj in proxy_objs:
        if proxy_obj.storageinstance.exists():
            raise ProxyBackendNotEmptyException(proxy="{}:{}".format(proxy_obj.machine.ip, proxy_obj.port))

    return proxy_objs, storage_objs
