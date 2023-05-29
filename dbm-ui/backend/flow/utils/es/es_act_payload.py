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

from typing import Any

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import (
    ES_DEFAULT_INSTANCE_NUM,
    ConfigTypeEnum,
    DBActuatorTypeEnum,
    EsActuatorActionEnum,
    ESRoleEnum,
    ManagerServiceType,
    NameSpaceEnum,
)
from backend.ticket.constants import TicketType


class EsActPayload(object):
    """
    定义ES不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict):
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data

    def __get_es_account(self) -> Any:
        """获取ES实例内置账户密码"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": self.bk_biz_id,
                "conf_file": "es#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.Es,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def __get_master_ips(self) -> list:
        """
        生成master ip数据
        :return:
        """
        if self.ticket_data["ticket_type"] == TicketType.ES_APPLY:
            # 创建集群的master从单据获取
            if "master" not in self.ticket_data["nodes"]:
                return []
            return [node["ip"] for node in self.ticket_data["nodes"]["master"]]
        elif self.ticket_data["ticket_type"] == TicketType.ES_SCALE_UP:
            # 扩容集群的master从dbmeta获取
            cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
            return list(
                set(
                    cluster.storageinstance_set.filter(instance_role=InstanceRole.ES_MASTER).values_list(
                        "machine__ip", flat=True
                    )
                )
            )
        elif self.ticket_data["ticket_type"] == TicketType.ES_SHRINK:
            # 缩容集群的master从dbmeta获取
            cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
            return list(
                set(
                    cluster.storageinstance_set.filter(instance_role=InstanceRole.ES_MASTER).values_list(
                        "machine__ip", flat=True
                    )
                )
            )
        return []

    def __get_master_nodenames(self) -> list:
        """
        生成master node name数组
        :return:
        """
        return ["master-" + ip + "_1" for ip in self.__get_master_ips()]

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.ticket_data["nodes"]:
            return []
        return [node["ip"] for node in self.ticket_data["nodes"][role]]

    def __get_all_node_ips(self) -> list:
        ips = []
        for role in self.ticket_data["nodes"]:
            ips.extend(self.__get_node_ips_by_role(role))
        return ips

    def __get_all_instances(self) -> list:
        instances = []
        for role in self.ticket_data["nodes"]:
            role_instances = self.ticket_data["nodes"][role]
            if role in [ESRoleEnum.MASTER.value, ESRoleEnum.CLIENT.value]:
                for role_instance in role_instances:
                    role_instance["instance_num"] = ES_DEFAULT_INSTANCE_NUM
            instances.extend(role_instances)
        return instances

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        :param kwargs:
        :return:
        """
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.Init.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "es_version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_install_es_payload(self, **kwargs) -> dict:
        """
        拼接安装节点的payload参数
        :param kwargs:
        :return:
        """
        action_dic = {
            "master": EsActuatorActionEnum.InstallMaster.value,
            "hot": EsActuatorActionEnum.InstallHot.value,
            "cold": EsActuatorActionEnum.InstallCold.value,
            "client": EsActuatorActionEnum.InstallClient.value,
        }
        master_ip = ",".join(self.__get_master_ips())
        master_nodename = ",".join(self.__get_master_nodenames())
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": action_dic[kwargs["role"]],
            "payload": {
                "general": {},
                "extend": {
                    "es_configs": self.ticket_data["es_config"],
                    "es_version": self.ticket_data["db_version"],
                    "http_port": self.ticket_data["http_port"],
                    "master_ip": master_ip,
                    "master_nodename": master_nodename,
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "instances": kwargs["instance_num"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_install_kibana_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.InstallKibana.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    "http_port": self.ticket_data["http_port"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "db_type": DBType.Es,
                    "service_type": ManagerServiceType.KIBANA,
                },
            },
        }

    def get_install_supervisor_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.InstallSupervisor.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                },
            },
        }

    def get_decompress_es_pkg_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.DecompressPkg.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                },
            },
        }

    def get_init_grant_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.InitGrant.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_install_telegraf_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.InstallTelegraf.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "http_port": self.ticket_data["http_port"],
                    "cluster_name": self.ticket_data["cluster_name"],
                },
            },
        }

    def get_install_exporter_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.InstallExporter.value,
            "payload": {
                "general": {},
                "extend": {
                    "es_version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                },
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.StopProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_start_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.StartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_reboot_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.RestartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "nodes": kwargs["instance_name"],
                },
            },
        }

    def get_clean_data_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.CleanData.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                },
            },
        }

    def get_exclude_node_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.ExcludeNode.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "http_port": self.ticket_data["http_port"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "exclude_nodes": self.__get_all_node_ips(),
                },
            },
        }

    def get_check_shards_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.CheckShards.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "http_port": self.ticket_data["http_port"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "exclude_nodes": self.__get_all_node_ips(),
                },
            },
        }

    def get_check_connections_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.CheckConnections.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "http_port": self.ticket_data["http_port"],
                },
            },
        }

    def get_check_nodes_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.CheckNodes.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "http_port": self.ticket_data["http_port"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "nodes": self.__get_all_instances(),
                },
            },
        }

    def get_replace_master_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Es.value,
            "action": EsActuatorActionEnum.ReplaceMaster.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "masters": self.__get_master_ips(),
                },
            },
        }
