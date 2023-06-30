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

from django.db.transaction import atomic

from backend.db_meta import api
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import LevelInfoEnum, PulsarRoleEnum
from backend.flow.utils.pulsar.consts import PULSAR_BOOKKEEPER_SERVICE_PORT, PULSAR_ZOOKEEPER_SERVICE_PORT

logger = logging.getLogger("flow")


class PulsarDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    规定：
    Machine:
        access_layer:          storage
    StorageInstance:
        access_layer:          storage
        machine_type:          zookeeper/broker/bookkeeper
        instance_role:         zookeeper/broker/bookkeeper
        instance_inner_role:   orphan
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.role_machine_dict = {
            PulsarRoleEnum.ZooKeeper.value: MachineType.PULSAR_ZOOKEEPER.value,
            PulsarRoleEnum.BookKeeper.value: MachineType.PULSAR_BOOKKEEPER.value,
            PulsarRoleEnum.Broker.value: MachineType.PULSAR_BROKER.value,
        }
        self.role_instance_dict = {
            PulsarRoleEnum.ZooKeeper.value: InstanceRole.PULSAR_ZOOKEEPER.value,
            PulsarRoleEnum.BookKeeper.value: InstanceRole.PULSAR_BOOKKEEPER.value,
            PulsarRoleEnum.Broker.value: InstanceRole.PULSAR_BROKER.value,
        }
        self.role_port_dict = {
            PulsarRoleEnum.ZooKeeper.value: PULSAR_ZOOKEEPER_SERVICE_PORT,
            PulsarRoleEnum.BookKeeper.value: PULSAR_BOOKKEEPER_SERVICE_PORT,
            PulsarRoleEnum.Broker.value: self.ticket_data["port"],
        }

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return [node["ip"] for node in self.ticket_data["nodes"][role]]

    def __generate_machine(self) -> list:
        machines = []
        for role in PulsarRoleEnum:
            for ip in self.__get_node_ips_by_role(role):
                machine = {
                    "ip": ip,
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "machine_type": self.role_machine_dict[role],
                }
                if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                    machine.update(
                        {
                            "spec_id": self.ticket_data["resource_spec"][role]["id"],
                            "spec_config": self.ticket_data["resource_spec"][role],
                        }
                    )
                machines.append(machine)
        return machines

    def __generate_storage_instance(self) -> list:
        instances = []
        for role in PulsarRoleEnum:
            for ip in self.__get_node_ips_by_role(role):
                instances.append(
                    {
                        "ip": ip,
                        "port": self.role_port_dict[role],
                        "instance_role": self.role_instance_dict[role],
                    }
                )

        return instances

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(f"Not found function {function_name}，please contact administrator")
        return False

    def pulsar_apply(self) -> bool:
        # 部署pulsar，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()
        cluster = {
            "bk_cloud_id": self.ticket_data["bk_cloud_id"],
            "bk_biz_id": self.ticket_data["bk_biz_id"],
            "name": self.ticket_data["cluster_name"],
            "alias": self.ticket_data["cluster_alias"],
            "immute_domain": self.ticket_data["domain"],
            "db_module_id": int(LevelInfoEnum.TendataModuleDefault),
            "storages": storage_instances,
            "creator": self.ticket_data["created_by"],
            "major_version": self.ticket_data["db_version"],
        }
        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.pulsar.create(**cluster)

        return True

    def pulsar_scale_up(self) -> bool:
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()

        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.pulsar.scale_up(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
        return True

    def pulsar_destroy(self) -> bool:
        api.cluster.pulsar.destroy(self.ticket_data["cluster_id"])
        return True

    def pulsar_disable(self) -> bool:
        api.cluster.pulsar.disable(self.ticket_data["cluster_id"])
        return True

    def pulsar_enable(self) -> bool:
        api.cluster.pulsar.enable(self.ticket_data["cluster_id"])
        return True

    def pulsar_shrink(self) -> bool:
        storage_instances = self.__generate_storage_instance()
        api.cluster.pulsar.shrink(
            cluster_id=self.ticket_data["cluster_id"],
            storages=storage_instances,
        )
        return True

    # only affect replace zookeeper
    def pulsar_replace(self) -> bool:
        old_storages = []
        new_storages = []
        for i in range(len(self.ticket_data["old_zk_ips"])):
            old_storages.append(
                {
                    "ip": self.ticket_data["old_zk_ips"][i],
                    "port": self.role_port_dict[PulsarRoleEnum.ZooKeeper],
                    "instance_role": self.role_instance_dict[PulsarRoleEnum.ZooKeeper],
                }
            )
            new_storages.append(
                {
                    "ip": self.ticket_data["new_zk_ips"][i],
                    "port": self.role_port_dict[PulsarRoleEnum.ZooKeeper],
                    "instance_role": self.role_instance_dict[PulsarRoleEnum.ZooKeeper],
                }
            )
        new_machines = []
        for ip in self.ticket_data["new_zk_ips"]:
            machine = {
                "ip": ip,
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": self.role_machine_dict[PulsarRoleEnum.ZooKeeper.value],
            }
            if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                machine.update(
                    {
                        "spec_id": self.ticket_data["resource_spec"][PulsarRoleEnum.ZooKeeper.value]["id"],
                        "spec_config": self.ticket_data["resource_spec"][PulsarRoleEnum.ZooKeeper.value],
                    }
                )
            new_machines.append(machine)
        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"],
                machines=new_machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=new_storages, creator=self.ticket_data["created_by"])
            api.cluster.pulsar.replace(
                cluster_id=self.ticket_data["cluster_id"], old_storages=old_storages, new_storages=new_storages
            )

        return True
