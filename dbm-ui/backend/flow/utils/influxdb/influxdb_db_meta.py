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
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.utils.influxdb.bk_module_operate import create_bk_module, transfer_host_in_cluster_module

logger = logging.getLogger("flow")


class InfluxdbMeta(object):
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
            "influxdb": MachineType.INFLUXDB.value,
        }
        self.role_instance_dict = {
            "influxdb": InstanceRole.INFLUXDB.value,
        }

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return self.ticket_data["nodes"][role]

    def __generate_machine(self) -> list:
        machines = []
        for role in self.role_machine_dict.keys():
            for node in self.__get_node_ips_by_role(role):
                machine = {
                    "ip": node["ip"],
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

    def __generate_storage_instance(self, global_port=None) -> list:
        instances = []
        for role in self.role_instance_dict.keys():
            for node in self.__get_node_ips_by_role(role):
                instances.append(
                    {
                        "ip": node["ip"],
                        "port": global_port or self.ticket_data["port"],
                        "instance_role": self.role_instance_dict[role],
                        "bk_cloud_id": node["bk_cloud_id"],
                        "db_version": self.ticket_data["db_version"],
                    }
                )
        return instances

    def __get_instance_ips(self) -> list:
        return [instance["ip"] for instance in self.ticket_data["instance_list"]]

    def __generate_new_machine(self) -> list:
        machines = []
        for node in self.ticket_data["new_nodes"]["influxdb"]:
            machine = {
                "ip": node["ip"],
                "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                "machine_type": "influxdb",
                "bk_cloud_id": node["bk_cloud_id"],
            }
            if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                machine.update(
                    {
                        "spec_id": self.ticket_data["resource_spec"]["influxdb"]["id"],
                        "spec_config": self.ticket_data["resource_spec"]["influxdb"],
                    }
                )
            machines.append(machine)
        return machines

    def __generate_new_storage_instance(self) -> list:
        instances = []
        for node in self.ticket_data["new_nodes"]["influxdb"]:
            instances.append(
                {
                    "ip": node["ip"],
                    "port": node["port"],
                    "instance_role": "influxdb",
                    "bk_cloud_id": node["bk_cloud_id"],
                    "db_version": node["db_version"],
                }
            )
        return instances

    def __get_old_instance_ips(self) -> list:
        return [instance["ip"] for instance in self.ticket_data["old_nodes"]["influxdb"]]

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()
        else:
            logger.error(_("找不到单据类型需要变更的cmdb函数，请联系系统管理员"))
            return False

    def influxdb_apply(self) -> bool:
        # 部署influxdb实例，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()
        with atomic():
            # 绑定事务更新cmdb
            bk_cloud_id = self.ticket_data["nodes"]["influxdb"][0]["bk_cloud_id"]
            api.machine.create(
                bk_cloud_id=bk_cloud_id,
                machines=machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.influxdb.create(group_id=self.ticket_data["group_id"], storages=storage_instances)
            # 生成模块
            ips = [influxdb["ip"] for influxdb in self.ticket_data["nodes"]["influxdb"]]
            storages = StorageInstance.find_storage_instance_by_addresses(ips)
            create_bk_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                storages=storages,
                creator=self.ticket_data["created_by"],
            )
            transfer_host_in_cluster_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                storages=storages,
                machine_type=MachineType.INFLUXDB.value,
                group_name=self.ticket_data["group_name"],
            )
        return True

    def influxdb_destroy(self) -> bool:
        addresses = self.__get_instance_ips()
        api.cluster.influxdb.destroy(addresses)
        return True

    def influxdb_disable(self) -> bool:
        addresses = self.__get_instance_ips()
        api.cluster.influxdb.disable(addresses)
        return True

    def influxdb_enable(self) -> bool:
        addresses = self.__get_instance_ips()
        api.cluster.influxdb.enable(addresses)
        return True

    def influxdb_replace(self) -> bool:
        machines = self.__generate_new_machine()
        storage_instances = self.__generate_new_storage_instance()
        addresses = self.__get_old_instance_ips()
        with atomic():
            # 绑定事务更新cmdb
            bk_cloud_id = self.ticket_data["new_nodes"]["influxdb"][0]["bk_cloud_id"]
            api.machine.create(
                bk_cloud_id=bk_cloud_id,
                machines=machines,
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.influxdb.replace(
                nodes=self.ticket_data["new_nodes"]["influxdb"],
                storages=storage_instances,
                addresses=addresses,
            )
            # 生成模块
            ips = [influxdb["ip"] for influxdb in self.ticket_data["new_nodes"]["influxdb"]]
            storages = StorageInstance.find_storage_instance_by_addresses(ips)
            create_bk_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                storages=storages,
                creator=self.ticket_data["created_by"],
            )
            transfer_host_in_cluster_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                storages=storages,
                machine_type=MachineType.INFLUXDB.value,
                group_name=self.ticket_data["group_name"],
            )
        return True
