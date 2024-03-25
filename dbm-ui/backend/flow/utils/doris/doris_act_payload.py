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


from backend.flow.consts import DBActuatorTypeEnum, DorisActuatorActionEnum
from backend.flow.utils.doris.consts import DorisMetaOperation, DorisNodeOperation


class DorisActPayload(object):
    """
    定义Doris不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict):
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        :param kwargs:
        :return:
        """
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.Init.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_install_supervisor_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.InstallSupervisor.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_render_config_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.RenderConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "http_port": self.ticket_data["http_port"],
                    "query_port": self.ticket_data["query_port"],
                    "master_fe_ip": self.ticket_data["master_fe_ip"],
                    "fe_conf": self.ticket_data["fe_conf"],
                    "be_conf": self.ticket_data["be_conf"],
                },
            },
        }

    def get_start_fe_by_helper_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.StartFeByHelper.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "http_port": self.ticket_data["http_port"],
                    "query_port": self.ticket_data["query_port"],
                    "master_fe_ip": self.ticket_data["master_fe_ip"],
                },
            },
        }

    def get_decompress_doris_pkg_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.DecompressPkg.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_add_nodes_metadata_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.UpdateMetadata.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "http_port": self.ticket_data["http_port"],
                    "query_port": self.ticket_data["query_port"],
                    "master_fe_ip": self.ticket_data["master_fe_ip"],
                    "operation": DorisMetaOperation.Add.value,
                    "host_map": self.ticket_data["host_meta_map"],
                },
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.StopProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "component": kwargs["role"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "operation": DorisNodeOperation.Stop,
                },
            },
        }

    def get_init_grant_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.InitGrant.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "http_port": self.ticket_data["http_port"],
                    "query_port": self.ticket_data["query_port"],
                    "master_fe_ip": self.ticket_data["master_fe_ip"],
                },
            },
        }

    def get_install_doris_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.InstallDoris.value,
            "payload": {
                "general": {},
                "extend": {
                    "version": self.ticket_data["db_version"],
                    # 目标机器IP，目标机器获取IP比较麻烦，不易知道哪块网卡
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "http_port": self.ticket_data["http_port"],
                    "query_port": self.ticket_data["query_port"],
                    "master_fe_ip": self.ticket_data["master_fe_ip"],
                },
            },
        }

    def get_start_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.StartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "component": kwargs["role"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "operation": DorisNodeOperation.Start,
                },
            },
        }

    def get_reboot_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.RestartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "component": kwargs["role"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "operation": DorisNodeOperation.Restart,
                },
            },
        }

    def get_clean_data_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.CleanData.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                    "cluster_name": self.ticket_data["cluster_name"],
                },
            },
        }
