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
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import (
    ConfigTypeEnum,
    DBActuatorTypeEnum,
    HdfsDBActuatorActionEnum,
    LevelInfoEnum,
    NameSpaceEnum,
)
from backend.flow.utils.hdfs.hdfs_context_dataclass import HdfsApplyContext, HdfsReplaceContext, UpdateDfsHostOperation
from backend.ticket.constants import TicketType


class HdfsActPayload(object):
    """
    定义hdfs不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, ticket_data: dict):
        self.ticket_data = ticket_data
        self.init_hdfs_config = self.__get_hdfs_config()

    def __get_hdfs_config(self) -> dict:
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.APP,
                "level_value": str(self.ticket_data["bk_biz_id"]),
                "conf_file": self.ticket_data["db_version"],
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": NameSpaceEnum.Hdfs,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        return {
            "hdfs-site": data["content"]["hdfs-site"],
            "core-site": data["content"]["core-site"],
            "install": data["content"]["install"],
        }

    def __get_common_extend_payload(self, **kwargs) -> dict:
        return {
            "host": kwargs["ip"],
            "hdfs-site": self.init_hdfs_config["hdfs-site"],
            "core-site": self.init_hdfs_config["core-site"],
            "install": self.init_hdfs_config["install"],
            "version": self.ticket_data["db_version"],
            "host_map": self.ticket_data["all_ip_hosts"],
            "cluster_name": self.ticket_data["cluster_name"],
            "nn1_ip": self.ticket_data["nn1_ip"],
            "nn2_ip": self.ticket_data["nn2_ip"],
            "zk_ips": ",".join(self.ticket_data["zk_ips"]),
            "jn_ips": ",".join(self.ticket_data["jn_ips"]),
            "dn_ips": ",".join(self.ticket_data["dn_ips"]),
            "http_port": self.ticket_data["http_port"],
            "rpc_port": self.ticket_data["rpc_port"],
            "haproxy_passwd": self.ticket_data["haproxy_passwd"],
        }

    def __gen_only_ip_payload(self, action: HdfsDBActuatorActionEnum, ip: str) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": action.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": ip,
                },
            },
        }

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InitSystemConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "install_config": self.init_hdfs_config["install"],
                    "version": self.ticket_data["db_version"],
                    "host_map": self.ticket_data["all_ip_hosts"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_render_cluster_config_payload(self, **kwargs) -> dict:
        """
        拼接渲染HDFS集群配置的payload参数
        """
        hdfs_config = copy.deepcopy(self.init_hdfs_config)
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.RenderConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "hdfs-site": hdfs_config["hdfs-site"],
                    "core-site": hdfs_config["core-site"],
                    # "zoo.cfg": hdfs_config['zoo.cfg'],
                    "install": hdfs_config["install"],
                    "version": self.ticket_data["db_version"],
                    "host_map": self.ticket_data["all_ip_hosts"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nn1_ip": self.ticket_data["nn1_ip"],
                    "nn2_ip": self.ticket_data["nn2_ip"],
                    "zk_ips": ",".join(self.ticket_data["zk_ips"]),
                    "jn_ips": ",".join(self.ticket_data["jn_ips"]),
                    "dn_ips": ",".join(self.ticket_data["dn_ips"]),
                    "http_port": self.ticket_data["http_port"],
                    "rpc_port": self.ticket_data["rpc_port"],
                },
            },
        }

    def get_install_supervisor_payload(self, **kwargs) -> dict:
        """
        拼接安装supervisor的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallSupervisor.value,
            "payload": {"general": {}, "extend": self.__get_common_extend_payload(**kwargs)},
        }

    def get_install_zookeeper_payload(self, **kwargs) -> dict:
        """
        拼接安装zookeeper的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallZooKeeper.value,
            "payload": {
                "general": {},
                "extend": self.__get_common_extend_payload(**kwargs),
            },
        }

    def get_install_journal_node_payload(self, **kwargs) -> dict:
        """
        拼接安装JournalNode的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallJournalNode.value,
            "payload": {
                "general": {},
                "extend": self.__get_common_extend_payload(**kwargs),
            },
        }

    def get_install_nn1_payload(self, **kwargs) -> dict:
        """
        拼接安装NN1的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallNn1.value,
            "payload": {
                "general": {},
                "extend": self.__get_common_extend_payload(**kwargs),
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        """
        拼接停止进程的payload参数
        """
        return self.__gen_only_ip_payload(HdfsDBActuatorActionEnum.StopProcess, kwargs["ip"])

    def get_common_start_component_payload(self, **kwargs) -> dict:
        """
        拼接启动组件的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.StartStopComponent.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "component": kwargs["hdfs_role"],
                    "operation": "start",
                    "host": kwargs["ip"],
                },
            },
        }

    def get_common_stop_component_payload(self, **kwargs) -> dict:
        """
        拼接启动组件的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.StartStopComponent.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "component": kwargs["hdfs_role"],
                    "operation": "stop",
                    "host": kwargs["ip"],
                },
            },
        }

    def get_common_restart_component_payload(self, **kwargs) -> dict:
        """
        拼接重启组件的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.StartStopComponent.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "component": kwargs["hdfs_role"],
                    "operation": "restart",
                    "host": kwargs["ip"],
                },
            },
        }

    def get_data_clean_payload(self, **kwargs) -> dict:
        """
        拼接数据清理的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.CleanData.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_install_nn2_payload(self, **kwargs) -> dict:
        """
        拼接安装NN2的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallNn2.value,
            "payload": {
                "general": {},
                "extend": self.__get_common_extend_payload(**kwargs),
            },
        }

    def get_install_zkfc_payload(self, **kwargs) -> dict:
        """
        拼接安装ZKFC的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallZKFC.value,
            "payload": {
                "general": {},
                "extend": self.__get_common_extend_payload(**kwargs),
            },
        }

    def get_install_datanode_payload(self, **kwargs) -> dict:
        """
        拼接安装DataNode的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallDataNode.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "hdfs-site": self.init_hdfs_config["hdfs-site"],
                    "core-site": self.init_hdfs_config["core-site"],
                    "install": self.init_hdfs_config["install"],
                    "version": self.ticket_data["db_version"],
                    "host_map": self.ticket_data["all_ip_hosts"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nn1_ip": self.ticket_data["nn1_ip"],
                    "nn2_ip": self.ticket_data["nn2_ip"],
                    "zk_ips": ",".join(self.ticket_data["zk_ips"]),
                    "jn_ips": ",".join(self.ticket_data["jn_ips"]),
                    "dn_ips": ",".join(self.ticket_data["dn_ips"]),
                    "http_port": self.ticket_data["http_port"],
                    "rpc_port": self.ticket_data["rpc_port"],
                },
            },
        }

    def get_install_telegraf_payload(self, **kwargs) -> dict:
        """
        拼接安装telegraf的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallTelegraf.value,
            "payload": {"general": {}, "extend": {}},
        }

    def get_decompress_package_payload(self, **kwargs) -> dict:
        """
        拼接解压缩包的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.DecompressPackage.value,
            "payload": {
                "general": {},
                "extend": {
                    # "install_config": self.init_hdfs_config['install'],
                    "version": self.ticket_data["db_version"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_install_haproxy_payload(self, **kwargs) -> dict:
        """
        拼接安装HAProxy的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.InstallHaproxy.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "install": self.init_hdfs_config["install"],
                    "version": self.ticket_data["db_version"],
                    "host_map": self.ticket_data["all_ip_hosts"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nn1_ip": self.ticket_data["nn1_ip"],
                    "nn2_ip": self.ticket_data["nn2_ip"],
                    "http_port": self.ticket_data["http_port"],
                    "rpc_port": self.ticket_data["rpc_port"],
                    # 当前未传参用户名
                    "haproxy_passwd": self.ticket_data["haproxy_passwd"],
                },
            },
        }

    def get_update_host_mapping_payload(self, **kwargs) -> dict:
        """
        拼接更新主机映射的payload参数
        """
        update_ip_hosts = dict()
        for new_dn_ip in self.ticket_data["new_dn_ips"]:
            update_ip_hosts[new_dn_ip] = self.ticket_data["all_ip_hosts"][new_dn_ip]
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateHostMapping.value,
            "payload": {
                "general": {},
                "extend": {
                    "host_map": update_ip_hosts,
                },
            },
        }

    def get_add_exclude_payload(self, **kwargs) -> dict:
        """
        拼接缩容时添加主机到exclude的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateDfsHost.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "data_node_hosts": ",".join(self.ticket_data["dn_hosts"]),
                    "conf_file": self.ticket_data["dfs_exclude_file"],
                    "operation": UpdateDfsHostOperation.Add.value,
                },
            },
        }

    def get_remove_exclude_payload(self, **kwargs) -> dict:
        """
        拼接缩容时删除主机到exclude的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateDfsHost.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "data_node_hosts": ",".join(self.ticket_data["dn_hosts"]),
                    "conf_file": self.ticket_data["dfs_exclude_file"],
                    "operation": UpdateDfsHostOperation.Remove.value,
                },
            },
        }

    def get_remove_include_payload(self, **kwargs) -> dict:
        """
        拼接缩容时删除主机到include的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateDfsHost.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "data_node_hosts": ",".join(self.ticket_data["dn_hosts"]),
                    "conf_file": self.ticket_data["dfs_include_file"],
                    "operation": UpdateDfsHostOperation.Remove.value,
                },
            },
        }

    def get_add_include_payload(self, **kwargs) -> dict:
        """
        拼接扩容时添加主机到include的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateDfsHost.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "data_node_hosts": ",".join(self.ticket_data["dn_hosts"]),
                    "conf_file": self.ticket_data["dfs_include_file"],
                    "operation": UpdateDfsHostOperation.Add.value,
                },
            },
        }

    def get_refresh_nodes_payload(self, **kwargs) -> dict:
        """
        拼接刷新数据节点的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.RefreshNodes.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "version": self.ticket_data["db_version"],
                },
            },
        }

    def get_check_decommission_payload(self, **kwargs) -> dict:
        """
        拼接检查节点是否退役的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.CheckDecommission.value,
            "payload": {
                "general": {},
                "extend": {
                    "data_node_hosts": ",".join(self.ticket_data["dn_hosts"]),
                    "version": self.ticket_data["db_version"],
                    "http_port": self.ticket_data["http_port"],
                    "haproxy_passwd": self.ticket_data["haproxy_passwd"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_generate_key_payload(self, **kwargs) -> dict:
        """
        拼接生成密钥的payload参数
        """
        return self.__gen_only_ip_payload(HdfsDBActuatorActionEnum.GenerateKey, kwargs["ip"])

    def get_write_key_payload(self, **kwargs) -> dict:
        """
        拼接写入密钥的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.WriteKey.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "key": kwargs["trans_data"]["generate_key_info"]["key"],
                    "host": kwargs["ip"],
                },
            },
        }

    def get_remote_copy_dir_payload(self, **kwargs) -> dict:
        """
        拼接写入密钥的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.RemoteCopyDir.value,
            "payload": {
                "general": {},
                "extend": {
                    "cluster_name": self.ticket_data["cluster_name"],
                    "dest": kwargs["transfer_target_ip"],
                    "host": kwargs["ip"],
                    "component": kwargs["hdfs_role"],
                },
            },
        }

    def get_dynamic_render_cluster_config_payload(self, **kwargs) -> dict:
        """
        拼接 动态IP 渲染HDFS集群配置的payload参数，用于替换流程的渲染集群配置
        """
        hdfs_config = copy.deepcopy(self.init_hdfs_config)
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.RenderConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "hdfs-site": hdfs_config["hdfs-site"],
                    "core-site": hdfs_config["core-site"],
                    "install": hdfs_config["install"],
                    "version": self.ticket_data["db_version"],
                    "host_map": kwargs["trans_data"]["cur_all_ip_hosts"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nn1_ip": kwargs["trans_data"]["cur_nn1_ip"],
                    "nn2_ip": kwargs["trans_data"]["cur_nn2_ip"],
                    "zk_ips": ",".join(kwargs["trans_data"]["cur_zk_ips"]),
                    "jn_ips": ",".join(kwargs["trans_data"]["cur_jn_ips"]),
                    "dn_ips": ",".join(kwargs["trans_data"]["cur_dn_ips"]),
                    "http_port": self.ticket_data["http_port"],
                    "rpc_port": self.ticket_data["rpc_port"],
                },
            },
        }

    def get_check_active_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.CheckActive.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "nn1_ip": kwargs["trans_data"]["cur_nn1_ip"],
                    "nn2_ip": kwargs["trans_data"]["cur_nn2_ip"],
                },
            },
        }

    def get_update_zk_config_payload(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.Hdfs.value,
            "action": HdfsDBActuatorActionEnum.UpdateZooKeeperConfig.value,
            "payload": {
                "general": {},
                "extend": {
                    "host": kwargs["ip"],
                    "cluster_name": self.ticket_data["cluster_name"],
                    "old_zk_ips": ",".join(self.ticket_data["old_zk_ips"]),
                    "new_zk_ips": ",".join(self.ticket_data["new_zk_ips"]),
                },
            },
        }


def gen_host_name_by_role(ip: str, role: str) -> str:
    return role + "-" + ip.replace(".", "-")


def get_cluster_config(bk_biz_id: str, cluster_domain: str, db_version: str, conf_type: ConfigTypeEnum) -> Any:
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": NameSpaceEnum.Hdfs,
            "format": FormatType.MAP,
            "method": ReqType.GENERATE_AND_PUBLISH,
        }
    )
    return data["content"]


def get_cluster_all_ip_from_meta(cluster_id: int) -> list:
    cluster = Cluster.objects.get(id=cluster_id)
    storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
    return storage_ips


# 获取不同单据类型需要操作转移模块到机器类型列表
def get_machine_list(ticket_type: str, replace_dn=False, replace_master=False) -> list:
    machine_list = []
    if ticket_type == TicketType.HDFS_APPLY.value:
        machine_list = [
            {
                "machine_type": MachineType.HDFS_MASTER.value,
                "ips_var_name": HdfsApplyContext.get_master_ips_var_name(),
            },
            {
                "machine_type": MachineType.HDFS_DATANODE.value,
                "ips_var_name": HdfsApplyContext.get_dn_ips_var_name(),
            },
        ]
    elif ticket_type == TicketType.HDFS_SCALE_UP.value:
        machine_list = [
            {
                "machine_type": MachineType.HDFS_DATANODE.value,
                "ips_var_name": HdfsApplyContext.get_new_dn_ips_var_name(),
            },
        ]
    elif ticket_type == TicketType.HDFS_REPLACE.value:
        if replace_dn:
            machine_list.append(
                {
                    "machine_type": MachineType.HDFS_DATANODE.value,
                    "ips_var_name": HdfsReplaceContext.get_new_dn_ips_var_name(),
                }
            )
        if replace_master:
            machine_list.append(
                {
                    "machine_type": MachineType.HDFS_MASTER.value,
                    "ips_var_name": HdfsReplaceContext.get_new_master_ips_var_name(),
                }
            )
    else:
        machine_list = []
    return machine_list


# 从meta中获取需要被完全替换的IP
def get_replace_ip_from_meta(ticket_data: dict) -> list:
    replace_master_ip_set = set()
    if ticket_data["old_nn_ips"]:
        for nn_ip in ticket_data["old_nn_ips"]:
            if (
                nn_ip in ticket_data["zk_ips"] + ticket_data["new_master_ips"]
                and nn_ip not in ticket_data["old_zk_ips"]
            ):
                pass
            else:
                replace_master_ip_set.add(nn_ip)
    if ticket_data["old_zk_ips"]:
        for zk_ip in ticket_data["old_zk_ips"]:
            if (
                zk_ip in ticket_data["nn_ips"] + ticket_data["new_master_ips"]
                and zk_ip not in ticket_data["old_nn_ips"]
            ):
                pass
            else:
                replace_master_ip_set.add(zk_ip)
    return ticket_data["del_dn_ips"] + list(replace_master_ip_set)
