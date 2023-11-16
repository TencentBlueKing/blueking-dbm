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
from typing import Any

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName
from backend.configuration.constants import DBType
from backend.flow.consts import (
    DBActuatorTypeEnum,
    KafkaActuatorActionEnum,
    ManagerDefaultPort,
    ManagerServiceType,
    NameSpaceEnum,
)
from backend.ticket.constants import TicketType

apply_list = [TicketType.MYSQL_SINGLE_APPLY.value, TicketType.MYSQL_HA_APPLY.value]


def get_base_payload(action, host) -> dict:
    """
    拼接安装payload参数
    """
    return {
        "db_type": DBActuatorTypeEnum.Kafka.value,
        "action": action,
        "payload": {
            "general": {},
            "extend": {
                "host": host,
            },
        },
    }


class KafkaActPayload(object):
    """
    定义mysql不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, ticket_data: dict, zookeeper_ip: str):
        """
        @param ticket_data 单据信息
        """
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data
        self.zookeeper_ip = zookeeper_ip
        self.kafka_config = self.__get_kafka_config()

    def __get_kafka_config(self) -> Any:
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.APP,
                "level_value": str(self.ticket_data["bk_biz_id"]),
                "conf_file": self.ticket_data["db_version"],
                "conf_type": ConfType.DBCONF,
                "namespace": NameSpaceEnum.Kafka,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def get_zookeeper_payload(self, action, my_id, host, zookeeper_conf) -> dict:
        """
        拼接安装zookeeper payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "my_id": my_id,
                    "host": host,
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "zookeeper_conf": zookeeper_conf,
                    "no_security": self.ticket_data["no_security"],
                    "version": self.ticket_data["db_version"],
                },
            },
        }

    def get_payload(self, action, host) -> dict:
        """
        拼接安装payload参数
        """
        kafka_config = copy.deepcopy(self.kafka_config)
        if not self.ticket_data.get("no_security"):
            self.ticket_data["no_security"] = 0
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "host": host,
                    "zookeeper_ip": self.zookeeper_ip,
                    "version": self.ticket_data["db_version"],
                    "kafka_configs": kafka_config,
                    "port": self.ticket_data["port"],
                    "jmx_port": int(kafka_config["jmx_port"]),
                    "retention": self.ticket_data["retention_hours"],
                    "replication": self.ticket_data["replication_num"],
                    "partition": self.ticket_data["partition_num"],
                    "factor": self.ticket_data["factor"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "no_security": self.ticket_data["no_security"],
                },
            },
        }

    def get_manager_payload(self, action, host) -> dict:
        """
        拼接安装manager payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "host": host,
                    "port": ManagerDefaultPort.KAFKA_MANAGER,
                    "zookeeper_ip": self.zookeeper_ip,
                    "version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "db_type": DBType.Kafka,
                    "service_type": ManagerServiceType.KAFKA_MANAGER,
                },
            },
        }

    def get_admin_user_payload(self, action) -> dict:
        """
        拼接安装payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "zookeeper_ip": self.zookeeper_ip,
                    "version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_user_payload(self, action) -> dict:
        """
        拼接安装payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "zookeeper_ip": self.zookeeper_ip,
                    "version": self.ticket_data["db_version"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                },
            },
        }

    def get_shrink_payload(self, action, host, new_host=None) -> dict:
        """
        拼接缩容参数
        """
        zookeeper_ip = self.zookeeper_ip.split(",")[0]
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": action,
            "payload": {
                "general": {},
                "extend": {
                    "zookeeper_ip": zookeeper_ip,
                    "exclude_brokers": host,
                    "new_brokers": new_host,
                },
            },
        }

    def get_restart_payload(self) -> dict:
        """
        拼接安装payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Kafka.value,
            "action": KafkaActuatorActionEnum.RestartBroker.value,
            "payload": {
                "general": {},
                "extend": {
                    "zookeeper_ip": self.zookeeper_ip,
                },
            },
        }
