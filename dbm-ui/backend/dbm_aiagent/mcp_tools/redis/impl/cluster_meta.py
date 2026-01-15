"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict, List

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceRole
from backend.db_meta.models import (
    AppCache,
    Cluster,
    ClusterEntry,
    Machine,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)


def list_my_redis_bizs(userID: str) -> List:
    res = []
    for app in AppCache.objects.all():
        bk_biz_id = app.bk_biz_id

        if DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, users__0=userID, db_type=DBType.Redis.value):
            res.append({"bk_biz_id": bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def list_biz_by_name(biz_name: str) -> List:
    res = []
    for app in AppCache.objects.all():
        if app.db_app_abbr.__contains__(biz_name.lower()):
            res.append({"bk_biz_id": app.bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def redis_list_clusters(bk_biz_id: int) -> List:
    clusters = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type__in=[
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
            ClusterType.TwemproxyTendisSSDInstance,
            ClusterType.TendisTwemproxyRedisInstance,
            ClusterType.RedisInstance,
        ],
    )

    return [
        {
            "cluster_id": c.id,
            "bk_cloud_id": c.bk_cloud_id,
            "cluster_type": c.cluster_type,
            "immute_domain": c.immute_domain,
            "alias": c.alias,
            "region": c.region,
            "proxy_count": len(c.proxyinstance_set.all()),
            "master_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)),
            "redis_version": c.major_version,
        }
        for c in clusters
    ]


def cluster_overview(immute_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)

    return {
        "bk_biz_id": cluster_obj.bk_biz_id,
        "cluster_id": cluster_obj.id,
        "bk_cloud_id": cluster_obj.bk_cloud_id,
        "cluster_type": cluster_obj.cluster_type,
        "cluster_domain": immute_domain,
        "region": cluster_obj.region,
        "major_version": cluster_obj.major_version,
        "proxy_count": len(cluster_obj.proxyinstance_set.all()),
        "master_count": len(cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)),
        "cluster_entries": [
            {"entry_type": ce.cluster_entry_type, "entry_addr": ce.entry}
            for ce in ClusterEntry.objects.filter(cluster=cluster_obj)
        ],
    }


def cluster_proxies(immute_domain: str) -> List:
    """集群proxy 列表"""
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    proxy_instances = c_obj.proxyinstance_set.all()
    return [
        {
            "address": "{}:{}".format(s.machine.ip, s.port),
            "status": s.status,
            "version": s.version,
            "sub_zone": s.machine.bk_sub_zone,
            "cls_name": s.machine.bk_svr_device_cls_name,
        }
        for s in proxy_instances
    ]


def cluster_masters(immute_domain: str) -> List:
    """集群 master节点 列表"""
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    master_objs = c_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)

    master_hosts, master_infos = {}, []
    for ins_obj in master_objs:
        if not master_hosts.get(ins_obj.machine.ip):
            master_hosts[ins_obj.machine.ip] = []
        master_hosts[ins_obj.machine.ip].append(ins_obj.port)

    for ip, ports in master_hosts.items():
        m_obj = Machine.objects.get(ip=ip, bk_cloud_id=c_obj.bk_cloud_id, bk_biz_id=c_obj.bk_biz_id)
        master_infos.append(
            {"ip": ip, "ports": ports, "sub_zone": m_obj.bk_sub_zone, "cls_name": m_obj.bk_svr_device_cls_name}
        )

    return master_infos


def instance_tuple(addr: str) -> List:
    """查找实例的 主从 信息
    1. 可以是主节点, 查slave
    2. 也可以是从节点, 查master"""
    ad = addr.split(":")
    ip, port = ad[0], ad[1]
    machine_objs = Machine.objects.filter(ip=ip)
    instance_tuples = {}
    for m_boj in machine_objs:
        if m_boj.access_layer == AccessLayer.PROXY.value:
            p_obj = ProxyInstance.objects.get(machine_id=m_boj.bk_host_id)
            cluster = p_obj.cluster.get()
            if not instance_tuples.get(cluster.immute_domain):
                instance_tuples[cluster.immute_domain] = []
            instance_tuples[cluster.immute_domain].append([{"proxy": "{}:{}".format(m_boj.ip, p_obj.port)}])
        else:
            inst_obj = StorageInstance.objects.get(machine__ip=ip, port=port)
            for otr in StorageInstanceTuple.objects.filter(ejector=inst_obj):
                cluster = otr.ejector.cluster.get()
                m_obj, s_obj = otr.ejector, otr.receiver
                if not instance_tuples.get(cluster.immute_domain):
                    instance_tuples[cluster.immute_domain] = []
                instance_tuples[cluster.immute_domain].append(
                    {
                        "master": "{}:{}".format(m_boj.ip, m_obj.port),
                        "slave": "{}:{}".format(m_boj.ip, s_obj.port),
                    }
                )
            for otr in StorageInstanceTuple.objects.filter(receiver=inst_obj):
                cluster = otr.receiver.cluster.get()
                m_obj, s_obj = otr.ejector, otr.receiver
                if not instance_tuples.get(cluster.immute_domain):
                    instance_tuples[cluster.immute_domain] = []
                instance_tuples[cluster.immute_domain].append(
                    {
                        "master": "{}:{}".format(m_boj.ip, m_obj.port),
                        "slave": "{}:{}".format(m_boj.ip, s_obj.port),
                    }
                )

    return instance_tuples
