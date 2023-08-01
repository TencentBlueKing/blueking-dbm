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
from django.db import transaction

from backend.configuration.constants import DBType
from backend.db_meta import api, request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple, TenDBClusterStorageSet
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator


class TenDBClusterMigrateRemoteDb:
    cluster_type = ClusterType.TenDBCluster

    @classmethod
    @transaction.atomic
    def storage_create(
        cls,
        cluster_id: int,
        master_ip: str,
        slave_ip: str,
        ports: list,
        creator: str,
        mysql_version: str,
        resource_spec: dict,
    ):
        """主从成对迁移初始化机器写入元数据"""
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        bk_biz_id = cluster.bk_biz_id
        time_zone = cluster.time_zone
        mysql_pkg = Package.get_latest_package(version=mysql_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        machines = [
            {
                "ip": master_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.REMOTE.value,
                "spec_id": resource_spec[MachineType.REMOTE.value]["id"],
                "spec_config": resource_spec[MachineType.REMOTE.value],
            },
            {
                "ip": slave_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.REMOTE.value,
                "spec_id": resource_spec[MachineType.REMOTE.value]["id"],
                "spec_config": resource_spec[MachineType.REMOTE.value],
            },
        ]
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)
        storages = []
        for port in ports:
            storages.append(
                {
                    "ip": master_ip,
                    "port": port,
                    "instance_role": InstanceRole.REMOTE_MASTER.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
            )
            storages.append(
                {
                    "ip": slave_ip,
                    "port": port,
                    "instance_role": InstanceRole.REMOTE_SLAVE.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
            )
        api.storage_instance.create(
            instances=storages, creator=creator, time_zone=time_zone, status=InstanceStatus.RESTORING
        )
        # cluster映射关系
        storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
        storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
        cluster.storageinstance_set.add(*storage_objs)
        #  转移模块
        cc_topo_operator = MysqlCCTopoOperator(cluster)
        cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)


    @classmethod
    @transaction.atomic
    def switch_remote_node(cls, cluster_id: int, source: dict, target: dict):
        """
        remotedb 分片切换
        source:{master:{ip:xx,port:xx},slave:"ip:xx,port:xx"}
        修正storage的状态>映射分片
        """
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        # bk_biz_id = cluster.bk_biz_id
        source_master_obj = StorageInstance.objects.get(
            machine__ip=source["master"]["ip"], port=source["master"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        source_slave_obj = StorageInstance.objects.get(
            machine__ip=source["slave"]["ip"], port=source["slave"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        target_master_obj = StorageInstance.objects.get(
            machine__ip=target["master"]["ip"], port=target["master"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        target_slave_obj = StorageInstance.objects.get(
            machine__ip=target["slave"]["ip"], port=target["slave"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        target_master_obj.status = InstanceStatus.RUNNING
        target_slave_obj.status = InstanceStatus.RUNNING
        target_master_obj.instance_role = InstanceRole.REMOTE_MASTER
        target_slave_obj.instance_role = InstanceRole.REMOTE_SLAVE
        target_master_obj.save()
        target_slave_obj.save()
        source_tuple = StorageInstanceTuple.objects.get(ejector=source_master_obj, receiver=source_slave_obj)
        target_tuple = StorageInstanceTuple.objects.get(ejector=target_master_obj, receiver=target_slave_obj)
        # 删除原本shard 新增shard
        storage_shard = TenDBClusterStorageSet.objects.get(
            cluster_id=cluster_id, storage_instance_tuple_id=source_tuple
        )
        storage_shard.storage_instance_tuple = target_tuple
        storage_shard.save()
        # storage_shard.delete()
        # TenDBClusterStorageSet.objects.create(
        #     storage_instance_tuple=target_tuple, shard_id=storage_shard.shard_key, cluster=cluster
        # )

    @classmethod
    @transaction.atomic
    def add_storage_tuple(cls, cluster_id: int, storage: dict):
        """
        添加成对迁移的主从映射关系
        storage:{master:{ip:xx,port:xx},slave:"ip:xx,port:xx"}
        新主库改为 storageinstance 角色为repeater
        """
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        master_obj = StorageInstance.objects.get(
            machine__ip=storage["master"]["ip"], port=storage["master"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        slave_obj = StorageInstance.objects.get(
            machine__ip=storage["slave"]["ip"], port=storage["slave"]["port"], machine__bk_cloud_id=bk_cloud_id
        )
        StorageInstanceTuple.objects.create(ejector=master_obj, receiver=slave_obj)

    @classmethod
    @transaction.atomic
    def uninstall_storage(cls, cluster_id: int, ip: str):
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        cluster.storageinstance_set.remove()
        storage_instances = StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
        for one in storage_instances:
            StorageInstanceTuple.objects.filter(ejector=one.id).delete()
            StorageInstanceTuple.objects.filter(receiver=one.id).delete()
        StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id).delete()
        api.machine.trans_module(bk_cloud_id=bk_cloud_id, cluster_ids=[cluster_id], machines=[ip], idle=True)
        api.machine.delete(bk_cloud_id=bk_cloud_id, machines=[ip])
