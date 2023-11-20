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
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.models import Cluster

from backend.flow.consts import (
    ConfigTypeEnum,
    DBActuatorTypeEnum,
    LevelInfoEnum,
    NameSpaceEnum,
    PulsarActuatorActionEnum,
    PulsarRoleEnum,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.pulsar.consts import PulsarConfigEnum
from backend.ticket.constants import TicketType


class PulsarActPayload(object):
    """
    定义Pulsar不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, ticket_data: dict):
        self.ticket_data = ticket_data
        self.pulsar_config = self.__get_pulsar_config()

    def __get_pulsar_config(self) -> dict:
        if self.ticket_data["ticket_type"] == TicketType.PULSAR_APPLY.value:
            data = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                    "level_name": LevelName.APP,
                    "level_value": str(self.ticket_data["bk_biz_id"]),
                    "conf_file": self.ticket_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Pulsar,
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
                    "level_value": self.ticket_data["domain"],
                    "conf_file": self.ticket_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Pulsar,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )

        return {
            PulsarRoleEnum.ZooKeeper: data["content"][PulsarRoleEnum.ZooKeeper],
            PulsarRoleEnum.BookKeeper: data["content"][PulsarRoleEnum.BookKeeper],
            PulsarRoleEnum.Broker: data["content"][PulsarRoleEnum.Broker],
        }

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        :param kwargs:
        :return:
        """
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.Init.value,
            "payload": {
                "general": {},
                "extend": {"host": kwargs["ip"], "pulsar_version": self.ticket_data["db_version"]},
            },
        }

    def get_decompress_pkg_payload(self, **kwargs) -> dict:
        """
        拼接解压缩包的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.DecompressPkg.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_install_supervisor_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InstallSupervisor.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_install_zookeeper_payload(self, **kwargs) -> dict:
        """
        拼接 安装ZooKeeper的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InstallZookeeper.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "zk_id": kwargs["my_id"],
                    "zk_host": self.ticket_data["zk_hosts_str"],
                    "zk_configs": self.pulsar_config[PulsarRoleEnum.ZooKeeper],
                },
            },
        }

    def get_init_cluster_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InitCluster.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "zk_host": self.ticket_data["zk_hosts_str"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "domain": self.ticket_data["domain"],
                },
            },
        }

    def get_install_bookkeeper_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InstallBookKeeper.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "zk_host": self.ticket_data["zk_hosts_str"],
                    "bk_configs": self.pulsar_config[PulsarRoleEnum.BookKeeper],
                },
            },
        }

    def get_install_broker_payload(self, **kwargs) -> dict:
        if self.ticket_data["ticket_type"] == TicketType.PULSAR_APPLY.value:
            extend_dict = {
                "pulsar_version": self.ticket_data["db_version"],
                "host": kwargs["ip"],
                "zk_host": self.ticket_data["zk_hosts_str"],
                "broker_configs": self.pulsar_config[PulsarRoleEnum.Broker],
                "cluster_name": self.ticket_data["cluster_name"],
                "partitions": self.ticket_data["partition_num"],
                "retention_time": self.ticket_data["retention_time"],
                "ensemble_size": self.ticket_data["ensemble_size"],
                "write_quorum": self.ticket_data["replication_num"],
                "ack_quorum": self.ticket_data["ack_quorum"],
                "token": "token:" + kwargs["trans_data"]["init_token_info"]["token"],
            }
        else:
            extend_dict = {
                "pulsar_version": self.ticket_data["db_version"],
                "host": kwargs["ip"],
                "zk_host": self.ticket_data["zk_hosts_str"],
                "broker_configs": self.pulsar_config[PulsarRoleEnum.Broker],
                "cluster_name": self.ticket_data["cluster_name"],
                "token": self.ticket_data["token"],
            }
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InstallBroker.value,
            "payload": {
                "general": {},
                "extend": extend_dict,
            },
        }

    def get_init_manager_payload(self, **kwargs) -> dict:
        if self.ticket_data["ticket_type"] == TicketType.PULSAR_APPLY.value:
            token = "token:" + kwargs["trans_data"]["init_token_info"]["token"]
        else:
            # ZK替换场景 新建Pulsar Manager，参数从密码服务 取
            token = self.ticket_data["token"]

        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InitManager.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "broker_web_service_port": int(self.pulsar_config[PulsarRoleEnum.Broker]["webServicePort"]),
                    "domain": self.ticket_data["domain"],
                    "zk_host": self.ticket_data["zk_hosts_str"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "token": token,
                },
            },
        }

    def get_install_manager_payload(self, **kwargs) -> dict:
        if self.ticket_data["ticket_type"] == TicketType.PULSAR_APPLY.value:
            token = "token:" + kwargs["trans_data"]["init_token_info"]["token"]
        else:
            # ZK替换场景 新建Pulsar Manager，token从密码服务获取
            token = self.ticket_data["token"]

        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.InstallManager.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "username": self.ticket_data["username"],
                    "password": self.ticket_data["password"],
                    "token": token,
                    "broker_web_service_port": int(self.pulsar_config[PulsarRoleEnum.Broker]["webServicePort"]),
                    "domain": self.ticket_data["domain"],
                    "zk_host": self.ticket_data["zk_hosts_str"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nginx_sub_path": "{}/pulsar/{}/pulsar_manager/".format(
                        self.ticket_data["bk_biz_id"], self.ticket_data["cluster_name"]
                    ),
                },
            },
        }

    def get_add_hosts_payload(self, **kwargs) -> dict:
        if kwargs["zk_host_map"]:
            zk_host_map = kwargs["zk_host_map"]
        else:
            zk_host_map = self.ticket_data["zk_host_map"]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.AddHosts.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "host_map": zk_host_map,
                },
            },
        }

    def get_modify_hosts_payload(self, **kwargs) -> dict:
        if kwargs["zk_host_map"]:
            zk_host_map = kwargs["zk_host_map"]
        else:
            zk_host_map = self.ticket_data["zk_host_map"]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.ModifyHosts.value,
            "payload": {
                "general": {},
                "extend": {
                    "pulsar_version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                    "host_map": zk_host_map,
                },
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.StopProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_start_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.StartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_reboot_process_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.RestartProcess.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "role": kwargs["role"],
                },
            },
        }

    def get_clean_data_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.CleanData.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_check_broker_config_payload(self, **kwargs) -> dict:
        if "shrink_bookie_ips" in self.ticket_data:
            shrink_bookie_ips = self.ticket_data["shrink_bookie_ips"]
        else:
            shrink_bookie_ips = [node["ip"] for node in self.ticket_data["old_nodes"][PulsarRoleEnum.BookKeeper]]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.CheckBrokerConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "bookkeeper_num": kwargs["cur_bookie_num"],
                    "bookkeeper_ip": shrink_bookie_ips,
                    "http_port": self.ticket_data["port"],
                },
            },
        }

    def get_check_namespace_config_payload(self, **kwargs) -> dict:
        if "shrink_bookie_ips" in self.ticket_data:
            shrink_bookie_ips = self.ticket_data["shrink_bookie_ips"]
        else:
            shrink_bookie_ips = [node["ip"] for node in self.ticket_data["old_nodes"][PulsarRoleEnum.BookKeeper]]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.CheckNamespaceConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "bookkeeper_num": kwargs["cur_bookie_num"],
                    "bookkeeper_ip": shrink_bookie_ips,
                    "http_port": self.ticket_data["port"],
                },
            },
        }

    def get_check_under_replicated_payload(self, **kwargs) -> dict:
        if "shrink_bookie_ips" in self.ticket_data:
            shrink_bookie_ips = self.ticket_data["shrink_bookie_ips"]
        else:
            shrink_bookie_ips = [node["ip"] for node in self.ticket_data["old_nodes"][PulsarRoleEnum.BookKeeper]]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.CheckUnderReplicated.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "bookkeeper_num": kwargs["cur_bookie_num"],
                    "bookkeeper_ip": shrink_bookie_ips,
                    "http_port": self.ticket_data["port"],
                },
            },
        }

    def get_set_bookie_read_only_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.SetBookieReadOnly.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_check_ledger_metadata_payload(self, **kwargs) -> dict:
        if "shrink_bookie_ips" in self.ticket_data:
            shrink_bookie_ips = self.ticket_data["shrink_bookie_ips"]
        else:
            shrink_bookie_ips = [node["ip"] for node in self.ticket_data["old_nodes"][PulsarRoleEnum.BookKeeper]]
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.CheckLedgerMetadata.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "bookkeeper_num": kwargs["cur_bookie_num"],
                    "bookkeeper_ip": shrink_bookie_ips,
                    "http_port": self.ticket_data["port"],
                },
            },
        }

    def get_decommission_bookie_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Pulsar.value,
            "action": PulsarActuatorActionEnum.DecommissionBookie.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                    "bookkeeper_num": kwargs["cur_bookie_num"],
                    "bookkeeper_ip": [],
                    "http_port": self.ticket_data["port"],
                },
            },
        }


def get_cluster_config(bk_biz_id: str, cluster_domain: str, db_version: str, conf_type: ConfigTypeEnum) -> dict:
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": NameSpaceEnum.Pulsar,
            "format": FormatType.MAP_LEVEL,
            "method": ReqType.GENERATE_AND_PUBLISH,
        }
    )
    return data["content"]


def get_token_by_cluster(cluster: Cluster, port: int) -> str:
    return PayloadHandler.get_bigdata_password_by_cluster(
        cluster, port, PulsarConfigEnum.ClientAuthenticationParameters
    )
