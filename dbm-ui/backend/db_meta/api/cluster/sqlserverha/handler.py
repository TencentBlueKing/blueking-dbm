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

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance, StorageInstanceTuple
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator
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
                    major_version=major_version,
                    region=region,
                    sync_type=sync_type,
                )
            )

        # 主机转移模块、添加对应的服务实例
        SqlserverCCTopoOperator(new_clusters).transfer_instances_to_cluster_module(storage_objs)

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群,ha下架逻辑于single一致，直接复用"""
        api.cluster.sqlserversingle.decommission(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        pass

    @classmethod
    @transaction.atomic
    def switch_role(cls, cluster_ids: list, old_master: Host, new_master: Host):
        """
        切换元信息，已机器维度去变更，关联的cluster都要处理
        @param cluster_ids: 关联的cluster_id 列表
        @param old_master: 旧的master机器
        @param new_master: 新的master机器
        """
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
                    StorageInstanceTuple.objects.filter(receiver=other_slave).update(ejector=new_master_storage_objs)

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

    @classmethod
    @transaction.atomic
    def cluster_reset(
        cls,
        cluster_id: int,
        new_cluster_name: str,
        new_immutable_domain: str,
        creator: str,
        new_slave_domain: str = None,
    ):
        """
        集群重置元数据，作为原子性处理
        @param cluster_id: 集群id
        @param new_cluster_name: 新集群名称
        @param new_immutable_domain: 新的集群主域名
        @param new_slave_domain: 新的集群从域名
        @param creator: 操作者
        """
        # 获取集群相关信息
        cluster = Cluster.objects.get(id=cluster_id)
        master = cluster.storageinstance_set.get(is_stand_by=True, instance_role=InstanceRole.BACKEND_MASTER)
        standby_slave = cluster.storageinstance_set.get(is_stand_by=True, instance_role=InstanceRole.BACKEND_SLAVE)
        slaves = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)

        # 更新集群状态
        cluster.phase = ClusterPhase.ONLINE
        cluster.name = new_cluster_name
        cluster.immute_domain = new_immutable_domain
        cluster.save()

        # 更新域名信息
        ClusterEntry.objects.filter(cluster=cluster).delete()
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=new_immutable_domain, creator=creator
        )
        cluster_entry.storageinstance_set.add(master)

        if new_slave_domain:
            cluster_slave_entry = ClusterEntry.objects.create(
                cluster=cluster,
                cluster_entry_type=ClusterEntryType.DNS,
                entry=new_slave_domain,
                creator=creator,
                role=ClusterEntryRole.SLAVE_ENTRY.value,
            )
            cluster_slave_entry.storageinstance_set.add(standby_slave)

        cc_manage = CcManage(cluster.bk_biz_id)
        # 更新master服务实例标签
        cc_manage.add_label_for_service_instance(
            bk_instance_ids=[master.bk_instance_id],
            labels_dict={"cluster_domain": new_immutable_domain, "cluster_name": new_cluster_name},
        )

        # 更新所有slave服务实例标签
        for slave in slaves:
            cc_manage.add_label_for_service_instance(
                bk_instance_ids=[slave.bk_instance_id],
                labels_dict={"cluster_domain": new_immutable_domain, "cluster_name": new_cluster_name},
            )

    @classmethod
    @transaction.atomic
    def switch_slave(
        cls,
        bk_biz_id: int,
        cluster_ids: list,
        old_slave_host: Host,
        new_slave_host: Host,
        resource_spec: dict,
        creator: str,
    ):
        """
        slave 新机重建后元数据更改
        @param bk_biz_id: 业务id
        @param cluster_ids: 关联的集群id列表
        @param old_slave_host: 旧的slave机器信息
        @param new_slave_host: 新的slave机器信息
        @param resource_spec: 新机器规格信息
        @param creator: 操作者
        """

        # 录入新机器的machine信息
        api.machine.create(
            machines=[
                {
                    "ip": new_slave_host.ip,
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.SQLSERVER_HA.value,
                    "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                    "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
                },
            ],
            creator=creator,
            bk_cloud_id=new_slave_host.bk_cloud_id,
        )

        for cluster_id in cluster_ids:
            # 每个集群维度遍历变更信息
            cluster = Cluster.objects.get(id=cluster_id)
            cc_manage = CcManage(cluster.bk_biz_id)
            old_slave_obj = cluster.storageinstance_set.get(machine__ip=old_slave_host.ip)

            storages = [
                {
                    "ip": new_slave_host.ip,
                    "port": old_slave_obj.port,
                    "instance_role": old_slave_obj.instance_role,
                    "is_stand_by": old_slave_obj.is_stand_by,  # 标记实例属于切换组实例
                    "db_version": cluster.major_version,
                }
            ]
            # 建立集群对应的实例信息
            new_slave_obj = api.storage_instance.create(
                instances=storages, creator=creator, time_zone=old_slave_obj.time_zone
            )[0]
            new_slave_obj.db_module_id = cluster.db_module_id
            new_slave_obj.machine.db_module_id = cluster.db_module_id
            new_slave_obj.save(update_fields=["db_module_id"])
            new_slave_obj.machine.save(update_fields=["db_module_id"])

            # 添加对应cmdb服务实例信息
            MysqlCCTopoOperator(cluster).transfer_instances_to_cluster_module([new_slave_obj])

            # 替换关联的主从关系信息
            StorageInstanceTuple.objects.filter(receiver=old_slave_obj).update(receiver=new_slave_obj)

            # 替换域名关联信息
            entry_list = old_slave_obj.bind_entry.all()
            for entry in entry_list:
                entry.storageinstance_set.remove(old_slave_obj)
                entry.storageinstance_set.add(new_slave_obj)

            # 删除旧实例信息
            cc_manage.delete_service_instance(bk_instance_ids=[old_slave_obj.bk_instance_id])
            old_slave_obj.delete(keep_parents=True)

            if not old_slave_obj.machine.storageinstance_set.exists():
                # 转移主机到待回收
                cc_manage.recycle_host([old_slave_obj.machine.bk_host_id])
                # 删除主机信息
                old_slave_obj.machine.delete(keep_parents=True)

    @classmethod
    @transaction.atomic
    def add_slave(
        cls,
        bk_biz_id: int,
        cluster_ids: list,
        new_slave_host: Host,
        resource_spec: dict,
        creator: str,
        is_stand_by: bool = False,
    ):
        """
        slave 添加元数据更改
        @param bk_biz_id: 业务id
        @param cluster_ids: 关联的集群id列表
        @param new_slave_host: 新的slave机器信息
        @param resource_spec: 新机器规格信息
        @param creator: 操作者
        @param is_stand_by: 是否作为互切备机
        """

        # 录入新机器的machine信息
        api.machine.create(
            machines=[
                {
                    "ip": new_slave_host.ip,
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.SQLSERVER_HA.value,
                    "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                    "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
                },
            ],
            creator=creator,
            bk_cloud_id=new_slave_host.bk_cloud_id,
        )

        for cluster_id in cluster_ids:
            # 每个集群维度遍历变更信息
            cluster = Cluster.objects.get(id=cluster_id)

            storages = [
                {
                    "ip": new_slave_host.ip,
                    "port": cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER).port,
                    "instance_role": InstanceRole.BACKEND_SLAVE,
                    "is_stand_by": is_stand_by,
                    "db_version": cluster.major_version,
                }
            ]
            # 建立集群对应的实例信息
            new_slave_obj = api.storage_instance.create(
                instances=storages, creator=creator, time_zone=cluster.time_zone
            )[0]
            new_slave_obj.db_module_id = cluster.db_module_id
            new_slave_obj.machine.db_module_id = cluster.db_module_id
            new_slave_obj.save(update_fields=["db_module_id"])
            new_slave_obj.machine.save(update_fields=["db_module_id"])

            # 添加对应cmdb服务实例信息
            MysqlCCTopoOperator(cluster).transfer_instances_to_cluster_module([new_slave_obj])
