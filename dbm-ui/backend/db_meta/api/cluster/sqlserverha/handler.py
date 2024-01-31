"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import transaction
from django.db.transaction import atomic

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.sqlserver_module_operate import SqlserverCCTopoOperator


class SqlserverHAClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.SqlserverHA

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        db_module_id: int,
        major_version: str,
        master_ip: str,
        slave_ip: str,
        clusters: list,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
        resource_spec: dict,
        region: str,
        sync_type: str,
    ):
        """
        1: 录入机器信息
        2：录入相关实例信息
        3：录入集群信息
        """

        # 录入机器
        machines = [
            {
                "ip": master_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.SQLSERVER_HA.value,
                "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
            },
            {
                "ip": slave_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.SQLSERVER_HA.value,
                "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
            },
        ]
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)

        # 录入机器对应的集群信息
        new_clusters = []
        storage_objs = []

        for cluster in clusters:
            name = cluster["name"]
            immute_domain = cluster["immutable_domain"]
            slave_domain = cluster["slave_domain"]
            storages = [
                {
                    "ip": master_ip,
                    "port": cluster["port"],
                    "instance_role": InstanceRole.BACKEND_MASTER.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": major_version,
                },
                {
                    "ip": slave_ip,
                    "port": cluster["port"],
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": major_version,
                },
            ]

            api.cluster.sqlserverha.create_pre_check(bk_biz_id, name, immute_domain, db_module_id, slave_domain)
            storage_objs.extend(api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone))

            new_clusters.append(
                api.cluster.sqlserverha.create(
                    bk_biz_id=bk_biz_id,
                    name=name,
                    immute_domain=immute_domain,
                    db_module_id=db_module_id,
                    slave_domain=slave_domain,
                    storages=storages,
                    creator=creator,
                    bk_cloud_id=bk_cloud_id,
                    time_zone=time_zone,
                    major_version=major_version,
                    region=region,
                    sync_type=sync_type,
                )
            )

        # 主机转移模块、添加对应的服务实例
        SqlserverCCTopoOperator(new_clusters).transfer_instances_to_cluster_module(storage_objs)

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        pass

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        pass

    @classmethod
    def switch_role(cls, cluster_ids: list, old_master: Host, new_master: Host):
        """
        切换元信息，已机器维度去变更，关联的cluster都要处理
        @param cluster_ids: 关联的cluster_id 列表
        @param old_master: 旧的master机器
        @param new_master: 新的master机器
        """
        with atomic():
            for cluster_id in cluster_ids:
                cluster = Cluster.objects.get(id=cluster_id)
                old_master_storage_objs = cluster.storageinstance_set.get(machine__ip=old_master.ip)
                new_master_storage_objs = cluster.storageinstance_set.get(machine__ip=new_master.ip)
                other_slave_info = (
                    StorageInstance.objects.filter(cluster=cluster, instance_inner_role=InstanceInnerRole.SLAVE)
                    .exclude(machine__ip=new_master.ip)
                    .all()
                )

                # 对换主从实例的角色信息
                new_master_storage_objs.instance_role = InstanceRole.BACKEND_MASTER
                new_master_storage_objs.instance_inner_role = InstanceInnerRole.MASTER
                new_master_storage_objs.save(update_fields=["instance_role", "instance_inner_role"])

                old_master_storage_objs.instance_role = InstanceRole.BACKEND_SLAVE
                old_master_storage_objs.instance_inner_role = InstanceInnerRole.SLAVE
                old_master_storage_objs.save(update_fields=["instance_role", "instance_inner_role"])

                # 修改db-meta主从的映射关系
                StorageInstanceTuple.objects.filter(
                    ejector=old_master_storage_objs, receiver=new_master_storage_objs
                ).update(ejector=new_master_storage_objs, receiver=old_master_storage_objs)

                # 其他slave修复对应的映射关系
                if other_slave_info:
                    for other_slave in other_slave_info:
                        StorageInstanceTuple.objects.filter(receiver=other_slave).update(
                            ejector=new_master_storage_objs
                        )

                # 更新集群从域名的最新映射关系
                master_entry_list = old_master_storage_objs.bind_entry.filter(role=ClusterEntryRole.MASTER_ENTRY).all()
                for master_entry in master_entry_list:
                    master_entry.storageinstance_set.remove(old_master_storage_objs)
                    master_entry.storageinstance_set.add(new_master_storage_objs)

                slave_entry_list = new_master_storage_objs.bind_entry.filter(role=ClusterEntryRole.SLAVE_ENTRY).all()
                for slave_entry in slave_entry_list:
                    slave_entry.storageinstance_set.remove(new_master_storage_objs)
                    slave_entry.storageinstance_set.add(old_master_storage_objs)

                cc_manage = CcManage(cluster.bk_biz_id)
                # 切换新master服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[new_master_storage_objs.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.BACKEND_MASTER.value},
                )

                # 切换新slave服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[old_master_storage_objs.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.BACKEND_SLAVE.value},
                )
