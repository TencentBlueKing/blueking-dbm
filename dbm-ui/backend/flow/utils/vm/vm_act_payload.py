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
from backend.components.dbconfig.client import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.flow.consts import ConfigTypeEnum, DBActuatorTypeEnum, NameSpaceEnum, VmActuatorActionEnum, VmRoleEnum
from backend.ticket.constants import TicketType


class VmActPayload(object):
    """
    定义vm不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict):
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data
        self.vm_config = self.__get_vm_config()

    def __get_vm_config(self) -> dict:
        if self.ticket_data["ticket_type"] == TicketType.VM_APPLY.value:
            data = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                    "level_name": LevelName.APP,
                    "level_value": str(self.ticket_data["bk_biz_id"]),
                    "conf_file": self.ticket_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Vm,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )
        else:
            # 已有集群的单据操作，通过集群域名获取个性化配置
            data = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                    "level_name": LevelName.CLUSTER,
                    "level_value": self.ticket_data["vminsert_domain"],
                    "conf_file": self.ticket_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Vm,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )

        return {
            VmRoleEnum.VMSTORAGE: data["content"][VmRoleEnum.VMSTORAGE],
            VmRoleEnum.VMINSERT: data["content"][VmRoleEnum.VMINSERT],
            VmRoleEnum.VMSELECT: data["content"][VmRoleEnum.VMSELECT],
            VmRoleEnum.VMAUTH: data["content"][VmRoleEnum.VMAUTH],
        }

    def __get_vmstorage_ipstr(self, port: int) -> str:
        """
        生成vminsert和vmselect的storage地址
        格式: ip1:port,ip2:port,ip3:port
        vminsert传8400
        vmselect传8401
        """
        return ",".join(f"{address}:{port}" for address in self.__get_vm_ips(role=InstanceRole.VM_STORAGE.value))

    def __get_vminsert_ipstr(self, port: int) -> str:
        return ",".join(f"{address}:{port}" for address in self.__get_vm_ips(role=InstanceRole.VM_INSERT.value))

    def __get_vmselect_ipstr(self, port: int) -> str:
        return ",".join(f"{address}:{port}" for address in self.__get_vm_ips(role=InstanceRole.VM_SELECT.value))

    # 定义常规extend参数
    def get_common_extend(self, **kwargs) -> dict:
        return {
            "host": kwargs["ip"],
            "cluster_name": self.ticket_data["cluster_name"],
            "vm_version": self.ticket_data["db_version"],
            "role": kwargs["role"],
            "username": self.ticket_data["username"],
            "password": self.ticket_data["password"],
            "vminsert_port": self.ticket_data["vminsert_port"],
            "vmselect_port": self.ticket_data["vmselect_port"],
        }

    def __get_vm_ips(self, role: str) -> list:
        """
        生成vm ip数据
        :return:
        """
        ticket_type = self.ticket_data["ticket_type"]
        # 当为TicketType.VM_APPLY时，从ticket_data返回
        if ticket_type == TicketType.VM_APPLY:
            return [node["ip"] for node in self.ticket_data["nodes"].get(role, [])]

        # 当为 TicketType.VM_SCALE_UP 或 TicketType.VM_SHRINK 时，从dbmeta获取
        if ticket_type in (
            TicketType.VM_SCALE_UP,
            TicketType.VM_SHRINK,
        ):
            cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
            db_ips = set(cluster.storageinstance_set.filter(instance_role=role).values_list("machine__ip", flat=True))

            # 当为TicketType.VM_SCALE_UP时，取ticket_data和数据库的合集
            if ticket_type == TicketType.VM_SCALE_UP:
                ticket_ips = set(node["ip"] for node in self.ticket_data["nodes"].get(role, []))
                return list(db_ips | ticket_ips)  # Union of db_ips and ticket_ips

            # 当为TicketType.VM_SHRINK时，取数据库和ticket_data的差集
            elif ticket_type == TicketType.VM_SHRINK:
                ticket_ips = set(node["ip"] for node in self.ticket_data["nodes"].get(role, []))
                return list(db_ips - ticket_ips)  # Difference of db_ips and ticket_ips

            # 当为TicketType.VM_REPLACE时，取数据库跟new_nodes的合集再减去old_nodes
            elif ticket_type == TicketType.VM_REPLACE:
                new_nodes_ips = set(node["ip"] for node in self.ticket_data["new_nodes"].get(role, []))
                old_nodes_ips = set(node["ip"] for node in self.ticket_data["old_nodes"].get(role, []))
                return list(
                    (db_ips | new_nodes_ips) - old_nodes_ips
                )  # Union of db_ips and new_nodes_ips, then difference of old_nodes_ips
        # 如果ticket_type不是上述任何一种，返回空列表
        return []

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        :param kwargs:
        :return:
        """
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.Init.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "vm_version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_install_supervisor_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.InstallSupervisor.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                },
            },
        }

    def get_decompress_vm_pkg_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.DecompressPkg.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_install_vmstorage_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.InstallVmStorage.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "storage_config": self.vm_config[VmRoleEnum.VMSTORAGE],
                    "retention_period": self.ticket_data["retention_period"],
                },
            },
        }

    def get_install_vminsert_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.InstallVmInsert.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "insert_config": self.vm_config[VmRoleEnum.VMINSERT],
                    "replication_factor": int(self.ticket_data["replication_factor"]),
                    "storage_node": self.ticket_data["vminsert_storage_node"],
                },
            },
        }

    def get_install_vmselect_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.InstallVmSelect.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "select_config": self.vm_config[VmRoleEnum.VMSELECT],
                    "retention_period": self.ticket_data["retention_period"],
                    "storage_node": self.ticket_data["vmselect_storage_node"],
                },
            },
        }

    def get_install_vmauth_payload(self, **kwargs) -> dict:
        vminsert_port = int(self.ticket_data["vminsert_port"])
        vmselect_port = int(self.ticket_data["vmselect_port"])
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.InstallVmAuth.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "insert_nodes": self.__get_vminsert_ipstr(port=vminsert_port),
                    "select_nodes": self.__get_vmselect_ipstr(port=vmselect_port),
                    "auth_config": self.vm_config[VmRoleEnum.VMAUTH],
                },
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.StopProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_start_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.StopProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_reboot_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.RestartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_clean_data_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.CleanData.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "cluster_name": self.ticket_data["cluster_name"],
                },
            },
        }

    def reload_vmselect_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.ReloadVmSelect.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "select_config": self.vm_config[VmRoleEnum.VMSELECT],
                    "retention_period": self.ticket_data["retention_period"],
                    "storage_node": self.ticket_data["vmselect_storage_node"],
                },
            },
        }

    def reload_vminsert_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Vm.value,
            "action": VmActuatorActionEnum.ReloadVmInsert.value,
            "payload": {
                "general": {},
                "extend": {
                    "vm_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "insert_config": self.vm_config[VmRoleEnum.VMINSERT],
                    "replication_factor": int(self.ticket_data["replication_factor"]),
                    "storage_node": self.ticket_data["vminsert_storage_node"],
                },
            },
        }
