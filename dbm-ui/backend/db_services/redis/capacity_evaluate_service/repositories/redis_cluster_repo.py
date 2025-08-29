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
from abc import abstractmethod
from collections import defaultdict
from typing import Dict, List, Union
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance


class DbmNode:
    """dbm node"""

    def __init__(
        self, ip: str, port: int, role: str, bk_cloud_id: int, mtype: str, version: str = None, domain: str = None
    ):
        self.ip: str = ip
        self.port: int = port
        self.role: str = role
        self.bk_cloud_id: int = bk_cloud_id
        self.machine_type = mtype
        self.version: str = version
        self.domain: str = None  # 这是关联bind_entry.first().entry

    # s is StorageInstance | ProxyInstance
    @classmethod
    def from_instance(cls, s: Union[ProxyInstance, StorageInstance], with_domain: bool = False):
        """from instance to dbm node"""
        meta_role = s.instance_role
        domain = None
        if with_domain:
            domain = s.bind_entry.first().entry
        node = DbmNode(s.ip_port.split(":")[0], s.port, meta_role, s.machine.bk_cloud_id, s.machine_type, domain)
        return node

    def addr(self) -> str:
        """get node address"""
        return "{}:{}".format(self.ip, self.port)

    def equal(self, other: "DbmNode") -> bool:
        """check if two nodes are equal"""
        return self.ip == other.ip and self.port == other.port and self.bk_cloud_id == other.bk_cloud_id

    @classmethod
    def from_conf(cls, conf) -> "DbmNode":
        """from dict"""
        return DbmNode(conf["ip"], int(conf["port"]), conf["role"], int(conf["bk_cloud_id"]), "")

    def __json__(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "role": self.role,
            "bk_cloud_id": self.bk_cloud_id,
            "machine_type": self.machine_type,
            "domain": self.domain,
            "version": self.version,
        }


class TendisClusterBase:
    bk_cloud_id: int
    bk_biz_id: int
    creator: str
    name: str
    app: str
    immute_domain: str
    alias: str
    major_version: str
    region: str
    cluster_type: str
    cluster_id: str
    tags: List[str] = None

    def __init__(
        self,
        bk_cloud_id: int = None,
        cluster_id: str = None,
        name: str = None,
        cluster_type: str = None,
        major_version: str = None,
        bk_biz_id: int = None,
        immute_domain: str = None,
        app: str = None,
        region: str = None,
        tags: List[str] = None,
    ):
        self.cluster_id = cluster_id
        self.name = name
        self.cluster_type = cluster_type
        self.major_version = major_version
        self.bk_biz_id = bk_biz_id
        self.immute_domain = immute_domain
        self.bk_cloud_id = bk_cloud_id
        self.app = app
        self.region = region
        self.tags = tags

    @abstractmethod
    def get_proxy_nodes(self) -> List[DbmNode]:
        pass

    @abstractmethod
    def get_storage_nodes(self) -> List[DbmNode]:
        pass

    def is_memory_cluster(self) -> bool:
        return ClusterType.is_redis_cluster_type(self.cluster_type) and self.cluster_type in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.RedisInstance.value,
        ]

    def is_ssd_cluster(self) -> bool:
        return ClusterType.is_redis_cluster_type(self.cluster_type) and self.cluster_type in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TendisTwemproxyRedisCluster.value,
        ]

    def is_tendis_cluster(self) -> bool:
        return ClusterType.is_redis_cluster_type(self.cluster_type)


class DbmClusterRepository:
    """
    DbmClusterRepository 用于获取dbm集群信息
    1. 获得集群信息
    2. 获得集群里的proxy和storage实例信息
    3. 这里不涉及具体Cluster类型的判断, 只获取集群信息和实例信息.
    """

    def __init__(self):
        pass

    @classmethod
    def get_cluster_by_domain(cls, domain: str) -> Cluster:
        if not domain:
            return None
        if ":" in domain:
            domain = domain.split(":")[0]
        domain = domain.strip()
        cluster = Cluster.objects.get(immute_domain=domain)
        return cluster

    @classmethod
    def get_cluster_by_id(cls, cluster_id: str) -> Cluster:
        """根据集群ID获取集群信息"""
        cluster = Cluster.objects.get(id=cluster_id)
        return cluster

    @classmethod
    def fetch_many_cluster(cls, **kwargs) -> List[Cluster]:
        clusters = Cluster.objects.filter(**kwargs)
        return [cls.get_cluster_by_id(cluster.id) for cluster in clusters]

    @classmethod
    def fetch_many_cluster_dict(cls, **kwargs) -> Dict[str, Cluster]:
        clusters = Cluster.objects.filter(**kwargs)
        return {cluster.id: cls.get_cluster_by_id(cluster.id) for cluster in clusters}

    @classmethod
    def fetch_one_cluster(cls, **kwargs) -> Cluster:
        return cls.fetch_many_cluster(**kwargs)[0]

    @classmethod
    def fetch_ip_instance_count(cls, ip_list: List[str], bk_cloud_id: int) -> Dict[str, int]:
        """查询每个ip的instance数量"""
        print(f"fetch_ip_instance_count: ip_list: {ip_list}, bk_cloud_id: {bk_cloud_id}")
        queryset = ProxyInstance.objects.select_related("machine").filter(
            machine__ip__in=ip_list, machine__bk_cloud_id=bk_cloud_id
        )
        # queryset = Machine.objects.select_related("proxy_instance").filter(ip__in=ip_list, bk_cloud_id=bk_cloud_id)
        print(f"queryset: {queryset.query}")
        ip_instance_count_map = defaultdict(int)
        for machine in queryset.all():
            ip_instance_count_map[machine.machine.ip] += 1

        queryset2 = StorageInstance.objects.select_related("machine").filter(
            machine__ip__in=ip_list, machine__bk_cloud_id=bk_cloud_id
        )
        for machine in queryset2.all():
            ip_instance_count_map[machine.machine.ip] += 1
        return ip_instance_count_map

    @classmethod
    def fetch_proxy_list(cls, bk_biz_id: int, cluster_id: int) -> List:
        """获取proxy实例列表"""
        queryset = ProxyInstance.objects.select_related("machine").filter(bk_biz_id=bk_biz_id, cluster__id=cluster_id)
        instances = []
        for proxy in queryset.all():
            instances.append(
                {
                    "ip": proxy.machine.ip if proxy.machine else None,
                    "port": proxy.port,
                    "role": proxy.instance_role,
                    "bk_cloud_id": proxy.machine.bk_cloud_id,
                    "machine_type": proxy.machine.machine_type,
                    "bk_host_id": proxy.machine.bk_host_id,
                    "bk_biz_id": proxy.bk_biz_id,
                    "instance_role": proxy.instance_role,
                }
            )
        return instances

    @classmethod
    def fetch_storage_list(cls, cluster_id: int, with_shard_name: bool = True) -> List:
        """获取存储实例列表. with_shard_name=True 表示包含seg_range"""
        from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl

        instance_detail_map = {}
        if with_shard_name:
            nosql_details = NosqlStorageSetDtl.objects.filter(cluster_id=cluster_id)
            for detail in nosql_details:
                instance_detail_map[detail.instance.id] = detail
        else:
            pass

        storage_instances = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(cluster__id=cluster_id)
        )

        result = []
        for instance in storage_instances:
            # 从预构建的映射中获取nosql_detail，避免额外查询
            nosql_detail = instance_detail_map.get(instance.id)
            seg_range = nosql_detail.seg_range if nosql_detail else None

            # 获取存储实例信息
            instance_data = {
                "bk_cloud_id": instance.machine.bk_cloud_id if instance.machine else None,
                "machine_type": instance.machine.machine_type if instance.machine else None,
                "id": instance.id,
                "bk_biz_id": instance.bk_biz_id,
                "bk_host_id": instance.machine.bk_host_id if instance.machine else None,
                "ip": instance.machine.ip if instance.machine else None,
                "port": instance.port,
                "instance_role": instance.instance_role,
                "seg_range": seg_range,  # shardName
            }
            result.append(instance_data)

        return result

    @classmethod
    def build_shard_list_by_instance_list(cls, instance_list: List[StorageInstance]) -> List:
        """获取shard列表"""
        shard_list = {}
        for instance in instance_list:
            if instance["seg_range"] is None or instance["seg_range"] == "":
                continue

            shard_name = instance["seg_range"]
            shard_list[shard_name] = {
                "shard_name": shard_name,
                "members": [
                    {
                        "ip": instance["ip"],
                        "port": instance["port"],
                        "bk_cloud_id": instance["bk_cloud_id"],
                        "bk_host_id": instance["bk_host_id"],
                        "machine_type": instance["machine_type"],
                        "instance_role": instance["instance_role"],
                    }
                ],
            }
        # 现在每个分片只包含一个主节点. 以后如果有需要，可以把其它节点也加进来。
        # 节点关系表在 db_meta_storageinstancetuple中.
        # 第一个节点是主节点，其它节点是备节点. 主节点和备节点是多1对多关系。
        return list(shard_list.values())
