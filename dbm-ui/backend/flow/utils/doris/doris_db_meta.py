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
from backend.flow.consts import DorisRoleEnum, LevelInfoEnum
from backend.flow.utils.doris.consts import DEFAULT_BE_WEB_PORT

logger = logging.getLogger("flow")


class DorisDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    规定：
    Machine:
        access_layer:          storage
    StorageInstance:
        access_layer:          storage
        machine_type:          follower/observer/backend
        instance_role:         hot/cold/master/follower/observer
        instance_inner_role:   orphan
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.role_machine_dict = {
            DorisRoleEnum.HOT.value: MachineType.DORIS_BACKEND.value,
            DorisRoleEnum.COLD.value: MachineType.DORIS_BACKEND.value,
            DorisRoleEnum.FOLLOWER.value: MachineType.DORIS_FOLLOWER.value,
            DorisRoleEnum.OBSERVER.value: MachineType.DORIS_OBSERVER.value,
        }
        self.role_instance_dict = {
            DorisRoleEnum.HOT.value: InstanceRole.DORIS_BACKEND_HOT.value,
            DorisRoleEnum.COLD.value: InstanceRole.DORIS_BACKEND_COLD.value,
            DorisRoleEnum.FOLLOWER.value: InstanceRole.DORIS_FOLLOWER.value,
            DorisRoleEnum.OBSERVER.value: InstanceRole.DORIS_OBSERVER.value,
        }
        self.role_port_dict = {
            DorisRoleEnum.HOT.value: DEFAULT_BE_WEB_PORT,
            DorisRoleEnum.COLD.value: DEFAULT_BE_WEB_PORT,
            DorisRoleEnum.FOLLOWER.value: ticket_data.get("query_port", 0),
            DorisRoleEnum.OBSERVER.value: ticket_data.get("query_port", 0),
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
            for node in role_nodes:
                instances.append(
                    {
                        "ip": node["ip"],
                        "port": self.role_port_dict[role],
                        "instance_role": self.role_instance_dict[role],
                    }
                )
        return instances

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型需要变更的cmdb函数{}，请联系系统管理员").format(function_name))
        return False

    def doris_apply(self) -> bool:
        # 部署doris，更新cmdb
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
            api.cluster.doris.create(**cluster)

        return True

    def doris_scale_up(self) -> bool:
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()

        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.doris.scale_up(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
        return True

    def doris_destroy(self) -> bool:
        api.cluster.doris.destroy(self.ticket_data["cluster_id"])
        return True

    def doris_disable(self) -> bool:
        api.cluster.doris.disable(self.ticket_data["cluster_id"])
        return True

    def doris_enable(self) -> bool:
        api.cluster.doris.enable(self.ticket_data["cluster_id"])
        return True

    def doris_shrink(self) -> bool:
        storage_instances = self.__generate_storage_instance()
        api.cluster.doris.shrink(
            cluster_id=self.ticket_data["cluster_id"],
            storages=storage_instances,
        )
        return True

    def clear_machines(self):
        """
        清理机器信息
        """
        api.cluster.doris.clear_machine(machines=self.ticket_data["clear_hosts"])
