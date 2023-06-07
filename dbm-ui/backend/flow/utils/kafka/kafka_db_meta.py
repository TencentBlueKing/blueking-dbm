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
from django.utils.translation import ugettext as _

from backend.db_meta import api
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import DEFAULT_DB_MODULE_ID, KafkaRoleEnum
from backend.flow.utils.kafka.bk_module_operate import create_bk_module_for_cluster_id, transfer_host_in_cluster_module

logger = logging.getLogger("flow")


class KafkaMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.role_machine_dict = {
            "broker": MachineType.BROKER.value,
            "zookeeper": MachineType.ZOOKEEPER.value,
        }
        self.role_instance_dict = {
            "broker": InstanceRole.BROKER.value,
            "zookeeper": InstanceRole.ZOOKEEPER.value,
        }
        self.role_port_dict = {
            "zookeeper": 2181,
            "broker": self.ticket_data["port"],
        }

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return [node["ip"] for node in self.ticket_data["nodes"][role]]

    def __get_node_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return self.ticket_data["nodes"][role]

    def __generate_machine(self) -> list:
        machines = []
        for role in self.role_machine_dict.keys():
            for node in self.__get_node_by_role(role):
                machine = {
                    "ip": node["ip"],
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "machine_type": self.role_machine_dict[role],
                    "bk_cloud_id": node["bk_cloud_id"],
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
        for role in self.role_instance_dict.keys():
            for node in self.__get_node_by_role(role):
                instances.append(
                    {
                        "ip": node["ip"],
                        "port": self.role_port_dict[role],
                        "instance_role": self.role_instance_dict[role],
                        "bk_cloud_id": node["bk_cloud_id"],
                    }
                )
        return instances

    def __generate_new(self) -> (list, list):
        machines = []
        instances = []
        if self.ticket_data["new_nodes"].get("zookeeper"):
            for node in self.ticket_data["new_nodes"]["zookeeper"]:
                machine = {
                    "ip": node["ip"],
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "machine_type": "zookeeper",
                    "bk_cloud_id": node["bk_cloud_id"],
                }
                if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                    machine.update(
                        {
                            "spec_id": self.ticket_data["resource_spec"][KafkaRoleEnum.ZOOKEEPER.value]["id"],
                            "spec_config": self.ticket_data["resource_spec"][KafkaRoleEnum.ZOOKEEPER.value],
                        }
                    )
                machines.append(machine)
                instances.append(
                    {
                        "ip": node["ip"],
                        "port": self.role_port_dict["zookeeper"],
                        "instance_role": "zookeeper",
                        "bk_cloud_id": node["bk_cloud_id"],
                    }
                )
        if self.ticket_data["new_nodes"].get("broker"):
            for node in self.ticket_data["new_nodes"]["broker"]:
                machine = {
                    "ip": node["ip"],
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "machine_type": "broker",
                    "bk_cloud_id": node["bk_cloud_id"],
                }
                if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                    machine.update(
                        {
                            "spec_id": self.ticket_data["resource_spec"][KafkaRoleEnum.BROKER.value]["id"],
                            "spec_config": self.ticket_data["resource_spec"][KafkaRoleEnum.BROKER.value],
                        }
                    )
                machines.append(machine)
                instances.append(
                    {
                        "ip": node["ip"],
                        "port": self.role_port_dict["broker"],
                        "instance_role": "broker",
                        "bk_cloud_id": node["bk_cloud_id"],
                    }
                )
        return machines, instances

    def __generate_old_storage_instance(self) -> list:
        instances = []
        if self.ticket_data["old_nodes"].get("zookeeper"):
            for ip in [node["ip"] for node in self.ticket_data["old_nodes"]["zookeeper"]]:
                instances.append(
                    {
                        "ip": ip,
                        "port": self.role_port_dict["zookeeper"],
                        "instance_role": "zookeeper",
                    }
                )
        if self.ticket_data["old_nodes"].get("broker"):
            for ip in [node["ip"] for node in self.ticket_data["old_nodes"]["broker"]]:
                instances.append(
                    {
                        "ip": ip,
                        "port": self.role_port_dict["broker"],
                        "instance_role": "broker",
                    }
                )
        return instances

    def __get_new_broker_ips(self) -> list:
        if self.ticket_data["new_nodes"].get("broker"):
            return [node["ip"] for node in self.ticket_data["new_nodes"]["broker"]]
        else:
            return []

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()
        else:
            logger.error(_("找不到单据类型需要变更的cmdb函数，请联系系统管理员"))
            return False

    def kafka_apply(self) -> bool:
        # 部署kafka集群，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()
        bk_cloud_id = machines[0]["bk_cloud_id"]
        cluster = {
            "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
            "name": self.ticket_data["cluster_name"],
            "alias": self.ticket_data["cluster_alias"],
            "immute_domain": self.ticket_data["domain"],
            "db_version": self.ticket_data["db_version"],
            "db_module_id": DEFAULT_DB_MODULE_ID,
            "storages": storage_instances,
            "creator": self.ticket_data["created_by"],
            "bk_cloud_id": bk_cloud_id,
        }
        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=bk_cloud_id,
                machines=machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            new_cluster_id = api.cluster.kafka.create(**cluster)
            # 生成模块
            create_bk_module_for_cluster_id(cluster_ids=[new_cluster_id])

            broker_ip_list = self.__get_node_ips_by_role("broker")
            transfer_host_in_cluster_module(
                cluster_ids=[new_cluster_id],
                ip_list=broker_ip_list,
                machine_type=MachineType.BROKER.value,
                bk_cloud_id=bk_cloud_id,
            )

            zookeeper_ip_list = self.__get_node_ips_by_role("zookeeper")
            transfer_host_in_cluster_module(
                cluster_ids=[new_cluster_id],
                ip_list=zookeeper_ip_list,
                machine_type=MachineType.ZOOKEEPER.value,
                bk_cloud_id=bk_cloud_id,
            )

        return True

    def kafka_scale_up(self) -> bool:
        # 扩容kafka集群，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()
        bk_cloud_id = machines[0]["bk_cloud_id"]
        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=bk_cloud_id,
                machines=machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.kafka.scale_up(cluster_id=self.ticket_data["cluster_id"], storages=storage_instances)
            broker_ip_list = self.__get_node_ips_by_role("broker")
            transfer_host_in_cluster_module(
                cluster_ids=[self.ticket_data["cluster_id"]],
                ip_list=broker_ip_list,
                machine_type=MachineType.BROKER.value,
                bk_cloud_id=bk_cloud_id,
            )

        return True

    def kafka_destroy(self) -> bool:
        api.cluster.kafka.destroy(self.ticket_data["cluster_id"])
        return True

    def kafka_disable(self) -> bool:
        api.cluster.kafka.disable(self.ticket_data["cluster_id"])
        return True

    def kafka_enable(self) -> bool:
        api.cluster.kafka.enable(self.ticket_data["cluster_id"])
        return True

    def kafka_shrink(self) -> bool:
        # 缩容kafka集群 更新cmdb
        storage_instances = self.__generate_storage_instance()
        with atomic():
            # 删除集群绑定关系
            api.cluster.kafka.shrink(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
        return True

    def kafka_replace(self) -> bool:
        # 替换kafka集群 更新cmdb
        new_machines, new_storage_instances = self.__generate_new()
        old_storage_instances = self.__generate_old_storage_instance()
        new_broker_ip_list = self.__get_new_broker_ips()
        bk_cloud_id = new_machines[0]["bk_cloud_id"]
        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=bk_cloud_id,
                machines=new_machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=new_storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.kafka.replace(
                cluster_id=self.ticket_data["cluster_id"],
                old_storages=old_storage_instances,
                new_storages=new_storage_instances,
            )
            if self.ticket_data.get("zk_ip"):
                transfer_host_in_cluster_module(
                    cluster_ids=[self.ticket_data["cluster_id"]],
                    ip_list=[self.ticket_data["zk_ip"]],
                    machine_type=MachineType.ZOOKEEPER.value,
                    bk_cloud_id=bk_cloud_id,
                )
            if new_broker_ip_list:
                transfer_host_in_cluster_module(
                    cluster_ids=[self.ticket_data["cluster_id"]],
                    ip_list=new_broker_ip_list,
                    machine_type=MachineType.BROKER.value,
                    bk_cloud_id=bk_cloud_id,
                )
        return True
