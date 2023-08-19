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
import logging.config
import time
from typing import Any

from django.utils.translation import ugettext as _

from backend import env
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType, ReqType
from backend.configuration.constants import DBType
from backend.configuration.models.system import SystemSettings
from backend.constants import BACKUP_SYS_STATUS, IP_PORT_DIVIDER
from backend.db_meta import api as metaApi
from backend.db_meta.api.cluster import nosqlcomm
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.redis.redis_dts.util import (
    is_predixy_proxy_type,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.db_services.version.constants import PredixyVersion, TwemproxyVersion
from backend.flow.consts import (
    DEFAULT_CONFIG_CONFIRM,
    DEFAULT_DB_MODULE_ID,
    DEFAULT_REDIS_START_PORT,
    ConfigDefaultEnum,
    ConfigFileEnum,
    ConfigTypeEnum,
    DBActuatorTypeEnum,
    DirEnum,
    MediumEnum,
    NameSpaceEnum,
    RedisActuatorActionEnum,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")
apply_list = [
    TicketType.REDIS_SINGLE_APPLY.value,
    TicketType.REDIS_CLUSTER_APPLY.value,
    TicketType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
    TicketType.REDIS_CLUSTER_TYPE_UPDATE.value,
]
global_list = [TicketType.REDIS_KEYS_DELETE.value]
proxy_scale_list = [
    TicketType.PROXY_SCALE_UP.value,
    TicketType.PROXY_SCALE_DOWN.value,
]
redis_scale_list = [
    TicketType.REDIS_SCALE_UPDOWN.value,
]
cutoff_list = [
    TicketType.REDIS_CLUSTER_CUTOFF.value,
    TicketType.REDIS_CLUSTER_ADD_SLAVE.value,
]
tool_list = [TicketType.REDIS_DATA_STRUCTURE.value, TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.value]
twemproxy_cluster_type_list = [
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTwemproxyTendisplusIns.value,
]
predixy_cluster_type_list = [
    ClusterType.TendisPredixyTendisplusCluster.value,
    ClusterType.TendisPredixyRedisCluster.value,
]


class RedisActPayload(object):
    """
    定义redis不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        """
        @param ticket_data 单据信息(全局信息，global_data)
        @param cluster 需要操作的集群信息(cluster+trans_data)
        """
        self.redis_pkg = None
        self.proxy_pkg = None
        self.namespace = None
        self.proxy_version = None
        self.init_proxy_config = None
        self.ticket_data = ticket_data
        self.cluster = cluster
        self.bk_biz_id = str(self.ticket_data["bk_biz_id"])
        self.tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )

        self.__init_dbconfig_params()
        if self.ticket_data["ticket_type"] in apply_list + cutoff_list + tool_list:
            self.account = self.__get_define_config(NameSpaceEnum.Common, ConfigFileEnum.OS, ConfigTypeEnum.OSConf)
            if "db_version" in self.ticket_data:
                self.init_redis_config = self.__get_define_config(
                    self.namespace, self.ticket_data["db_version"], ConfigTypeEnum.DBConf
                )
                self.init_proxy_config = self.__get_define_config(
                    self.namespace, self.proxy_version, ConfigTypeEnum.ProxyConf
                )
        if self.ticket_data["ticket_type"] in global_list:
            self.global_config = self.__get_define_config(
                NameSpaceEnum.Common, ConfigFileEnum.Redis, ConfigTypeEnum.ActConf
            )
        if self.ticket_data["ticket_type"] in redis_scale_list + proxy_scale_list:
            self.account = self.__get_define_config(NameSpaceEnum.Common, ConfigFileEnum.OS, ConfigTypeEnum.OSConf)

    def __init_dbconfig_params(self) -> Any:
        if "cluster_type" in self.cluster:
            self.namespace = self.cluster["cluster_type"]
        elif "cluster_type" in self.ticket_data:
            self.namespace = self.ticket_data["cluster_type"]

        if self.namespace == ClusterType.TendisTwemproxyRedisInstance.value:
            self.proxy_version = ConfigFileEnum.Twemproxy
        elif self.namespace == ClusterType.TwemproxyTendisSSDInstance.value:
            self.proxy_version = ConfigFileEnum.Twemproxy
        elif self.namespace == ClusterType.TendisPredixyTendisplusCluster.value:
            self.proxy_version = ConfigFileEnum.Predixy

    def __get_define_config(self, namespace: str, conf_file: str, conf_type: str) -> Any:
        """获取一些全局的参数配置"""
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": self.bk_biz_id,
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def set_redis_config(self, clusterMap: dict) -> Any:
        conf_items = []
        for conf_name, conf_value in clusterMap["conf"].items():
            conf_items.append({"conf_name": conf_name, "conf_value": conf_value, "op_type": OpType.UPDATE})
        data = DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": clusterMap["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": self.namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["domain_name"],
            }
        )
        return data

    def delete_redis_config(self, clusterMap: dict):
        conf_items = [
            {"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name, _ in clusterMap["conf"].items()
        ]
        data = DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": self.cluster["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": self.namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": self.cluster["domain_name"],
            }
        )
        return data

    def redis_conf_names_by_cluster_type(self, cluster_type: str) -> list:
        conf_names: list = ["requirepass"]
        if is_redis_instance_type(cluster_type) or is_tendisplus_instance_type(cluster_type):
            conf_names.append("cluster-enabled")
        if is_redis_instance_type(cluster_type) or is_tendisssd_instance_type(cluster_type):
            conf_names.append("maxmemory")
            conf_names.append("databases")
        return conf_names

    def dts_swap_redis_config(self, clusterMap: dict):
        """交换源集群和目标集群的redis配置"""
        logger.info(_("开始交换源集群和目标集群的redis配置"))
        logger.info(_("获取源集群:{} redis配置").format(clusterMap["src_cluster_domain"]))
        src_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(clusterMap["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["src_cluster_domain"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": clusterMap["src_cluster_version"],
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": clusterMap["src_cluster_type"],
                "format": FormatType.MAP,
            }
        )
        src_conf_names = self.redis_conf_names_by_cluster_type(clusterMap["src_cluster_type"])
        src_conf_items = []
        for conf_name in src_conf_names:
            if conf_name in src_resp["content"]:
                src_conf_items.append(
                    {"conf_name": conf_name, "conf_value": src_resp["content"][conf_name], "op_type": OpType.UPDATE}
                )

        logger.info(_("获取目标集群:{} redis配置").format(clusterMap["dst_cluster_domain"]))
        dst_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(clusterMap["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["dst_cluster_domain"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": clusterMap["dst_cluster_version"],
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": clusterMap["dst_cluster_type"],
                "format": FormatType.MAP,
            }
        )
        dst_conf_names = self.redis_conf_names_by_cluster_type(clusterMap["dst_cluster_type"])
        dst_conf_items = []
        for conf_name in dst_conf_names:
            if conf_name in dst_resp["content"]:
                dst_conf_items.append(
                    {"conf_name": conf_name, "conf_value": dst_resp["content"][conf_name], "op_type": OpType.UPDATE}
                )

        upsert_param = {
            "conf_file_info": {
                "conf_file": "",  # 需要替换成真实值
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": "",  # 需要替换成真实值
            },
            "conf_items": [],  # 需要替换成真实值
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "confirm": DEFAULT_CONFIG_CONFIRM,
            "req_type": ReqType.SAVE_AND_PUBLISH,
            "bk_biz_id": str(clusterMap["bk_biz_id"]),
            "level_name": LevelName.CLUSTER,
            "level_value": "",  # 需要替换成真实值
        }

        if src_conf_names != dst_conf_names:
            # 源集群、目标集群类型有变化, 先删除原有的配置,再更新配置,避免残留
            src_remove_items = [{"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name in src_conf_names]
            upsert_param["conf_file_info"]["namespace"] = clusterMap["src_cluster_type"]
            upsert_param["conf_file_info"]["conf_file"] = clusterMap["src_cluster_version"]
            upsert_param["conf_items"] = src_remove_items
            upsert_param["level_value"] = clusterMap["src_cluster_domain"]
            logger.info(_("删除源集群:{} redis配置,upsert_param:{}".format(clusterMap["src_cluster_domain"], upsert_param)))
            DBConfigApi.upsert_conf_item(upsert_param)

            dst_remove_items = [{"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name in dst_conf_names]
            upsert_param["conf_file_info"]["namespace"] = clusterMap["dst_cluster_type"]
            upsert_param["conf_file_info"]["conf_file"] = clusterMap["dst_cluster_version"]
            upsert_param["conf_items"] = dst_remove_items
            upsert_param["level_value"] = clusterMap["dst_cluster_domain"]
            logger.info(_("删除目标集群:{} redis配置,upsert_param:{}").format(clusterMap["dst_cluster_domain"], upsert_param))
            DBConfigApi.upsert_conf_item(upsert_param)
        # 源集群 写入目标集群的配置
        upsert_param["conf_file_info"]["namespace"] = clusterMap["dst_cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = clusterMap["dst_cluster_version"]
        upsert_param["conf_items"] = dst_conf_items
        upsert_param["level_value"] = clusterMap["src_cluster_domain"]
        logger.info(_("更新源集群redis配置 为 目标集群的配置,upsert_param:{}".format(upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)
        # 目标集群 写入源集群的配置
        upsert_param["conf_file_info"]["namespace"] = clusterMap["src_cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = clusterMap["src_cluster_version"]
        upsert_param["conf_items"] = src_conf_items
        upsert_param["level_value"] = clusterMap["dst_cluster_domain"]
        logger.info(_("更新目标集群redis配置 为 源集群的配置,upsert_param:{}".format(upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)

    def delete_proxy_config(self, clusterMap: dict):
        conf_items = [
            {"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name, _ in clusterMap["conf"].items()
        ]
        data = DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": self.proxy_version,
                    "conf_type": ConfigTypeEnum.ProxyConf,
                    "namespace": self.namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": self.cluster["domain_name"],
            }
        )
        return data

    def __get_cluster_config(self, domain_name: str, db_version: str, conf_type: str) -> Any:
        """
        获取已部署的实例配置
        """
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": conf_type,
                "namespace": self.namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def set_proxy_config(self, clusterMap: dict) -> Any:
        """
        集群初始化的时候twemproxy没做变动，直接写入集群就OK
        """
        conf_items = []
        for conf_name, conf_value in clusterMap["conf"].items():
            conf_items.append({"conf_name": conf_name, "conf_value": conf_value, "op_type": OpType.UPDATE})
        data = DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": self.proxy_version,
                    "conf_type": ConfigTypeEnum.ProxyConf,
                    "namespace": self.namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["domain_name"],
            }
        )
        return data

    def dts_swap_proxy_config_version(self, clusterMap: dict) -> Any:
        """
        交换源集群和目标集群 dbconfig 中的proxy版本信息,有可能 twemproxy集群 切换到 predixy集群 s
        """
        proxy_conf_names = ["password", "redis_password", "port"]
        logger.info(_("交换源集群和目标集群 dbconfig 中的proxy版本信息"))
        logger.info(_("获取源集群:{} proxy配置").format(clusterMap["src_cluster_domain"]))
        src_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(clusterMap["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["src_cluster_domain"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": clusterMap["src_proxy_version"],
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": clusterMap["src_cluster_type"],
                "format": FormatType.MAP,
            }
        )
        src_conf_upsert_items = []
        for conf_name in proxy_conf_names:
            src_conf_upsert_items.append(
                {"conf_name": conf_name, "conf_value": src_resp["content"][conf_name], "op_type": OpType.UPDATE}
            )
        logger.info(_("src_conf_upsert_items==>{}".format(src_conf_upsert_items)))

        logger.info(_("获取目标集群:{} proxy配置").format(clusterMap["dst_cluster_domain"]))
        dst_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(clusterMap["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": clusterMap["dst_cluster_domain"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": clusterMap["dst_proxy_version"],
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": clusterMap["dst_cluster_type"],
                "format": FormatType.MAP,
            }
        )
        dst_conf_upsert_items = []
        for conf_name in proxy_conf_names:
            dst_conf_upsert_items.append(
                {"conf_name": conf_name, "conf_value": dst_resp["content"][conf_name], "op_type": OpType.UPDATE}
            )
        logger.info(_("dst_conf_upsert_items==>{}".format(dst_conf_upsert_items)))

        upsert_param = {
            "conf_file_info": {
                "conf_file": "",  # 需要替换成真实值
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": "",  # 需要替换成真实值
            },
            "conf_items": [],  # 需要替换成真实值
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "confirm": DEFAULT_CONFIG_CONFIRM,
            "req_type": ReqType.SAVE_AND_PUBLISH,
            "bk_biz_id": str(clusterMap["bk_biz_id"]),
            "level_name": LevelName.CLUSTER,
            "level_value": "",  # 需要替换成真实值
        }

        remove_items = []
        for conf_name in proxy_conf_names:
            remove_items.append({"conf_name": conf_name, "op_type": OpType.REMOVE})
        # 删除源集群的proxy配置
        src_remove_param = copy.deepcopy(upsert_param)
        src_remove_param["conf_file_info"]["conf_file"] = clusterMap["src_proxy_version"]
        src_remove_param["conf_file_info"]["namespace"] = clusterMap["src_cluster_type"]
        src_remove_param["conf_items"] = remove_items
        src_remove_param["level_value"] = clusterMap["src_cluster_domain"]
        logger.info(
            _("删除源集群:{} proxy配置,src_remove_param:{}").format(clusterMap["src_cluster_domain"], src_remove_param)
        )
        DBConfigApi.upsert_conf_item(src_remove_param)

        # 删除目标集群的proxy配置
        dst_remove_param = copy.deepcopy(upsert_param)
        dst_remove_param["conf_file_info"]["conf_file"] = clusterMap["dst_proxy_version"]
        dst_remove_param["conf_file_info"]["namespace"] = clusterMap["dst_cluster_type"]
        dst_remove_param["conf_items"] = remove_items
        dst_remove_param["level_value"] = clusterMap["dst_cluster_domain"]
        logger.info(
            _("删除目标集群:{} proxy配置,dst_remove_param:{}").format(clusterMap["dst_cluster_domain"], dst_remove_param)
        )
        DBConfigApi.upsert_conf_item(dst_remove_param)

        time.sleep(2)

        # 更新源集群的proxy版本信息
        src_upsert_param = copy.deepcopy(upsert_param)
        src_upsert_param["conf_file_info"]["conf_file"] = clusterMap["dst_proxy_version"]  # 替换成目标集群的proxy版本
        src_upsert_param["conf_file_info"]["namespace"] = clusterMap["dst_cluster_type"]
        src_upsert_param["conf_items"] = src_conf_upsert_items
        src_upsert_param["level_value"] = clusterMap["src_cluster_domain"]
        logger.info(
            _("更新源集群:{} dbconfig 中proxy版本等信息,src_upsert_param:{}").format(
                clusterMap["src_cluster_domain"], src_upsert_param
            )
        )
        DBConfigApi.upsert_conf_item(src_upsert_param)

        # 更新目标集群的proxy版本信息
        dst_upsert_param = copy.deepcopy(upsert_param)
        dst_upsert_param["conf_file_info"]["conf_file"] = clusterMap["src_proxy_version"]  # 替换成源集群的proxy版本
        dst_upsert_param["conf_file_info"]["namespace"] = clusterMap["src_cluster_type"]
        dst_upsert_param["conf_items"] = dst_conf_upsert_items
        dst_upsert_param["level_value"] = clusterMap["dst_cluster_domain"]
        logger.info(
            _("更新目标集群:{} dbconfig 中proxy版本等信息,dst_upsert_param:{}").format(
                clusterMap["dst_cluster_domain"], dst_upsert_param
            )
        )
        DBConfigApi.upsert_conf_item(dst_upsert_param)

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        初始化机器
        """
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": RedisActuatorActionEnum.Sysinit.value,
            "payload": {"user": self.account["user"], "password": self.account["user_pwd"]},
        }

    def get_install_predixy_payload(self, **kwargs) -> dict:
        self.proxy_pkg = Package.get_latest_package(
            version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
        )
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Predixy.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "dbconfig": self.init_proxy_config,
                "mediapkg": {
                    "pkg": self.proxy_pkg.name,
                    "pkg_md5": self.proxy_pkg.md5,
                },
            },
        }

    def add_predixy_payload(self, **kwargs) -> dict:
        """
        predixy扩容
        """
        self.proxy_pkg = Package.get_latest_package(
            version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
        )
        proxy_config = self.__get_cluster_config(
            self.cluster["domain_name"], self.proxy_version, ConfigTypeEnum.ProxyConf
        )

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Predixy.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "ip": kwargs["ip"],
                "port": self.cluster["proxy_port"],
                "predixypasswd": proxy_config["password"],
                "redispasswd": proxy_config["redis_password"],
                "servers": self.cluster["servers"],
                "dbconfig": proxy_config,
                "mediapkg": {
                    "pkg": self.proxy_pkg.name,
                    "pkg_md5": self.proxy_pkg.md5,
                },
            },
        }

    def get_install_twemproxy_payload(self, **kwargs) -> dict:
        """
        初始化twemproxy
        """
        self.proxy_pkg = Package.get_latest_package(
            version=TwemproxyVersion.TwemproxyLatest, pkg_type=MediumEnum.Twemproxy, db_type=DBType.Redis
        )

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "pkg": self.proxy_pkg.name,
                "pkg_md5": self.proxy_pkg.md5,
                "data_dirs": ConfigDefaultEnum.DATA_DIRS,
                "conf_configs": self.init_proxy_config,
            },
        }

    def add_twemproxy_payload(self, **kwargs) -> dict:
        """
        twemproxy扩容
        """
        self.proxy_pkg = Package.get_latest_package(
            version=TwemproxyVersion.TwemproxyLatest, pkg_type=MediumEnum.Twemproxy, db_type=DBType.Redis
        )
        proxy_config = self.__get_cluster_config(
            self.cluster["domain_name"], self.proxy_version, ConfigTypeEnum.ProxyConf
        )

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "pkg": self.proxy_pkg.name,
                "pkg_md5": self.proxy_pkg.md5,
                "redis_password": proxy_config["redis_password"],
                "password": proxy_config["password"],
                "port": self.cluster["proxy_port"],
                "data_dirs": ConfigDefaultEnum.DATA_DIRS,
                "db_type": self.cluster["cluster_type"],
                "conf_configs": proxy_config,
                # 以下为流程中需要补充的参数
                "ip": kwargs["ip"],
                "servers": self.cluster["servers"],
            },
        }

    def get_install_redis_payload(self, **kwargs) -> dict:
        """
        安装redisredis
        """
        self.__get_redis_pkg(self.ticket_data["cluster_type"], self.ticket_data["db_version"])
        redis_conf = copy.deepcopy(self.init_redis_config)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
                "pkg": self.redis_pkg.name,
                "pkg_md5": self.redis_pkg.md5,
                "password": self.ticket_data["redis_pwd"],
                "databases": self.ticket_data["databases"],
                "db_type": self.ticket_data["cluster_type"],
                "maxmemory": self.ticket_data["maxmemory"],
                "data_dirs": ConfigDefaultEnum.DATA_DIRS,
                "ports": [],
                "redis_conf_configs": redis_conf,
                "inst_num": self.ticket_data["shard_num"] // self.ticket_data["group_num"],
                # 以下为流程中需要补充的参数
                "ip": kwargs["ip"],
                "start_port": DEFAULT_REDIS_START_PORT,
            },
        }

    def get_slaveof_redis_payload(self, **kwargs) -> dict:
        """
        redis建立主从关系
        """
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.REPLICA_BATCH.value,
            "payload": {},
        }

    def get_clustermeet_slotsassign_payload(self, **kwargs) -> dict:
        """
        rediscluster 集群建立
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": RedisActuatorActionEnum.CLUSTER_MEET.value,
            "payload": {
                "password": params["password"],
                "slots_auto_assign": True,
            },
        }

    def keys_extract_payload(self, **kwargs) -> dict:
        """
        提取keys
        """
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        ip = kwargs["ip"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendis.value + "_" + RedisActuatorActionEnum.KEYS_PATTERN.value,
            "payload": {
                "pkg": tools_pkg.name,
                "pkg_md5": tools_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "fileserver": self.ticket_data["fileserver"],
                "path": self.cluster["path"],
                "domain": self.cluster["domain_name"],
                "key_white_regex": self.cluster["white_regex"],
                "key_black_regex": self.cluster["black_regex"],
                "ip": ip,
                "ports": self.cluster[ip],
            },
        }

    def keys_delete_regex_payload(self, **kwargs) -> dict:
        """
        按正则删除keys
        """
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        ip = kwargs["ip"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendis.value + "_" + RedisActuatorActionEnum.KEYS_DELETE_REGEX.value,
            "payload": {
                "pkg": tools_pkg.name,
                "pkg_md5": tools_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "fileserver": self.ticket_data["fileserver"],
                "path": self.cluster["path"],
                "domain": self.cluster["domain_name"],
                "key_white_regex": self.cluster["white_regex"],
                "key_black_regex": self.cluster["black_regex"],
                "ip": ip,
                "ports": self.cluster[ip],
                "is_keys_to_be_del": True,
                "delete_rate": int(self.global_config["delete_rate"]),
                "tendisplus_delete_rate": int(self.global_config["tendisplus_delete_rate"]),
            },
        }

    def keys_delete_files_payload(self, **kwargs) -> dict:
        """
        按文件方式删除keys
        """
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        proxy_config = self.__get_cluster_config(
            self.cluster["domain_name"], self.proxy_version, ConfigTypeEnum.ProxyConf
        )

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendis.value + "_" + RedisActuatorActionEnum.KEYS_DELETE_FILES.value,
            "payload": {
                "pkg": tools_pkg.name,
                "pkg_md5": tools_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "fileserver": self.ticket_data["fileserver"],
                "path": self.cluster["path"],
                "domain": self.cluster["domain_name"],
                "delete_rate": int(self.global_config["delete_rate"]),
                "proxy_port": int(proxy_config["port"]),
                "proxy_password": proxy_config["password"],
                "tendis_type": self.cluster["cluster_type"],
                "tendisplus_delete_rate": int(self.global_config["tendisplus_delete_rate"]),
            },
        }

    def redis_cluster_backup_payload(self, **kwargs) -> dict:
        """
        redis集群备份
        """
        ip = kwargs["ip"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Backup.value,
            "payload": {
                "bk_biz_id": self.bk_biz_id,
                "ip": ip,
                "ports": self.cluster[ip],
                "backup_type": self.cluster["backup_type"],
                "domain": self.cluster["domain_name"],
                "without_to_backup_sys": not BACKUP_SYS_STATUS,
            },
        }

    def proxy_operate_payload(self, **kwargs) -> dict:
        """
        proxy启停、下架
        """
        action = ""
        if self.cluster["cluster_type"] in twemproxy_cluster_type_list:
            action = DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.Operate.value
        elif self.cluster["cluster_type"] in predixy_cluster_type_list:
            action = DBActuatorTypeEnum.Predixy.value + "_" + RedisActuatorActionEnum.Operate.value
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": action,
            "payload": {},
        }

    def redis_shutdown_payload(self, **kwargs) -> dict:
        """
        redis下架
        """
        ip = kwargs["ip"]
        ports = self.cluster[ip]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            "payload": {"ip": ip, "ports": ports},
        }

    def redis_flush_data_payload(self, **kwargs) -> dict:
        """
        redis清档
        """
        ip = kwargs["ip"]
        redis_config = self.__get_cluster_config(
            self.cluster["domain_name"], self.cluster["db_version"], ConfigTypeEnum.DBConf
        )

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.FlushData.value,
            "payload": {
                "ip": ip,
                "db_type": self.cluster["cluster_type"],
                "ports": self.cluster[ip],
                "is_force": self.cluster["force"],
                "password": redis_config["requirepass"],
                "db_list": self.cluster["db_list"],
                "is_flush_all": self.cluster["flushall"],
            },
        }

    def redis_capturer(self, **kwargs) -> dict:
        """
        调用redis_capturer工具统计请求
        """
        ip = kwargs["ip"]
        p = self.cluster[ip]
        ports = []
        if isinstance(p, int):
            ports.append(p)
        elif isinstance(p, list):
            ports = p

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Capturer.value,
            "payload": {
                "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
                "ip": ip,
                "ports": ports,
                "monitor_time_ms": self.cluster["monitor_time_ms"],
                "ignore": self.cluster["ignore_req"],
                "ignore_keys": self.cluster["ignore_keys"],
            },
        }

    def bkdbmon_install(self, **kwargs) -> dict:
        """
        redis bk-dbmon安装
        """
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        fullbackup_config = self.__get_define_config(
            NameSpaceEnum.RedisCommon, ConfigFileEnum.FullBackup, ConfigTypeEnum.Config
        )
        binlogbackup_config = self.__get_define_config(
            NameSpaceEnum.RedisCommon, ConfigFileEnum.BinlogBackup, ConfigTypeEnum.Config
        )
        heartbeat_config = self.__get_define_config(
            NameSpaceEnum.RedisCommon, ConfigFileEnum.Heartbeat, ConfigTypeEnum.Config
        )
        monitor_config = self.__get_define_config(
            NameSpaceEnum.RedisCommon, ConfigFileEnum.Monitor, ConfigTypeEnum.Config
        )
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        monitor_config["bkmonitor_event_data_id"] = bkm_dbm_report["event"]["data_id"]
        monitor_config["bkmonitor_event_token"] = bkm_dbm_report["event"]["token"]
        monitor_config["bkmonitor_metric_data_id"] = bkm_dbm_report["metric"]["data_id"]
        monitor_config["bkmonitor_metirc_token"] = bkm_dbm_report["metric"]["token"]

        keylife_config = {
            "stat_dir": DirEnum.REDIS_KEY_LIFE_DIR,
            **self.__get_define_config(NameSpaceEnum.RedisCommon, ConfigFileEnum.Base, ConfigTypeEnum.Config),
            "hotkey_conf": self.__get_define_config(
                NameSpaceEnum.RedisCommon, ConfigFileEnum.HotKey, ConfigTypeEnum.Config
            ),
            "bigkey_conf": self.__get_define_config(
                NameSpaceEnum.RedisCommon, ConfigFileEnum.BigKey, ConfigTypeEnum.Config
            ),
        }

        return {
            "db_type": DBActuatorTypeEnum.Bkdbmon.value,
            "action": DBActuatorTypeEnum.Bkdbmon.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "bkdbmonpkg": {"pkg": bkdbmon_pkg.name, "pkg_md5": bkdbmon_pkg.md5},
                "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
                "gsepath": DirEnum.GSE_DIR,
                "redis_fullbackup": fullbackup_config,
                "redis_binlogbackup": binlogbackup_config,
                "redis_heartbeat": heartbeat_config,
                "redis_monitor": monitor_config,
                "redis_keylife": keylife_config,
            },
        }

    # 场景化需求
    def __get_redis_pkg(self, cluster_type, db_version):
        if cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.Redis, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TendisPredixyTendisplusCluster:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.TendisPlus, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TwemproxyTendisSSDInstance:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.TendisSsd, db_type=DBType.Redis
            )

    # redis批量建立主从关系 (兼容单实例)
    def get_redis_batch_replicate(self, **kwargs) -> dict:
        """
        redis批量建立主从关系 (兼容单实例)
        [{
            "master_ip":
            "master_port":
            "slave_ip":
            "slave_port":
        }]
        """
        params = kwargs["params"]
        self.namespace = params["cluster_type"]
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)

        replica_pairs = []
        for pair in params["ms_link"]:
            replica_pairs.append(
                {
                    "master_ip": pair["master_ip"],
                    "master_port": int(pair["master_port"]),
                    "slave_ip": pair["slave_ip"],
                    "slave_port": int(pair["slave_port"]),
                    "master_auth": redis_config["requirepass"],  # ??!
                    "slave_password": redis_config["requirepass"],
                }
            )
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Replicaof.value,
            "payload": {"replica_pairs": replica_pairs},
        }

    # 安装redis
    def get_redis_install_4_scene(self, **kwargs) -> dict:
        """安装redis
        {"exec_ip":"xxx", "start_port":30000,"inst_num":12,"cluster_type":"","db_version":"","immute_domain":""}
        """
        params = kwargs["params"]
        self.namespace = params["cluster_type"]
        self.__get_redis_pkg(params["cluster_type"], params["db_version"])
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)

        redis_conf = copy.deepcopy(redis_config)
        install_payload = {
            "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
            "pkg": self.redis_pkg.name,
            "pkg_md5": self.redis_pkg.md5,
            "db_type": params["cluster_type"],
            "password": redis_config["requirepass"],
            "data_dirs": ConfigDefaultEnum.DATA_DIRS,
            "ports": [],
            "databases": 1,  # 给个默认值吧
            "maxmemory": 666,  # 给个默认值吧
            "ip": params["exec_ip"],
            "inst_num": int(params["inst_num"]),
            "start_port": int(params["start_port"]),
            "redis_conf_configs": redis_conf,
        }
        # tendisplus cluster 模式暂时不需要特别指定这两个参数
        if self.namespace in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
            install_payload["databases"] = int(redis_config["databases"])
            install_payload["maxmemory"] = int(float(redis_config["maxmemory"]))

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": install_payload,
        }

    def get_install_redis_apply_payload(self, **kwargs) -> dict:
        """
        安装redisredis
        """
        params = kwargs["params"]
        self.namespace = params["cluster_type"]
        self.__get_redis_pkg(params["cluster_type"], params["db_version"])
        redis_conf = copy.deepcopy(self.init_redis_config)

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": {
                "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
                "pkg": self.redis_pkg.name,
                "pkg_md5": self.redis_pkg.md5,
                "password": params["requirepass"],
                "databases": int(params["databases"]),
                "db_type": params["cluster_type"],
                "maxmemory": int(params["maxmemory"]),
                "data_dirs": ConfigDefaultEnum.DATA_DIRS,
                "ports": [],
                "redis_conf_configs": redis_conf,
                "inst_num": params["inst_num"],
                # 以下为流程中需要补充的参数
                "ip": params["exec_ip"],
                "start_port": int(params["start_port"]),
            },
        }

    # redis 备份
    def redis_cluster_backup_4_scene(self, **kwargs) -> dict:
        """
        redis 备份
        {"backup_instance":30001,"exec_ip":"","bk_biz_id":1,"immute_domain":"xx","ssd_log_count":{}}
        """
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Backup.value,
            "payload": {
                "bk_biz_id": str(params["bk_biz_id"]),
                "domain": params["immute_domain"],
                "ip": params["backup_host"],
                "ports": params["backup_instances"],
                # "start_port":30000,
                # "inst_num":10,
                "backup_type": "normal_backup",
                "without_to_backup_sys": True,  # // 是否上传到备份系统,默认false
                "ssd_log_count": params["ssd_log_count"],
            },
        }

    def redis_shutdown_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            "payload": {"ip": params["exec_ip"], "ports": params["shutdown_ports"]},
        }

    # 调用redis_capturer工具统计请求
    def redis_capturer_4_scene(self, **kwargs) -> dict:
        """
        调用redis_capturer工具统计请求
        """
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Capturer.value,
            "payload": {
                "dbtoolspkg": {"pkg": self.tools_pkg.name, "pkg_md5": self.tools_pkg.md5},
                "ip": params["exec_ip"],
                "ports": params["ports"],
                "monitor_time_ms": params["monitor_time_ms"],
                "ignore": params["ignore_req"],
                "ignore_keys": params["ignore_keys"],
            },
        }

    # 干掉 僵尸链接/不活跃链接
    def redis_killconn_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.KillConn.value,
            "payload": {
                "instances": params["instances"],
                "idel_time": int(params["idle_time"]),
                "cluster_type": params["cluster_type"],
            },
        }

    # 同步参数 （通常ssd使用， 或许新管控平台有更好的解决方案）
    def redis_syncparams_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.SyncParam.value,
            "payload": {"instances": params["instances"], "cluster_type": params["cluster_type"]},
        }

    # 检测 同步状态
    def redis_checksync_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.CheckSync.value,
            "payload": {
                "instances": params["instances"],
                "watch_seconds": params["watch_seconds"],
                "cluster_type": params["cluster_type"],
                "last_io_second_ago": params["last_io_second_ago"],
            },
        }

    # 检测 proxy 后端一致性
    def redis_twemproxy_backends_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.CheckProxysMd5.value,
            "payload": {"instances": params["instances"], "cluster_type": params["cluster_type"]},
        }

    # twemproxy 架构-实例切换
    def redis_twemproxy_arch_switch_4_scene(self, **kwargs) -> dict:
        """{
            "cluster_id":0,
            "immute_domain":"",
            "cluster_type":"",
            "switch_info":{},
            "switch_condition":{},
        }
        """
        params, proxy_version = kwargs["params"], ""
        self.namespace = params["cluster_type"]
        if self.namespace in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TwemproxyTendisSSDInstance.value,
        ]:
            proxy_version = ConfigFileEnum.Twemproxy
        elif self.namespace == ClusterType.TendisPredixyTendisplusCluster.value:
            proxy_version = ConfigFileEnum.Predixy
        proxy_config = self.__get_cluster_config(params["immute_domain"], proxy_version, ConfigTypeEnum.ProxyConf)
        cluster_meta = nosqlcomm.other.get_cluster_detail(cluster_id=params["cluster_id"])[0]
        cluster_meta["proxy_pass"] = proxy_config["password"]
        cluster_meta["storage_pass"] = proxy_config["redis_password"]

        logger.info("switch cluster {}, switch infos : {}".format(params["immute_domain"], params["switch_info"]))
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.SwitchBackends.value,
            "payload": {
                "cluster_meta": cluster_meta,  # dict
                "switch_info": params["switch_info"],  # list
                "switch_condition": params["switch_condition"],  # dict
            },
        }

    # redis dts数据校验
    def redis_dts_datacheck_payload(self, **kwargs) -> dict:
        """
        redis dts数据校验
        """
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        ip = kwargs["ip"]
        current_src_ip = kwargs["params"]["current_src_ip"] if kwargs["params"].get("current_src_ip") else ip
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DTS_DATACHECK.value,
            "payload": {
                "pkg": tools_pkg.name,
                "pkg_md5": tools_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "dts_copy_type": self.cluster["dts_copy_type"],
                "src_redis_ip": current_src_ip,
                "src_redis_port_segmentlist": self.cluster[current_src_ip],
                "src_hash_tag": False,
                "src_redis_password": self.cluster["src_redis_password"],
                "src_cluster_addr": self.cluster["src_cluster_addr"],
                "dst_cluster_addr": self.cluster["dst_cluster_addr"],
                "dst_cluster_password": self.cluster["dst_cluster_password"],
                "key_white_regex": self.cluster["key_white_regex"],
                "key_black_regex": self.cluster["key_black_regex"],
            },
        }

    # redis dts数据修复
    def redis_dts_datarepair_payload(self, **kwargs) -> dict:
        """
        redis dts数据修复
        """
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        ip = kwargs["ip"]
        current_src_ip = kwargs["params"]["current_src_ip"] if kwargs["params"].get("current_src_ip") else ip
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DTS_DATAREPAIR.value,
            "payload": {
                "pkg": tools_pkg.name,
                "pkg_md5": tools_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "dts_copy_type": self.cluster["dts_copy_type"],
                "src_redis_ip": current_src_ip,
                "src_redis_port_segmentlist": self.cluster[current_src_ip],
                "src_hash_tag": False,
                "src_redis_password": self.cluster["src_redis_password"],
                "src_cluster_addr": self.cluster["src_cluster_addr"],
                "dst_cluster_addr": self.cluster["dst_cluster_addr"],
                "dst_cluster_password": self.cluster["dst_cluster_password"],
                "key_white_regex": self.cluster["key_white_regex"],
                "key_black_regex": self.cluster["key_black_regex"],
            },
        }

    # redis dts 源集群 proxy在线切换
    def redis_dts_src_proxys_online_switch_payload(self, **kwargs) -> dict:
        """
        redis dts 在线切换
        """
        params = kwargs["params"]
        proxy_pkg: Package = None
        if is_twemproxy_proxy_type(params["dst_cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=TwemproxyVersion.TwemproxyLatest, pkg_type=MediumEnum.Twemproxy, db_type=DBType.Redis
            )
        elif is_predixy_proxy_type(params["dst_cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
            )
        logger.info(
            "redis_dts_src_proxys_online_switch_payload dst_proxy_config ===>{}".format(
                self.cluster["dst_proxy_config"]
            )
        )
        dst_proxy_config = self.cluster["dst_proxy_config"]
        dst_proxy_config_data = ""
        dst_proxy_ip = params["my_dst_proxy_ip"]
        for k, v in dst_proxy_config.items():
            dst_proxy_ip = k
            if isinstance(v, dict) and "data" in v:
                dst_proxy_config_data = v["data"]
                break
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DTS_ONLINE_SWITCH.value,
            "payload": {
                "dst_proxy_pkg": {
                    "pkg": proxy_pkg.name,
                    "pkg_md5": proxy_pkg.md5,
                },
                "dts_bill_id": params["dts_bill_id"],
                "src_proxy_ip": params["src_proxy_ip"],
                "src_proxy_port": int(params["src_proxy_port"]),
                "src_proxy_password": params["src_proxy_password"],
                "src_cluster_type": params["src_cluster_type"],
                "dst_proxy_ip": dst_proxy_ip,
                "dst_proxy_port": int(params["dst_proxy_port"]),
                "dst_proxy_password": params["dst_proxy_password"],
                "dst_cluster_type": params["dst_cluster_type"],
                "dst_redis_ip": params["dst_redis_ip"],
                "dst_redis_port": int(params["dst_redis_port"]),
                "dst_proxy_config_content": dst_proxy_config_data,
            },
        }

    # redis dts 目标集群 proxy 在线切换
    def redis_dts_dst_proxys_online_switch_payload(self, **kwargs) -> dict:
        """
        redis dts 在线切换
        """
        params = kwargs["params"]
        proxy_pkg: Package = None
        if is_twemproxy_proxy_type(params["dst_cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=TwemproxyVersion.TwemproxyLatest, pkg_type=MediumEnum.Twemproxy, db_type=DBType.Redis
            )
        elif is_predixy_proxy_type(params["dst_cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
            )
        logger.info(
            "redis_dts_dst_proxys_online_switch_payload src_proxy_config ===>{}".format(
                self.cluster["src_proxy_config"]
            )
        )
        src_proxy_config = self.cluster["src_proxy_config"]
        src_proxy_config_data = ""
        dst_proxy_ip = params["my_dst_proxy_ip"]
        for k, v in src_proxy_config.items():
            dst_proxy_ip = k
            if isinstance(v, dict) and "data" in v:
                src_proxy_config_data = v["data"]
                break
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DTS_ONLINE_SWITCH.value,
            "payload": {
                "dst_proxy_pkg": {
                    "pkg": proxy_pkg.name,
                    "pkg_md5": proxy_pkg.md5,
                },
                "dts_bill_id": params["dts_bill_id"],
                "src_proxy_ip": params["src_proxy_ip"],
                "src_proxy_port": int(params["src_proxy_port"]),
                "src_proxy_password": params["src_proxy_password"],
                "src_cluster_type": params["src_cluster_type"],
                "dst_proxy_ip": dst_proxy_ip,
                "dst_proxy_port": int(params["dst_proxy_port"]),
                "dst_proxy_password": params["dst_proxy_password"],
                "dst_cluster_type": params["dst_cluster_type"],
                "dst_redis_ip": params["dst_redis_ip"],
                "dst_redis_port": int(params["dst_redis_port"]),
                "dst_proxy_config_content": src_proxy_config_data,
            },
        }

    # Tendis ssd 重建热备
    def redis_tendisssd_dr_restore_4_scene(self, **kwargs) -> dict:
        """#### Tendis ssd 重建热备
        {       "backup_tasks":[] # from backup output.
                "master_ip":params["master_ip"],
                "master_ports":params["master_ports"],
                "slave_ip":params["slave_ip"],
                "slave_ports":params["slave_ports"],
        }
        """
        params = kwargs["params"]
        self.namespace = params["cluster_type"]
        proxy_config = self.__get_cluster_config(params["immute_domain"], self.proxy_version, ConfigTypeEnum.ProxyConf)

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.TendisSSD.value + "_" + RedisActuatorActionEnum.DR_RESTORE.value,
            "payload": {
                "master_ip": params["master_ip"],
                "master_ports": params["master_ports"],
                "master_auth": proxy_config["redis_password"],
                "slave_ip": params["slave_ip"],
                "slave_ports": params["slave_ports"],
                "slave_password": proxy_config["redis_password"],
                "task_dir": "/data/dbbak",
                "backup_dir": "/data/dbbak",
            },
        }

    def get_add_dts_server_payload(self, **kwargs) -> dict:
        """
        获取dts server部署的payload
        """
        dts_server_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisDts, db_type=DBType.Redis
        )
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.ADD_DTS_SERVER.value,
            "payload": {
                "pkg": dts_server_pkg.name,
                "pkg_md5": dts_server_pkg.md5,
                "bk_biz_id": self.bk_biz_id,
                "bk_dbm_nginx_url": self.cluster["nginx_url"],
                "bk_dbm_cloud_id": self.cluster["bk_cloud_id"],
                "bk_dbm_cloud_token": self.cluster["cloud_token"],
                "system_user": self.cluster["system_user"],
                "system_password": self.cluster["system_password"],
                "city_name": self.cluster["bk_city_name"],
                "warning_msg_notifiers": "xxxxx",
            },
        }

    def get_remove_dts_server_payload(self, **kwargs) -> dict:
        """
        获取dts server删除的payload
        """
        dts_server_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisDts, db_type=DBType.Redis
        )
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.REMOVE_DTS_SERVER.value,
            "payload": {
                "pkg": dts_server_pkg.name,
                "pkg_md5": dts_server_pkg.md5,
            },
        }

    # redis 数据构造

    def redis_data_structure(self, **kwargs) -> dict:
        """
        redis 数据构造
        """
        params = kwargs["params"]
        print("params", params)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DATA_STRUCTURE.value,
            "payload": {
                "source_ip": params["data_params"]["source_ip"],
                "source_ports": params["data_params"]["source_ports"],
                "new_temp_ip": params["data_params"]["new_temp_ip"],
                "new_temp_ports": params["data_params"]["new_temp_ports"],
                "recovery_time_point": params["data_params"]["recovery_time_point"],
                "is_precheck": params["data_params"]["is_precheck"],
                "tendis_type": params["data_params"]["tendis_type"],
                "user": self.account["user"],
                "password": self.account["user_pwd"],
                "base_info": {
                    "url": env.IBS_INFO_URL,
                    "sys_id": env.IBS_INFO_SYSID,
                    "key": env.IBS_INFO_KEY,
                },
            },
        }

    # redis 数据构造集群建立
    def rollback_clustermeet_payload(self, **kwargs) -> dict:
        """
        数据构造 rediscluster 集群建立
        """
        params = kwargs["params"]
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)
        bacth_pairs = []
        for instance in params["all_instance"]:
            ip, port = instance.split(":")
            pair = {
                "master_ip": ip,
                "master_port": int(port),
            }
            bacth_pairs.append(pair)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": RedisActuatorActionEnum.CLUSTER_MEET.value,
            "payload": {
                "password": redis_config["requirepass"],
                "slots_auto_assign": True,
                "replica_pairs": bacth_pairs,
            },
        }

    # 数据构造 proxy 进程下架
    def proxy_shutdown_payload(self, **kwargs) -> dict:
        """
        数据构造 proxy 进程下架
        """
        params = kwargs["params"]
        ip = params["proxy_ip"]
        port = params["proxy_port"]
        op = params["operate"]
        action = ""
        if self.cluster["cluster_type"] in twemproxy_cluster_type_list:
            action = DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.Operate.value
        elif self.cluster["cluster_type"] in predixy_cluster_type_list:
            action = DBActuatorTypeEnum.Predixy.value + "_" + RedisActuatorActionEnum.Operate.value
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": action,
            "payload": {"ip": ip, "port": port, "operate": op},
        }

    # redis 数据构造集群重建和校验
    def clustermeet_check_payload(self, **kwargs) -> dict:
        """
        数据构造 rediscluster meet建立集群关系并检查集群状态
        """
        params = kwargs["params"]
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)
        bacth_pairs = []
        for instance in params["all_instance"]:
            ip, port = instance.split(IP_PORT_DIVIDER)
            bacth_pairs.append(
                {
                    "master_ip": ip,
                    "master_port": int(port),
                }
            )
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": RedisActuatorActionEnum.CLUSTER_MEET_CHECK.value,
            "payload": {
                "password": redis_config["requirepass"],
                "replica_pairs": bacth_pairs,
            },
        }

    # 把心节点添加到已有的集群
    def redis_cluster_meet_4_scene(self, **kwargs) -> dict:
        """{
            "immute_domain":"",
            "db_version":"",
            "meet_instances":[],
        }
        """
        params = kwargs["params"]
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)
        cluster = Cluster.objects.get(immute_domain=params["immute_domain"])
        cluster_info = metaApi.cluster.nosqlcomm.get_cluster_detail(cluster.id)[0]
        bacth_pairs = []
        oneNodeInCluster = cluster_info["redis_master_set"][0]
        bacth_pairs.append(
            {
                "master_ip": oneNodeInCluster.split(IP_PORT_DIVIDER)[0],
                "master_port": int(oneNodeInCluster.split(IP_PORT_DIVIDER)[1]),
            }
        )
        bacth_pairs.extend(params["meet_instances"])
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": RedisActuatorActionEnum.CLUSTER_MEET.value,
            "payload": {
                "password": redis_config["requirepass"],
                "replica_pairs": bacth_pairs,
                "slots_auto_assign": False,
                "use_for_expansion": False,
            },
        }

    # 从集群中去掉节点
    def redis_cluster_forget_4_scene(self, **kwargs) -> dict:
        """{
            "immute_domain":"",
            "db_version":"",
            "forget_instances":[],
        }
        """
        params = kwargs["params"]
        redis_config = self.__get_cluster_config(params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf)
        cluster = Cluster.objects.get(immute_domain=params["immute_domain"])
        cluster_info = metaApi.cluster.nosqlcomm.get_cluster_detail(cluster.id)[0]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.ClusterForget.value,
            "payload": {
                "cluster_meta": {
                    "storage_pass": redis_config["requirepass"],
                    "immute_domain": cluster_info["immute_domain"],
                    "cluster_type": cluster_info["cluster_type"],
                    "redis_master_set": cluster_info["redis_master_set"],
                },
                "forget_list": params["forget_instances"],
            },
        }
