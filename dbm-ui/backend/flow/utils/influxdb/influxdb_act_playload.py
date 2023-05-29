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
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName
from backend.flow.consts import DBActuatorTypeEnum, LevelInfoEnum, NameSpaceEnum
from backend.ticket.constants import TicketType

apply_list = [TicketType.MYSQL_SINGLE_APPLY.value, TicketType.MYSQL_HA_APPLY.value]


def get_base_payload(action, host) -> dict:
    """
    拼接安装payload参数
    """
    return {
        "db_type": DBActuatorTypeEnum.Influxdb.value,
        "action": action,
        "payload": {
            "general": {},
            "extend": {
                "host": host,
            },
        },
    }


class InfluxdbActPayload(object):
    """
    定义mysql不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data 单据信息
        """
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data

    def __get_influxdb_config(self, version, instance_id) -> Any:
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.INSTANCE,
                "level_value": str(instance_id),
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault, "cluster": "0"},
                "conf_file": version,
                "conf_type": ConfType.DBCONF,
                "namespace": NameSpaceEnum.Influxdb,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def get_payload(self, action, host) -> dict:
        """
        拼接安装payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Influxdb.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "host": host,
                    "version": self.ticket_data["db_version"],
                    "port": self.ticket_data["port"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_telegraf_payload(self, action, host) -> dict:
        """
        拼接安装payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Influxdb.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "host": host,
                    "port": self.ticket_data["port"],
                    "group_id": self.ticket_data["group_id"],
                    "group_name": self.ticket_data["group_name"],
                },
            },
        }

    def get_replace_payload(self, action, host, port, version, group_id, group_name, instance_id) -> dict:
        """
        拼接安装payload参数
        """
        influxdb_config = self.__get_influxdb_config(version=version, instance_id=instance_id)
        return {
            "db_type": DBActuatorTypeEnum.Influxdb.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "host": host,
                    "port": port,
                    "version": version,
                    "username": influxdb_config["username"],
                    "password": influxdb_config["password"],
                    "group_id": group_id,
                    "group_name": group_name,
                },
            },
        }
