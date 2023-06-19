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
import copy
import logging

from django.db.transaction import atomic

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.api.cluster.tendbha.handler import TenDBHAClusterHandler
from backend.db_meta.api.cluster.tendbsingle.handler import TenDBSingleClusterHandler
from backend.db_meta.api.common import CCApi, del_service_instance
from backend.db_meta.enums import ClusterPhase, InstanceInnerRole, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version

logger = logging.getLogger("flow")


class MySQLDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        """
        @param ticket_data : 单据信息
        @param cluster: 集群信息
        """
        self.ticket_data = ticket_data
        self.cluster = cluster

    def mysql_single_apply(self) -> bool:
        """
        部署mysql单节点版集群，更新db-meta
        支持单台机器属于多个集群录入的场景
        """
        def_resource_spec = {"single": {"id": 0}}
        TenDBSingleClusterHandler.create(
            bk_biz_id=self.ticket_data["bk_biz_id"],
            major_version=self.ticket_data["db_version"],
            ip=self.cluster["new_ip"],
            clusters=self.ticket_data["clusters"],
            db_module_id=self.ticket_data["module"],
            creator=self.ticket_data["created_by"],
            time_zone=self.cluster["time_zone_info"]["time_zone"],
            bk_cloud_id=int(self.ticket_data["bk_cloud_id"]),
            resource_spec=self.ticket_data.get("resource_spec", def_resource_spec),
            region=self.ticket_data["city"],
        )
        return True

    def mysql_ha_apply(self) -> bool:
        # 部署mysql主从版集群，更新cmdb
        def_resource_spec = {"backend": {"id": 0}, "proxy": {"id": 0}}
        cluster_ip_dict = {
            "new_master_ip": self.cluster["new_master_ip"],
            "new_slave_ip": self.cluster["new_slave_ip"],
            "new_proxy_1_ip": self.cluster["new_proxy_1_ip"],
            "new_proxy_2_ip": self.cluster["new_proxy_2_ip"],
        }

        kwargs = {
            "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
            "db_module_id": int(self.ticket_data["module"]),
            "major_version": self.ticket_data["db_version"],
            "cluster_ip_dict": copy.deepcopy(cluster_ip_dict),
            "clusters": self.ticket_data["clusters"],
            "creator": self.ticket_data["created_by"],
            "time_zone": self.cluster["time_zone_info"]["time_zone"],
            "bk_cloud_id": int(self.ticket_data["bk_cloud_id"]),
            "resource_spec": self.ticket_data.get("resource_spec", def_resource_spec),
            "region": self.ticket_data["city"],
        }
        TenDBHAClusterHandler.create(**kwargs)
        return True

    def mysql_single_destroy(self) -> bool:
        """
        下架mysql单节点版集群，删除元信息
        """
        TenDBSingleClusterHandler(
            bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.cluster["id"]
        ).decommission()
        return True

    def mysql_ha_destroy(self) -> bool:
        """
        下架mysql主从版集群，删除元信息
        """
        TenDBHAClusterHandler(bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.cluster["id"]).decommission()
        return True

    def mysql_proxy_add(self) -> bool:
        """
        添加proxy节点，添加相关元信息
        """

        machines = [
            {
                "ip": self.cluster["proxy_ip"]["ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": MachineType.PROXY.value,
            },
        ]

        proxies = []
        for proxy_port in self.ticket_data["proxy_ports"]:
            proxies.append({"ip": self.cluster["proxy_ip"]["ip"], "port": proxy_port})

        with atomic():
            # 绑定事务更新cmdb
            # TODO 统一到CLusterHandler处理
            api.machine.create(
                machines=machines,
                creator=self.ticket_data["created_by"],
                bk_cloud_id=self.cluster["proxy_ip"]["bk_cloud_id"],
            )
            api.proxy_instance.create(proxies=proxies, creator=self.ticket_data["created_by"])
            api.cluster.tendbha.add_proxy(
                cluster_ids=self.cluster["cluster_ids"],
                proxy_ip=self.cluster["proxy_ip"]["ip"],
                bk_cloud_id=self.cluster["proxy_ip"]["bk_cloud_id"],
            )

        return True

    def mysql_proxy_switch(self):
        """
        替换proxy节点，处理相关元信息
        """

        machines = [
            {
                "ip": self.cluster["target_proxy_ip"]["ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": MachineType.PROXY.value,
            },
        ]

        proxies = []
        for proxy_port in self.ticket_data["proxy_ports"]:
            proxies.append({"ip": self.cluster["target_proxy_ip"]["ip"], "port": proxy_port})

        with atomic():
            # 绑定事务更新cmdb
            # TODO 统一到CLusterHandler处理
            api.machine.create(
                machines=machines,
                creator=self.ticket_data["created_by"],
                bk_cloud_id=self.cluster["target_proxy_ip"]["bk_cloud_id"],
            )
            api.proxy_instance.create(proxies=proxies, creator=self.ticket_data["created_by"])
            api.cluster.tendbha.switch_proxy(
                cluster_ids=self.cluster["cluster_ids"],
                target_proxy_ip=self.cluster["target_proxy_ip"]["ip"],
                origin_proxy_ip=self.cluster["origin_proxy_ip"]["ip"],
                bk_cloud_id=self.cluster["target_proxy_ip"]["bk_cloud_id"],
            )

        return True

    def mysql_restore_slave_add_instance(self):
        """
        SLAVE 重建处理元数据步骤之一：添加新建实例信息到集群(定点回滚也用此)
        """
        mysql_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
        )
        machines = [
            {
                "ip": self.cluster["new_slave_ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": MachineType.BACKEND.value,
            },
        ]
        storage_instances = []
        for storage_port in self.cluster["cluster_ports"]:
            storage_instances.append(
                {
                    "ip": self.cluster["new_slave_ip"],
                    "port": int(storage_port),
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "is_stand_by": False,  # 添加新建
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                }
            )
        cluster_list = []
        clusterid_list = []
        for one_cluster in self.cluster["clusters"]:
            cluster_list.append(
                {
                    "ip": self.cluster["new_slave_ip"],
                    "port": int(one_cluster["mysql_port"]),
                    "cluster_id": one_cluster["cluster_id"],
                }
            )
            clusterid_list.append(one_cluster["cluster_id"])

        with atomic():
            api.machine.create(
                bk_cloud_id=self.cluster["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(
                instances=storage_instances,
                creator=self.ticket_data["created_by"],
                time_zone=self.cluster["time_zone"],
                status=InstanceStatus.RESTORING.value,
            )
            # 新建的实例处于游离态，关联到每个相对应的集群ID。
            api.cluster.tendbha.cluster_add_storage(cluster_list)
            # ip转移模块，ip底下关联的每个实例注册到服务(即可监控)
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"],
                cluster_ids=clusterid_list,
                machines=[self.cluster["new_slave_ip"]],
            )

        return True

    def mysql_add_slave_info(self):
        """
        SLAVE 重建处理元数据步骤之二: 数据同步完毕后，添加临时主从关系,(不注册域名)。仅添加从库的流程用此元数据修改函数
        """
        with atomic():
            api.cluster.tendbha.add_slave(
                cluster_id=self.cluster["cluster_id"], target_slave_ip=self.cluster["new_slave_ip"]
            )
            api.cluster.tendbha.add_storage_tuple(
                master_ip=self.cluster["master_ip"],
                slave_ip=self.cluster["new_slave_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=[self.cluster["master_port"]],
            )
            # 修改新slave实例状态: restoring->running
            slave_storage = StorageInstance.objects.get(
                machine__ip=self.cluster["new_slave_ip"],
                machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                port=self.cluster["master_port"],
            )
            slave_storage.status = InstanceStatus.RUNNING.value
            slave_storage.save()

    def mysql_restore_slave_change_cluster_info(self):
        """
        SLAVE 重建处理元数据步骤之三：切换实例，修改集群从节点域名指向新从节点
        """
        with atomic():
            api.cluster.tendbha.switch_slave(
                cluster_id=self.cluster["cluster_id"],
                target_slave_ip=self.cluster["new_slave_ip"],
                source_slave_ip=self.cluster["old_slave_ip"],
                slave_domain=self.cluster["slave_domain"],
            )

    def mysql_restore_remove_old_slave(self):
        """
        SLAVE 重建处理元数据步骤之四：卸载实例，删除旧实例节点。删除完毕检查机器下是否存在实力，不存在则转移就ip到空闲模块
        卸载完毕才处理old_slave的元数据更合理
        """
        with atomic():
            # 删除实例记录的主从关系
            api.cluster.tendbha.remove_storage_tuple(
                master_ip=self.cluster["master_ip"],
                slave_ip=self.cluster["old_slave_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=[self.cluster["master_port"]],
            )
            # 删除实例与集群关联信息
            api.cluster.tendbha.remove_slave(
                cluster_id=self.cluster["cluster_id"], target_slave_ip=self.cluster["old_slave_ip"]
            )
            # 删除实例ID注册服。
            bk_instance_id = StorageInstance.objects.get(
                machine__ip=self.cluster["old_slave_ip"], port=self.cluster["master_port"]
            ).bk_instance_id
            del_service_instance(bk_instance_id=bk_instance_id)

            # 删除实例元数据信息
            api.storage_instance.delete(
                [
                    {
                        "ip": self.cluster["old_slave_ip"],
                        "port": self.cluster["master_port"],
                        "bk_cloud_id": self.cluster["bk_cloud_id"],
                    }
                ]
            )

        if not StorageInstance.objects.filter(machine__ip=self.cluster["old_slave_ip"]).exists():
            # 机器转移模块到空闲模块，转移到空闲模块 实例ID的服务会自动注销。
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"], machines=[self.cluster["old_slave_ip"]], idle=True
            )
            api.machine.delete([self.cluster["old_slave_ip"]], bk_cloud_id=self.cluster["bk_cloud_id"])

    def machine_single_create(self):
        """
        定义machine录入的方法
        传入的ip可以暂时通过cluster变量的结构体来提供，
        todo 方法废弃，后续去除
        """
        api.machine.create(
            machines=[
                {
                    "ip": self.cluster["ip"],
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "machine_type": MachineType.SINGLE.value,
                }
            ],
            creator=self.ticket_data["created_by"],
        )
        return True

    def mysql_migrate_cluster_add_instance(self):
        """
        集群成对迁移之一：安装新节点，添加实例元数据，关联到集群，转移机器模块
        """
        mysql_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
        )

        machines = [
            {
                "ip": self.cluster["new_master_ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": MachineType.BACKEND.value,
            },
            {
                "ip": self.cluster["new_slave_ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": MachineType.BACKEND.value,
            },
        ]
        storage_instances = []
        for storage_port in self.cluster["cluster_ports"]:
            storage_instances.append(
                {
                    "ip": self.cluster["new_master_ip"],
                    "port": int(storage_port),
                    "instance_role": InstanceRole.BACKEND_REPEATER.value,
                    "is_stand_by": False,  # 添加新建
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                }
            )
            storage_instances.append(
                {
                    "ip": self.cluster["new_slave_ip"],
                    "port": int(storage_port),
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "is_stand_by": False,  # 添加新建
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                }
            )

        cluster_list = []
        clusterid_list = []
        for one_cluster in self.cluster["clusters"]:
            cluster_list.append(
                {
                    "ip": self.cluster["new_slave_ip"],
                    "port": int(one_cluster["mysql_port"]),
                    "cluster_id": one_cluster["cluster_id"],
                }
            )
            cluster_list.append(
                {
                    "ip": self.cluster["new_master_ip"],
                    "port": int(one_cluster["mysql_port"]),
                    "cluster_id": one_cluster["cluster_id"],
                }
            )
            clusterid_list.append(one_cluster["cluster_id"])

        with atomic():
            api.machine.create(
                bk_cloud_id=self.cluster["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(
                instances=storage_instances,
                creator=self.ticket_data["created_by"],
                time_zone=self.cluster["time_zone"],
                status=InstanceStatus.RESTORING,
            )
            api.cluster.tendbha.cluster_add_storage(cluster_list)
            # 转移模块，实例ID注册服务
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"],
                cluster_ids=clusterid_list,
                machines=[self.cluster["new_master_ip"], self.cluster["new_slave_ip"]],
            )
            api.cluster.tendbha.add_storage_tuple(
                master_ip=self.cluster["new_master_ip"],
                slave_ip=self.cluster["new_slave_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=self.cluster["cluster_ports"],
            )
        return True

    def mysql_ha_switch(self):
        """
        定义整机维度去切换后变更对应集群的元数据的方法
        变更内容：slave和master 角色对换、域名映射关系对换
        """
        slave_ip = self.cluster["slave_ip"]["ip"]
        master_ip = self.cluster["master_ip"]["ip"]
        with atomic():
            for cluster_id in self.cluster["cluster_ids"]:

                cluster = Cluster.objects.get(id=cluster_id)
                cluster_storage_port = StorageInstance.objects.filter(cluster=cluster).all()[0].port
                slave_storage_objs = StorageInstance.objects.get(machine__ip=slave_ip, port=cluster_storage_port)
                master_storage_objs = StorageInstance.objects.get(machine__ip=master_ip, port=cluster_storage_port)
                other_slave_info = (
                    StorageInstance.objects.filter(cluster=cluster, instance_inner_role=InstanceInnerRole.SLAVE)
                    .exclude(machine__ip=slave_ip)
                    .all()
                )

                # 对换主从实例的角色信息
                slave_storage_objs.instance_role = InstanceRole.BACKEND_MASTER
                slave_storage_objs.instance_inner_role = InstanceInnerRole.MASTER
                slave_storage_objs.save(update_fields=["instance_role", "instance_inner_role"])

                master_storage_objs.instance_role = InstanceRole.BACKEND_SLAVE
                master_storage_objs.instance_inner_role = InstanceInnerRole.SLAVE
                master_storage_objs.save(update_fields=["instance_role", "instance_inner_role"])

                # 修改db-meta主从的映射关系
                StorageInstanceTuple.objects.filter(ejector=master_storage_objs, receiver=slave_storage_objs).update(
                    ejector=slave_storage_objs, receiver=master_storage_objs
                )

                # 其他slave修复对应的映射关系
                if other_slave_info:
                    for other_slave in other_slave_info:
                        StorageInstanceTuple.objects.filter(receiver=other_slave).update(ejector=slave_storage_objs)

                # 更新集群从域名的最新映射关系
                slave_entry_list = slave_storage_objs.bind_entry.all()
                for slave_entry in slave_entry_list:
                    slave_entry.storageinstance_set.remove(slave_storage_objs)
                    slave_entry.storageinstance_set.add(master_storage_objs)

                # 更新集群的proxy-master 的最新映射关系
                proxy_list = master_storage_objs.proxyinstance_set.all()
                for proxy in proxy_list:
                    proxy.storageinstance.remove(master_storage_objs)
                    proxy.storageinstance.add(slave_storage_objs)

                # 切换新master服务实例角色标签
                CCApi.add_label_for_service_instance(
                    {
                        "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                        "instance_ids": [slave_storage_objs.bk_instance_id],
                        "labels": {"instance_role": InstanceRole.BACKEND_MASTER.value},
                    }
                )

                # 切换新slave服务实例角色标签
                CCApi.add_label_for_service_instance(
                    {
                        "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                        "instance_ids": [master_storage_objs.bk_instance_id],
                        "labels": {"instance_role": InstanceRole.BACKEND_SLAVE.value},
                    }
                )

    def mysql_cluster_offline(self):
        """
        定义更新cluster集群的为offline 状态
        """
        Cluster.objects.filter(id=self.cluster["id"]).update(phase=ClusterPhase.OFFLINE)

    def mysql_cluster_online(self):
        """
        定义更新cluster集群的为online 状态
        """
        Cluster.objects.filter(id=self.cluster["id"]).update(phase=ClusterPhase.ONLINE)

    def mysql_migrate_cluster_switch_storage(self):
        """
        集群成对迁移之三：切换到新实例。修改集群对应的实例，
        """
        with atomic():

            # 先修改映射关系
            api.cluster.tendbha.change_proxy_storage_entry(
                cluster_id=self.cluster["cluster_id"],
                master_ip=self.cluster["old_master_ip"],
                new_master_ip=self.cluster["new_master_ip"],
            )
            api.cluster.tendbha.change_storage_cluster_entry(
                cluster_id=self.cluster["cluster_id"],
                slave_ip=self.cluster["old_slave_ip"],
                new_slave_ip=self.cluster["new_slave_ip"],
            )

            # 再移除旧节点
            api.cluster.tendbha.switch_storage(
                cluster_id=self.cluster["cluster_id"],
                target_storage_ip=self.cluster["new_master_ip"],
                origin_storage_ip=self.cluster["old_master_ip"],
                # 切换后从 REPEATER 转为 MASTER
                role=InstanceRole.BACKEND_MASTER.value,
            )
            api.cluster.tendbha.switch_storage(
                cluster_id=self.cluster["cluster_id"],
                target_storage_ip=self.cluster["new_slave_ip"],
                origin_storage_ip=self.cluster["old_slave_ip"],
            )
            # 去除同步关系链相关元数据
            api.cluster.tendbha.storage_tuple.remove_storage_tuple(
                master_ip=self.cluster["old_master_ip"],
                slave_ip=self.cluster["new_master_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=[self.cluster["master_port"]],
            )

    def mysql_migrate_cluster_add_tuple(self):
        """
        集群成对迁移之二：添加 实例主从对应关系
        """
        with atomic():
            api.cluster.tendbha.storage_tuple.add_storage_tuple(
                master_ip=self.cluster["old_master_ip"],
                slave_ip=self.cluster["new_master_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=[self.cluster["master_port"]],
            )

    def mysql_rollback_remove_instance(self):
        """
        rollback_data之二： 定点恢复之卸载恢复实例修改元数据
        """
        with atomic():
            # 先解除集群关系再删除实例
            api.cluster.tendbha.cluster_remove_storage(
                cluster_id=self.cluster["cluster_id"], ip=self.cluster["rollback_ip"], port=self.cluster["master_port"]
            )
            api.storage_instance.delete(
                [
                    {
                        "bk_cloud_id": self.cluster["bk_cloud_id"],
                        "ip": self.cluster["rollback_ip"],
                        "port": self.cluster["master_port"],
                    }
                ]
            )
        if not StorageInstance.objects.filter(
            machine__bk_cloud_id=self.cluster["bk_cloud_id"], machine__ip=self.cluster["rollback_ip"]
        ).exists():
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"], machines=[self.cluster["rollback_ip"]], idle=True
            )
            api.machine.delete([self.cluster["rollback_ip"]], bk_cloud_id=self.cluster["bk_cloud_id"])

    def mysql_cluster_migrate_remote_instance(self):
        """
        成对迁移处理元数据步骤之四：卸载实例，删除旧实例节点。删除完毕检查机器下是否存在实例，不存在则转移就ip到空闲模块
        """
        with atomic():
            # 删除实例记录的主从关系
            api.cluster.tendbha.remove_storage_tuple(
                master_ip=self.cluster["master_ip"],
                slave_ip=self.cluster["old_slave_ip"],
                bk_cloud_id=self.cluster["bk_cloud_id"],
                port_list=[self.cluster["backend_port"]],
            )
            # 删除实例ID注册服。
            bk_instance_id = StorageInstance.objects.get(
                machine__ip=self.cluster["old_slave_ip"], port=self.cluster["backend_port"]
            ).bk_instance_id
            del_service_instance(bk_instance_id=bk_instance_id)
            bk_instance_id = StorageInstance.objects.get(
                machine__ip=self.cluster["master_ip"], port=self.cluster["backend_port"]
            ).bk_instance_id
            del_service_instance(bk_instance_id=bk_instance_id)
            # 删除实例元数据信息
            api.storage_instance.delete(
                [
                    {
                        "ip": self.cluster["old_slave_ip"],
                        "port": self.cluster["backend_port"],
                        "bk_cloud_id": self.cluster["bk_cloud_id"],
                    },
                    {
                        "ip": self.cluster["master_ip"],
                        "port": self.cluster["backend_port"],
                        "bk_cloud_id": self.cluster["bk_cloud_id"],
                    },
                ]
            )

        if not StorageInstance.objects.filter(machine__ip=self.cluster["old_slave_ip"]).exists():
            # 机器转移模块到空闲模块，转移到空闲模块 实例ID的服务会自动注销。
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"],
                cluster_ids=[self.cluster["cluster_id"]],
                machines=[self.cluster["old_slave_ip"]],
                idle=True,
            )
            api.machine.delete([self.cluster["old_slave_ip"]], bk_cloud_id=self.cluster["bk_cloud_id"])

        if not StorageInstance.objects.filter(machine__ip=self.cluster["master_ip"]).exists():
            api.machine.trans_module(
                bk_cloud_id=self.cluster["bk_cloud_id"],
                cluster_ids=[self.cluster["cluster_id"]],
                machines=[self.cluster["master_ip"]],
                idle=True,
            )
            api.machine.delete([self.cluster["master_ip"]], bk_cloud_id=self.cluster["bk_cloud_id"])
