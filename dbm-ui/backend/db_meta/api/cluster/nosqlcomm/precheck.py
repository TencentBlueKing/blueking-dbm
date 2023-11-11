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

from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.exceptions import CreateTendisPreCheckException, ProxyBackendNotEmptyException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance


def before_create_storage_precheck(storages):
    for storage in storages:
        if StorageInstance.objects.filter(machine__ip=storage["ip"], port=storage["port"]).exists():
            raise Exception("storage instance aleardy exists {}:{}".format(storage["ip"], storage["port"]))


def before_create_proxy_precheck(proxies):
    for storage in proxies:
        if ProxyInstance.objects.filter(machine__ip=storage["ip"], port=storage["port"]).exists():
            raise Exception("storage instance aleardy exists {}:{}".format(storage["ip"], storage["port"]))


def before_create_domain_precheck(domains):
    for domain in domains:
        if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry=domain).exists():
            raise Exception("dns entry aleardy exists {}".format(domain))


def create_precheck(bk_biz_id: int, name: str, immute_domain: str, cluster_type: str, proxies: list, storages: list):
    """校验逻辑：集群名、域名、proxy和storage可用性"""

    create_domain_precheck(bk_biz_id=bk_biz_id, name=name, immute_domain=immute_domain, cluster_type=cluster_type)
    storage_objs = create_storage_precheck(storages=storages)
    proxy_objs = create_proxies_precheck(proxies=proxies)

    return proxy_objs, storage_objs


def create_domain_precheck(bk_biz_id: int, name: str, immute_domain: str, cluster_type: str):
    if Cluster.objects.filter(bk_biz_id=bk_biz_id, name=name, cluster_type=cluster_type).exists():
        raise Exception("Cluster Name {} IN bk_biz_id:{} Aleardy Exist".format(name, bk_biz_id))

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immute_domain).exists():
        raise Exception("Cluster ClusterEntry {}  Aleardy Exist".format(immute_domain))

    # 检查域名是否已存在
    if Cluster.objects.filter(immute_domain=immute_domain).exists():
        raise Exception("Cluster {}  Aleardy Exist".format(immute_domain))


def create_proxies_precheck(proxies: list):
    # proxy 不能属于任何集群
    proxy_objs = common.filter_out_instance_obj(proxies, ProxyInstance.objects.all())

    in_obj = common.in_another_cluster(proxy_objs)
    if in_obj:
        raise CreateTendisPreCheckException(msg="proxy {} belong other cluster".format(in_obj))

    # proxy已经绑定了存储节点
    for proxy_obj in proxy_objs:
        if proxy_obj.storageinstance.exists():
            raise ProxyBackendNotEmptyException(proxy="{}:{}".format(proxy_obj.machine.ip, proxy_obj.port))

    return proxy_objs


def create_storage_precheck(storages: list):
    # storage 不能属于任何集群
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    in_obj = common.in_another_cluster(storage_objs)
    if in_obj:
        raise CreateTendisPreCheckException(msg="storage {}  belong other cluster".format(in_obj))
    return storage_objs
