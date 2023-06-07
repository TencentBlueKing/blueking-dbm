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
from backend.flow.consts import ES_DEFAULT_INSTANCE_NUM, ESRoleEnum, LevelInfoEnum

logger = logging.getLogger("flow")


class EsDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    规定：
    Machine:
        access_layer:          storage
    StorageInstance:
        access_layer:          storage
        machine_type:          datanode/master/client
        instance_role:         datanode_hot/datanode_cold/master/client
        instance_inner_role:   orphan
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.role_machine_dict = {
            ESRoleEnum.HOT.value: MachineType.ES_DATANODE.value,
            ESRoleEnum.COLD.value: MachineType.ES_DATANODE.value,
            ESRoleEnum.MASTER.value: MachineType.ES_MASTER.value,
            ESRoleEnum.CLIENT.value: MachineType.ES_CLIENT.value,
        }
        self.role_instance_dict = {
            ESRoleEnum.HOT.value: InstanceRole.ES_DATANODE_HOT.value,
            ESRoleEnum.COLD.value: InstanceRole.ES_DATANODE_COLD.value,
            ESRoleEnum.MASTER.value: InstanceRole.ES_MASTER.value,
            ESRoleEnum.CLIENT.value: InstanceRole.ES_CLIENT.value,
        }

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return [node["ip"] for node in self.ticket_data["nodes"][role]]

    def __generate_machine(self) -> list:
        machines = []
        for role in self.role_machine_dict.keys():
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
        for role, role_nodes in self.ticket_data["nodes"].items():
            role_name = "dn" if role == "hot" else role
            for node in role_nodes:
                for i in range(0, node.get("instance_num", ES_DEFAULT_INSTANCE_NUM)):
                    instances.append(
                        {
                            "ip": node["ip"],
                            "port": self.ticket_data["http_port"] + i,
                            "instance_role": self.role_instance_dict[role],
                            "name": f'{role_name}-{node["ip"]}_{i+1}',
                        }
                    )
        return instances

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型需要变更的cmdb函数{}，请联系系统管理员").format(function_name))
        return False

    def es_apply(self) -> bool:
        # 部署es，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()
        cluster = {
            "bk_cloud_id": self.ticket_data["bk_cloud_id"],
            "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
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
            api.cluster.es.create(**cluster)

        return True

    def es_scale_up(self) -> bool:
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()

        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.es.scale_up(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
        return True

    def es_destroy(self) -> bool:
        api.cluster.es.destroy(self.ticket_data["cluster_id"])
        return True

    def es_disable(self) -> bool:
        api.cluster.es.disable(self.ticket_data["cluster_id"])
        return True

    def es_enable(self) -> bool:
        api.cluster.es.enable(self.ticket_data["cluster_id"])
        return True

    def es_shrink(self) -> bool:
        storage_instances = self.__generate_storage_instance()
        api.cluster.es.shrink(
            cluster_id=self.ticket_data["cluster_id"],
            storages=storage_instances,
        )
        return True
