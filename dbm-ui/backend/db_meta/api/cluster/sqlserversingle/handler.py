"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List

from django.db import transaction

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceRole,
    MachineType,
)
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.sqlserver_module_operate import SqlserverCCTopoOperator


class SqlserverSingleClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.SqlserverSingle

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        major_version: str,
        ip: str,
        clusters: list,
        db_module_id: int,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
        resource_spec: dict,
        region: str,
        zone_list: list,
        is_increment: bool = False,
    ):
        """
        1: 录入机器信息
        2：录入相关实例信息
        3：录入集群信息
        """
        api.machine.create(
            machines=[
                {
                    "ip": ip,
                    "bk_biz_id": bk_biz_id,
                    "machine_type": MachineType.SQLSERVER_SINGLE.value,
                    "bk_cloud_id": bk_cloud_id,
                    "spec_id": resource_spec[MachineType.SQLSERVER_SINGLE.value]["id"],
                    "spec_config": resource_spec[MachineType.SQLSERVER_SINGLE.value],
                }
            ],
            creator=creator,
            bk_cloud_id=bk_cloud_id,
        )
        new_clusters = []
        new_storage_objs = []
        for cluster in clusters:
            storage = {"ip": ip, "port": cluster["port"]}
            immutable_domain = cluster["immutable_domain"]
            new_storage_objs.extend(
                api.storage_instance.create(
                    instances=[
                        {
                            "ip": ip,
                            "port": cluster["port"],
                            "instance_role": InstanceRole.ORPHAN.value,
                            "bk_cloud_id": bk_cloud_id,
                            "db_version": major_version,
                        }
                    ],
                    creator=creator,
                    time_zone=time_zone,
                )
            )
            api.cluster.sqlserversingle.create_pre_check(bk_biz_id, cluster["name"], immutable_domain, db_module_id)
            new_clusters.append(
                api.cluster.sqlserversingle.create(
                    bk_biz_id=bk_biz_id,
                    major_version=major_version,
                    name=cluster["name"],
                    immute_domain=immutable_domain,
                    db_module_id=db_module_id,
                    storage=storage,
                    creator=creator,
                    bk_cloud_id=bk_cloud_id,
                    region=region,
                    zone_list=zone_list,
                )
            )

        # 主机转移模块、添加对应的服务实例
        SqlserverCCTopoOperator(new_clusters).transfer_instances_to_cluster_module(
            instances=new_storage_objs, is_increment=is_increment
        )

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        api.cluster.sqlserversingle.decommission(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        pass

    def get_remote_address(self) -> StorageInstance:
        """查询DRS访问远程数据库的地址"""
        return StorageInstance.objects.get(
            cluster=self.cluster, instance_inner_role=InstanceInnerRole.ORPHAN.value
        ).ip_port

    @classmethod
    @transaction.atomic
    def migrate_cluster(cls, bk_biz_id: int, cluster_ids: List[int], new_host: Host, creator: str):
        """
        单节点集群替换机器
        @param bk_biz_id: 业务id
        @param cluster_ids: 代表同机关联集群ID列表
        @param new_host: 新机器信息
        @param creator: 操作者
        """

        # 录入新机器的machine信息
        api.machine.create(
            machines=[
                {
                    "ip": new_host.ip,
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.SQLSERVER_SINGLE.value,
                    "spec_id": new_host.spec["id"],
                    "spec_config": new_host.spec,
                },
            ],
            creator=creator,
            bk_cloud_id=new_host.bk_cloud_id,
        )

        clusters = []
        new_objs = []
        for cluster_id in cluster_ids:
            # 每个集群维度遍历变更信息
            cluster = Cluster.objects.get(id=cluster_id)
            old_obj = cluster.storageinstance_set.get()

            storages = [
                {
                    "ip": new_host.ip,
                    "port": old_obj.port,
                    "instance_role": InstanceRole.ORPHAN.value,
                    "is_stand_by": True,
                    "db_version": cluster.major_version,
                }
            ]

            # 保存新实例的信息
            new_obj = api.storage_instance.create(instances=storages, creator=creator, time_zone=old_obj.time_zone)[0]
            new_obj.db_module_id = cluster.db_module_id
            new_obj.machine.db_module_id = cluster.db_module_id
            new_obj.save()
            new_obj.machine.save()
            cluster.storageinstance_set.add(new_obj)

            # 切换域名信息
            entry_list = old_obj.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
            for entry in entry_list:
                entry.storageinstance_set.remove(old_obj)
                entry.storageinstance_set.add(new_obj)

            # 旧实例标记为offline状态
            old_obj.phase = InstancePhase.OFFLINE
            old_obj.save()

            # 移除旧机器跟集群的关系
            cluster.storageinstance_set.remove(old_obj)

            new_objs.append(new_obj)
            clusters.append(cluster)

        # 添加对应cmdb服务实例信息
        SqlserverCCTopoOperator(clusters).transfer_instances_to_cluster_module(new_objs, is_increment=False)
