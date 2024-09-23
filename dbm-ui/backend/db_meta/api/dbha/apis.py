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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import validators
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Q
from django.utils.translation import ugettext_lazy as _

from backend.constants import DEFAULT_BK_CLOUD_ID, IP_PORT_DIVIDER
from backend.db_meta import flatten, meta_validator, request_validator
from backend.db_meta.api.cluster.sqlserverha.handler import SqlserverHAClusterHandler
from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceStatus,
)
from backend.db_meta.exceptions import (
    ClusterNotExistException,
    ClusterSetDtlExistException,
    InstanceNotExistException,
    TendisClusterNotExistException,
)
from backend.db_meta.models import (
    BKCity,
    Cluster,
    ClusterDBHAExt,
    ClusterEntry,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)
from backend.db_meta.request_validator import DBHASwapRequestSerializer, DBHAUpdateStatusRequestSerializer
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("root")


def cities():
    return flatten.cities(BKCity.objects.all())


def entry_detail(domains: List[str]) -> Dict[str, Dict[Any, list]]:
    entries = {}
    for domain in domains:
        clusterentry_set = defaultdict(list)
        try:
            cluster_obj = Cluster.objects.get(immute_domain=domain)
        except ObjectDoesNotExist:
            raise ClusterNotExistException(cluster=domain)

        for cluster_entry_obj in cluster_obj.clusterentry_set.all():
            if cluster_entry_obj.cluster_entry_type == ClusterEntryType.DNS:

                if cluster_entry_obj.storageinstance_set.exists():
                    bind_ips = list(set([ele.machine.ip for ele in list(cluster_entry_obj.storageinstance_set.all())]))
                    bind_port = cluster_entry_obj.storageinstance_set.first().port
                elif cluster_entry_obj.proxyinstance_set.exists():
                    bind_ips = list(set([ele.machine.ip for ele in list(cluster_entry_obj.proxyinstance_set.all())]))
                    bind_port = cluster_entry_obj.proxyinstance_set.first().port
                else:
                    bind_ips = []
                    bind_port = 0

                clusterentry_set[cluster_entry_obj.cluster_entry_type].append(
                    {
                        "domain": cluster_entry_obj.entry,
                        "entry_role": cluster_entry_obj.role,
                        "forward_entry_id": cluster_entry_obj.forward_to_id,
                        "bind_ips": bind_ips,
                        "bind_port": bind_port,
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


def instances(
    logical_city_ids: Optional[List[int]] = None,
    addresses: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    cluster_types: Optional[List[str]] = None,
    hash_cnt: Optional[int] = None,
    hash_value: Optional[int] = None,
):

    logical_city_ids = request_validator.validated_integer_list(logical_city_ids)
    addresses = request_validator.validated_str_list(addresses)
    statuses = request_validator.validated_str_list(statuses)

    # dbha 会频繁周期性调用这个函数, 拉取需要探测的实例
    # 在这个接口的最开始, 检查所有集群的 end_time
    # 如果 end_time < now, 就把 begin_time 和 end_time 置 NULL
    # 这样下面 query 实例的代码就可以把屏蔽到期的集群捞出来了
    # 因为这个只是给 dbha 用, 如果 dbha 挂了, 这个字段没有及时更新, 也没啥影响
    ClusterDBHAExt.objects.filter(end_time__lt=datetime.now(timezone.utc)).delete()

    queries = Q()

    if addresses:
        for ad in [ad for ad in addresses if len(ad.strip()) > 0]:
            if validators.ipv4(ad):
                queries |= Q(**{"machine__ip": ad})
            elif meta_validator.instance(ad):
                queries |= Q(**{"machine__ip": ad.split(IP_PORT_DIVIDER)[0], "port": ad.split(IP_PORT_DIVIDER)[1]})
            elif validators.domain(ad):
                queries |= Q(**{"cluster__clusterentry__entry": ad})
            else:
                logger.warning("{} is not a valid ip, instance or domain".format(ad))
                raise ValueError("{} is not a valid ip, instance or domain".format(ad))

    # 如果没有城市ID，或者城市ID包含-1，则不过滤城市
    if logical_city_ids and -1 not in logical_city_ids:
        queries &= Q(**{"machine__bk_city__logical_city_id__in": logical_city_ids})

    if statuses:
        queries &= Q(**{"status__in": statuses})

    queries &= Q(**{"machine__bk_cloud_id": bk_cloud_id})
    queries &= ~Q(**{"phase": InstancePhase.TRANS_STAGE})  # 排除 scr/gcs 迁移状态实例
    if cluster_types:
        queries &= Q(**{"cluster__cluster_type__in": cluster_types})

    storage_qs = StorageInstance.objects.filter(queries)
    proxy_qs = ProxyInstance.objects.filter(queries)

    if hash_cnt is not None and hash_value is not None:
        storage_qs = storage_qs.annotate(bk_host_id_mod=F("machine__bk_host_id") % hash_cnt).filter(
            bk_host_id_mod=hash_value
        )
        proxy_qs = proxy_qs.annotate(bk_host_id_mod=F("machine__bk_host_id") % hash_cnt).filter(
            bk_host_id_mod=hash_value
        )

    flat_instances = flatten.storage_instance(storage_qs) + flatten.proxy_instance(proxy_qs)
    disabled_dbha_cluster_ids = list(
        ClusterDBHAExt.objects.filter(end_time__gte=datetime.now()).values_list("cluster_id", flat=True)
    )

    return [ele for ele in flat_instances if ele["cluster_id"] not in disabled_dbha_cluster_ids]


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

    st = StorageInstanceTuple.objects.get(ejector=ins1, receiver=ins2)
    st.ejector = ins2
    st.receiver = ins1
    st.save(update_fields=["ejector", "receiver"])

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
    3. 切换CC 服务实例 角色
    """
    try:
        cluster_obj = Cluster.objects.get(immute_domain=payload["domain"], bk_cloud_id=bk_cloud_id)
    except ObjectDoesNotExist:
        raise TendisClusterNotExistException(cluser=payload["domain"])

    master, slave = payload["master"], payload["slave"]
    ins1_obj = StorageInstance.objects.get(
        machine__ip=master["ip"],
        port=master["port"],
        machine__bk_cloud_id=bk_cloud_id,
        bk_biz_id=cluster_obj.bk_biz_id,
    )
    ins2_obj = StorageInstance.objects.get(
        machine__ip=slave["ip"], port=slave["port"], machine__bk_cloud_id=bk_cloud_id, bk_biz_id=cluster_obj.bk_biz_id
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
    if cluster_obj.cluster_type == ClusterType.TendisRedisInstance.value:
        # 1. master 故障，需要把master 的entry 转移到 slave ，重建热备的时候，再纠正slave域名
        for bind_entry in ins1_obj.bind_entry.all():
            entry_obj = cluster_obj.clusterentry_set.get(id=bind_entry.id)
            if entry_obj.cluster_entry_type == ClusterEntryType.DNS.value:
                switch_instance_domain(ins1_obj, ins2_obj, entry_obj)
            ins1_obj.bind_entry.remove(entry_obj)
            ins2_obj.bind_entry.add(entry_obj)
        # 2. slave  故障，需要把slave 的entry 转移到master，重建热备的时候，再纠正slave域名 // TODO(update_status.)
    else:
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
    # 切换CC 服务实例 角色，性能数据展示使用
    swap_cc_svr_instance_role(ins1_obj, ins2_obj)


@transaction.atomic
def switch_instance_domain(ins1, ins2: StorageInstance, entry_obj: ClusterEntry):
    dns_manage = DnsManage(bk_biz_id=ins1.bk_biz_id, bk_cloud_id=ins1.machine.bk_cloud_id)
    old_instance = "{}#{}".format(ins1.machine.ip, ins1.port)
    new_instance = "{}#{}".format(ins2.machine.ip, ins2.port)
    logger.info("try update dns pointer {} from {} to {}".format(entry_obj.entry, ins1, ins2))
    if not dns_manage.update_domain(
        old_instance=old_instance, new_instance=new_instance, update_domain_name=entry_obj.entry
    ):
        raise Exception("update domain {} failed ".format(entry_obj.entry))


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


@transaction.atomic
def swap_cc_svr_instance_role(ins1_obj: StorageInstance, ins2_obj: StorageInstance):
    cc_manage = CcManage(ins1_obj.bk_biz_id, ins1_obj.cluster_type)
    # 切换新master服务实例角色标签
    cc_manage.add_label_for_service_instance(
        bk_instance_ids=[ins1_obj.bk_instance_id],
        labels_dict={"instance_role": ins1_obj.instance_role},
    )

    # 切换新slave服务实例角色标签
    cc_manage.add_label_for_service_instance(
        bk_instance_ids=[ins2_obj.bk_instance_id],
        labels_dict={"instance_role": ins2_obj.instance_role},
    )
    cc_manage.update_host_properties(bk_host_ids=[ins1_obj.machine.bk_host_id, ins2_obj.machine.bk_host_id])


@transaction.atomic
def sqlserver_cluster_swap(payloads: List, bk_cloud_id: int):
    """
    用于切换sqlserver集群实例
    @param payloads: 传入主从参数
    @param bk_cloud_id: 云区域ID
    """
    DBHASwapRequestSerializer(data={"payloads": payloads}).is_valid(raise_exception=True)
    for pl in payloads:
        old_master = pl["instance1"]
        new_master = pl["instance2"]

        old_master_obj = StorageInstance.objects.get(
            machine__ip=old_master["ip"], port=old_master["port"], machine__bk_cloud_id=bk_cloud_id
        )
        new_master_obj = StorageInstance.objects.get(
            machine__ip=new_master["ip"], port=new_master["port"], machine__bk_cloud_id=bk_cloud_id
        )

        if (
            not StorageInstanceTuple.objects.filter(ejector=old_master_obj, receiver=new_master_obj).exists()
            and not StorageInstanceTuple.objects.filter(ejector=new_master_obj, receiver=old_master_obj).exists()
        ):
            raise Exception(
                "no replicate relate between {}:{} {}:{}".format(
                    old_master_obj.machine.ip, old_master_obj.port, new_master_obj.machine.ip, new_master_obj.port
                )
            )

        if (
            old_master_obj.instance_inner_role == InstanceInnerRole.REPEATER
            or new_master_obj.instance_role == InstanceInnerRole.REPEATER
        ):
            raise Exception("repeater found, may be not prod cluster")

        # 切换元数据
        cluster_id = old_master_obj.cluster.get().id
        SqlserverHAClusterHandler.switch_role(
            cluster_ids=[cluster_id],
            old_master=Host(ip=old_master["ip"], bk_cloud_id=bk_cloud_id),
            new_master=Host(ip=new_master["ip"], bk_cloud_id=bk_cloud_id),
            is_force=True,
        )
