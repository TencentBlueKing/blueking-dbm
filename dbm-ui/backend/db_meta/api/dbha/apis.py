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
from collections import defaultdict
from typing import Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend.constants import DEFAULT_BK_CLOUD_ID, IP_PORT_DIVIDER
from backend.db_meta import flatten, request_validator, validators
from backend.db_meta.enums import ClusterEntryType, ClusterStatus, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.exceptions import (
    ClusterSetDtlExistException,
    InstanceNotExistException,
    TendisClusterNotExistException,
)
from backend.db_meta.models import BKCity, Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_meta.request_validator import DBHASwapRequestSerializer, DBHAUpdateStatusRequestSerializer

logger = logging.getLogger("root")


def cities():
    return flatten.cities(BKCity.objects.all())


def entry_detail(domains: List[str]) -> List[Dict]:
    entries = {}
    for domain in domains:
        clusterentry_set = defaultdict(list)
        try:
            cluster_obj = Cluster.objects.get(immute_domain=domain)
        except ObjectDoesNotExist:
            raise TendisClusterNotExistException(cluster=domain)

        for cluster_entry_obj in cluster_obj.clusterentry_set.all():
            if cluster_entry_obj.cluster_entry_type == ClusterEntryType.DNS:
                clusterentry_set[cluster_entry_obj.cluster_entry_type].append(
                    {
                        "domain": cluster_entry_obj.entry,
                        "bind_ips": list(
                            set(
                                [
                                    ele.machine.ip
                                    for ele in list(cluster_entry_obj.proxyinstance_set.all())
                                    + list(cluster_entry_obj.storageinstance_set.all())
                                ]
                            )
                        ),
                    }
                )
            elif cluster_entry_obj.cluster_entry_type == ClusterEntryType.CLB:
                de = cluster_entry_obj.clbentrydetail_set.get()
                clusterentry_set[cluster_entry_obj.cluster_entry_type].append(
                    {
                        "clb_ip": de.clb_ip,
                        "clb_id": de.clb_id,
                        "listener_id": de.listener_id,
                        "clb_region": de.clb_region,
                    }
                )
            elif cluster_entry_obj.cluster_entry_type == ClusterEntryType.POLARIS:
                de = cluster_entry_obj.polarisentrydetail_set.get()
                clusterentry_set[cluster_entry_obj.cluster_entry_type].append(
                    {
                        "polaris_name": de.polaris_name,
                        "polaris_l5": de.polaris_l5,
                        "polaris_token": de.polaris_token,
                        "alias_token": de.alias_token,
                    }
                )
            else:
                clusterentry_set[cluster_entry_obj.cluster_entry_type].append(cluster_entry_obj.entry)
            entries[domain] = clusterentry_set
    return entries


@transaction.atomic
def instances(
    logical_city_ids: Optional[List[int]] = None,
    addresses: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
):

    logical_city_ids = request_validator.validated_integer_list(logical_city_ids)
    addresses = request_validator.validated_str_list(addresses)
    statuses = request_validator.validated_str_list(statuses)

    queries = Q()
    if addresses:
        for ad in [ad for ad in addresses if len(ad.strip()) > 0]:
            if validators.ipv4(ad):
                queries |= Q(**{"machine__ip": ad})
            elif validators.instance(ad):
                queries |= Q(**{"machine__ip": ad.split(IP_PORT_DIVIDER)[0], "port": ad.split(IP_PORT_DIVIDER)[1]})
            elif validators.domain(ad):
                queries |= Q(**{"cluster__clusterentry__entry": ad})
            else:
                logger.warning("{} is not a valid ip, instance or domain".format(ad))

    if logical_city_ids:
        queries &= Q(**{"machine__bk_city__logical_city_id__in": logical_city_ids})

    if statuses:
        queries &= Q(**{"status__in": statuses})

    queries &= Q(**{"machine__bk_cloud_id": bk_cloud_id})

    return flatten.storage_instance(StorageInstance.objects.filter(queries)) + flatten.proxy_instance(
        ProxyInstance.objects.filter(queries)
    )


@transaction.atomic
def update_status(payloads: List, bk_cloud_id: int):
    """
    ToDo 验证 status
    """
    DBHAUpdateStatusRequestSerializer(data={"payloads": payloads}).is_valid(raise_exception=True)
    for pl in payloads:
        ip = pl["ip"]
        port = pl["port"]

        try:
            storage_obj = StorageInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
            cluster = storage_obj.cluster.first()

            storage_obj.status = pl["status"]
            storage_obj.save(update_fields=["status"])
        except ObjectDoesNotExist:
            try:
                proxy_obj = ProxyInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
                cluster = proxy_obj.cluster.first()

                proxy_obj.status = pl["status"]
                proxy_obj.save(update_fields=["status"])
            except ObjectDoesNotExist:
                raise InstanceNotExistException(_("实例ip={}, port={}不存在，请检查输入参数或相关数据").format(ip, port))
            except Exception as e:
                raise e
        except Exception as e:
            raise e

        if cluster and pl["status"] == InstanceStatus.UNAVAILABLE.value:
            cluster.status = ClusterStatus.ABNORMAL.value
            cluster.save(update_fields=["status"])


@transaction.atomic
def swap_role(payloads: List, bk_cloud_id: int):
    """
    可以用来操作 tendbha 和 tendbcluster 的存储层
    """
    DBHASwapRequestSerializer(data={"payloads": payloads}).is_valid(raise_exception=True)
    for pl in payloads:
        ins1 = pl["instance1"]
        ins2 = pl["instance2"]

        ins1_obj = StorageInstance.objects.get(
            machine__ip=ins1["ip"], port=ins1["port"], machine__bk_cloud_id=bk_cloud_id
        )
        ins2_obj = StorageInstance.objects.get(
            machine__ip=ins2["ip"], port=ins2["port"], machine__bk_cloud_id=bk_cloud_id
        )

        if (
            not StorageInstanceTuple.objects.filter(ejector=ins1_obj, receiver=ins2_obj).exists()
            and not StorageInstanceTuple.objects.filter(ejector=ins2_obj, receiver=ins1_obj).exists()
        ):
            raise Exception(
                "no replicate relate between {}:{} {}:{}".format(
                    ins1_obj.machine.ip, ins1_obj.port, ins2_obj.machine.ip, ins2_obj.port
                )
            )

        if (
            ins1_obj.instance_inner_role == InstanceInnerRole.REPEATER
            or ins2_obj.instance_role == InstanceInnerRole.REPEATER
        ):
            raise Exception("repeater found, may be not prod cluster")

        __swap(ins1_obj, ins2_obj)


def __swap(ins1: StorageInstance, ins2: StorageInstance):
    # 修改 proxy backend
    temp_proxy_set = list(ins1.proxyinstance_set.all())

    ins1.proxyinstance_set.clear()
    ins1.proxyinstance_set.add(*ins2.proxyinstance_set.all())

    ins2.proxyinstance_set.clear()
    ins2.proxyinstance_set.add(*temp_proxy_set)

    StorageInstanceTuple.objects.get(ejector=ins1, receiver=ins2).delete(keep_parents=True)
    StorageInstanceTuple.objects.create(ejector=ins2, receiver=ins1)

    temp_instance_role = ins1.instance_role
    tmep_instance_inner_role = ins1.instance_inner_role

    ins1.instance_role = ins2.instance_role
    ins1.instance_inner_role = ins2.instance_inner_role

    ins2.instance_role = temp_instance_role
    ins2.instance_inner_role = tmep_instance_inner_role

    ins1.save(update_fields=["instance_role", "instance_inner_role"])
    ins2.save(update_fields=["instance_role", "instance_inner_role"])


@transaction.atomic
def tendis_cluster_swap(payload: Dict, bk_cloud_id: int):
    """
    集群模式下,提升slave 为 master
    1. 互换ins1,ins2 tuple_ 表
    2. 修改 setDtl 表为 ins2
    """
    try:
        cluster_obj = Cluster.objects.get(immute_domain=payload["domain"])
    except ObjectDoesNotExist:
        raise TendisClusterNotExistException(cluser=payload["domain"])

    master = payload["master"]
    slave = payload["slave"]

    ins1_obj = StorageInstance.objects.get(
        machine__ip=master["ip"], port=master["port"], machine__bk_cloud_id=bk_cloud_id
    )
    ins2_obj = StorageInstance.objects.get(
        machine__ip=slave["ip"], port=slave["port"], machine__bk_cloud_id=bk_cloud_id
    )

    if (
        not StorageInstanceTuple.objects.filter(ejector=ins1_obj, receiver=ins2_obj).exists()
        and not StorageInstanceTuple.objects.filter(ejector=ins2_obj, receiver=ins1_obj).exists()
    ):
        raise Exception(
            "no replicate relate between {}:{} {}:{}".format(
                ins1_obj.machine.ip, ins1_obj.port, ins2_obj.machine.ip, ins2_obj.port
            )
        )

    # 修改表db_meta_storagesetdtl  关联对象-->改成slave
    try:
        cluster_obj.nosqlstoragesetdtl_set.filter(instance=ins1_obj).update(instance=ins2_obj)
    except ObjectDoesNotExist:
        raise ClusterSetDtlExistException(cluster=payload["domain"], master=master)

    # 修改表db_meta_proxyinstance_storageinstance  关联对象-->改成slave
    temp_proxy_set = list(ins1_obj.proxyinstance_set.all())
    ins1_obj.proxyinstance_set.clear()
    ins2_obj.proxyinstance_set.clear()
    ins2_obj.proxyinstance_set.add(*temp_proxy_set)

    StorageInstanceTuple.objects.get(ejector=ins1_obj, receiver=ins2_obj).delete(keep_parents=True)
    StorageInstanceTuple.objects.create(ejector=ins2_obj, receiver=ins1_obj)

    temp_instance_role = ins1_obj.instance_role
    tmep_instance_inner_role = ins1_obj.instance_inner_role

    ins1_obj.instance_role = ins2_obj.instance_role
    ins1_obj.instance_inner_role = ins2_obj.instance_inner_role

    ins2_obj.instance_role = temp_instance_role
    ins2_obj.instance_inner_role = tmep_instance_inner_role

    ins1_obj.save(update_fields=["instance_role", "instance_inner_role"])
    ins2_obj.save(update_fields=["instance_role", "instance_inner_role"])


@transaction.atomic
def swap_ctl_role(payloads: List):
    DBHASwapRequestSerializer(data={"payloads": payloads}).is_valid(raise_exception=True)
    for pl in payloads:
        ins1 = pl["instance1"]
        ins2 = pl["instance2"]
        bk_cloud_id = pl.get("bk_cloud_id")

        ins1_obj = ProxyInstance.objects.get(
            machine__ip=ins1["ip"],
            port=ins1["port"],
            machine__bk_cloud_id=bk_cloud_id,
            cluster__cluster_type=ClusterType.TenDBCluster.value,
        )

        ins2_obj = ProxyInstance.objects.get(
            machine__ip=ins2["ip"],
            port=ins2["port"],
            machine__bk_cloud_id=bk_cloud_id,
            cluster__cluster_type=ClusterType.TenDBCluster.value,
        )

        ins1_ctl_role = ins1_obj.tendbclusterspiderext.ctl_role

        ins1_obj.tendbclusterspiderext.ctl_role = ins2_obj.tendbclusterspiderext.ctl_role
        ins2_obj.tendbclusterspiderext.ctl_role = ins1_ctl_role

        ins1_obj.save()
        ins2_obj.save()
