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


import base64
import logging

from backend import constants
from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import DBActuatorTypeEnum, DorisActuatorActionEnum, MySQLPrivComponent
from backend.flow.utils.doris.consts import DorisMetaOperation, DorisNodeOperation
from backend.flow.utils.doris.doris_context_dataclass import DorisResourceContext

logger = logging.getLogger("flow")


class DorisActPayload(object):
    """
    定义Doris不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict):
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data

    # 定义常规extend参数
    def get_common_extend(self, **kwargs) -> dict:
        return {
            "host": kwargs["ip"],
            "cluster_name": self.ticket_data["cluster_name"],
            "version": self.ticket_data["db_version"],
            "role": kwargs["role"],
            "username": self.ticket_data["username"],
            "password": self.ticket_data["password"],
            "http_port": self.ticket_data["http_port"],
            "query_port": self.ticket_data["query_port"],
            # "master_fe_ip": self.ticket_data["master_fe_ip"],
        }

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
        """
        拼接 安装supervisor payload参数
        """
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
        """
        拼接 渲染Doris集群配置 payload参数
        """
        extend_dict = {
            "fe_conf": self.ticket_data["fe_conf"],
            "be_conf": self.ticket_data["be_conf"],
            "master_fe_ip": self.ticket_data["master_fe_ip"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.RenderConfig.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    def get_start_fe_by_helper_payload(self, **kwargs) -> dict:
        """
        拼接 通过helper初始化启动FE payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.StartFeByHelper.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    def get_decompress_doris_pkg_payload(self, **kwargs) -> dict:
        """
        拼接 解压缩Doris安装包 payload参数
        """
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

    # 添加节点到元数据
    def get_add_metadata_payload(self, **kwargs) -> dict:
        """
        拼接 集群添加节点元数据 payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "operation": DorisMetaOperation.Add.value,
            "host_map": self.ticket_data["host_meta_map"],
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.UpdateMetadata.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    # 元数据管理：删除节点
    def get_drop_metadata_payload(self, **kwargs) -> dict:
        """
        拼接 集群Drop节点元数据 payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "operation": DorisMetaOperation.Drop.value,
            "host_map": self.ticket_data["host_meta_map"],
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.UpdateMetadata.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    # 元数据管理：强制删除节点 适用于BE节点
    def get_force_drop_metadata_payload(self, **kwargs) -> dict:
        """
        拼接 集群强制下线节点元数据 payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "operation": DorisMetaOperation.ForceDrop.value,
            "host_map": self.ticket_data["host_meta_map"],
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.UpdateMetadata.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    # 元数据管理：退役BE节点
    def get_decommission_metadata_payload(self, **kwargs) -> dict:
        """
        拼接 集群退役BE节点元数据操作 payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "operation": DorisMetaOperation.Decommission.value,
            "host_map": self.ticket_data["host_meta_map"],
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.UpdateMetadata.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    def get_stop_process_payload(self, **kwargs) -> dict:
        """
        拼接 集群停止服务进程 payload参数
        """
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
        """
        拼接 初始化集群认证配置 payload参数
        """
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
                    "root_password": self.ticket_data["root_password"],
                    "admin_password": self.ticket_data["admin_password"],
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
        """
        拼接 集群启动服务进程 payload参数
        """
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

    def get_check_decommission_payload(self, **kwargs) -> dict:
        """
        拼接检查节点是否退役的payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "host_map": self.ticket_data["host_meta_map"],
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.CheckDecommission.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    def get_check_start_payload(self, **kwargs) -> dict:
        """
        拼接 检查FE节点是否正常启动 payload参数
        """
        extend_dict = {
            "master_fe_ip": self.ticket_data["master_fe_ip"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.CheckProcessStart.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    # 元数据管理：Doris绑定远程存储资源
    def get_create_resource_payload(self, **kwargs) -> dict:
        """
        拼接 集群创建存储资源 payload参数
        """
        if self.ticket_data["res"]["bucket_name"]:
            bucket_name = self.ticket_data["res"]["bucket_name"]
        else:
            bucket_name = kwargs["trans_data"][DorisResourceContext.get_bucket_var_name()]
        extend_dict = {
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
            "resource_name": self.ticket_data["res"]["name"],
            "master_fe_ip": self.ticket_data["master_fe_ip"],
            "region": self.ticket_data["res"]["region"],
            "bucket_name": bucket_name,
            # 暂时冗余留空，由actor决定使用内网域名还是公网域名
            "endpoint": "",
            "root_path": self.ticket_data["res"]["root_path"],
            "access_key": self.ticket_data["res"]["access_key"],
            "secret_key": self.ticket_data["res"]["secret_key"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.CreateResource.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }

    def get_drop_resource_payload(self, **kwargs) -> dict:
        """
        拼接 集群删除存储资源 payload参数
        """
        extend_dict = {
            "root_password": self.ticket_data["root_password"],
            "admin_password": self.ticket_data["admin_password"],
            "resource_name": self.ticket_data["res"]["name"],
            "master_fe_ip": self.ticket_data["master_fe_ip"],
        }
        return {
            "db_type": DBActuatorTypeEnum.Doris.value,
            "action": DorisActuatorActionEnum.DropResource.value,
            "payload": {
                "general": {},
                "extend": dict(**(self.get_common_extend(**kwargs)), **extend_dict),
            },
        }


def get_key_by_account_id(account_id: str, port: int = 0) -> dict:
    """
    通过account_id获取腾讯云的ak/sk
    - 只从密码服务中获取
    - 获取不到时返回空串，不报错
    """
    auth = {"access_key": "", "secret_key": "", "appid": ""}
    # 从密码服务获取腾讯云的appid. 存储桶名及策略需用到
    query_appid_params = {
        "instances": [{"ip": account_id, "port": port, "bk_cloud_id": constants.DEFAULT_BK_CLOUD_ID}],
        "users": [
            {"username": MySQLPrivComponent.DORIS_CLOUD_APP_ID.value, "component": ClusterType.Doris},
        ],
    }
    appid_data = DBPrivManagerApi.get_password(query_appid_params)
    if appid_data["items"]:
        auth["appid"] = base64.b64decode(appid_data["items"][0]["password"]).decode("utf-8")
    else:
        logger.error("{} cannot get auth info appid from password service".format(account_id))
    # 从密码服务获取用户名，若返回空串，则密码服务未存
    query_ak_params = {
        "instances": [{"ip": account_id, "port": port, "bk_cloud_id": constants.DEFAULT_BK_CLOUD_ID}],
        "users": [
            {"username": account_id, "component": ClusterType.Doris},
        ],
    }
    ak_data = DBPrivManagerApi.get_password(query_ak_params)
    # 判断密码服务是否有对应item
    if not ak_data["items"]:
        logger.error("{} cannot get auth info access_key from password service".format(account_id))
        return auth
    else:
        # 默认返回第一个item
        auth["access_key"] = base64.b64decode(ak_data["items"][0]["password"]).decode("utf-8")
        query_sk_params = {
            "instances": [{"ip": account_id, "port": port, "bk_cloud_id": constants.DEFAULT_BK_CLOUD_ID}],
            "users": [
                {"username": auth["access_key"], "component": ClusterType.Doris},
            ],
        }
        sk_data = DBPrivManagerApi.get_password(query_sk_params)
        if not sk_data["items"]:
            logger.error("{} cannot get auth info secret_key from password service".format(account_id))
        else:
            auth["secret_key"] = base64.b64decode(sk_data["items"][0]["password"]).decode("utf-8")

    return auth
