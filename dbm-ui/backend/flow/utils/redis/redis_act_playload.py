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
import json
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
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Cluster, StorageInstance
from backend.db_package.models import Package
from backend.db_services.redis.redis_dts.models.tb_tendis_dts_switch_backup import TbTendisDtsSwitchBackup
from backend.db_services.redis.util import (
    is_predixy_proxy_type,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.db_services.version.constants import PredixyVersion, RedisVersion, TwemproxyVersion
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
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_proxy_util import (
    get_cache_backup_mode,
    get_twemproxy_cluster_server_shards,
    set_backup_mode,
)
from backend.flow.utils.redis.redis_util import get_latest_redis_package_by_version
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")
apply_list = [
    TicketType.REDIS_SINGLE_APPLY.value,
    TicketType.REDIS_INS_APPLY.value,
    TicketType.REDIS_CLUSTER_APPLY.value,
    TicketType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
    TicketType.REDIS_CLUSTER_TYPE_UPDATE.value,
]
global_list = [TicketType.REDIS_KEYS_DELETE.value]
proxy_scale_list = [
    TicketType.REDIS_PROXY_SCALE_UP.value,
    TicketType.REDIS_PROXY_SCALE_DOWN.value,
]
redis_scale_list = [TicketType.REDIS_SCALE_UPDOWN.value, TicketType.REDIS_SLOTS_MIGRATE.value]
cutoff_list = [
    TicketType.REDIS_CLUSTER_CUTOFF.value,
    TicketType.REDIS_CLUSTER_ADD_SLAVE.value,
]
migrate_list = [TicketType.REDIS_TENDIS_META_MITRATE.value]
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
cache_cluster_type_list = [
    ClusterType.RedisCluster.value,
    ClusterType.TendisPredixyRedisCluster.value,
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value,
    ClusterType.TendisRedisCluster.value,
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
        if self.ticket_data["ticket_type"] in apply_list + cutoff_list + tool_list + migrate_list:
            self.account = self.__get_define_config(NameSpaceEnum.Common, ConfigFileEnum.OS, ConfigTypeEnum.OSConf)
            db_version = ""
            if "db_version" in self.cluster:
                db_version = self.cluster["db_version"]
            elif "db_version" in self.ticket_data:
                db_version = self.ticket_data["db_version"]
            if db_version != "":
                self.init_redis_config = self.__get_define_config(self.namespace, db_version, ConfigTypeEnum.DBConf)
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

        if is_twemproxy_proxy_type(self.namespace):
            self.proxy_version = ConfigFileEnum.Twemproxy
        elif is_predixy_proxy_type(self.namespace):
            self.proxy_version = ConfigFileEnum.Predixy

    def __get_define_config(self, namespace: str, conf_file: str, conf_type: str) -> Any:
        if conf_file is None:
            return
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

    @staticmethod
    def get_common_config(bk_biz_id: str, namespace: str, conf_file: str, conf_type: str) -> Any:
        """获取一些common的参数配置"""
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": bk_biz_id,
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def set_redis_config(self, cluster_map: dict) -> Any:
        conf_items = []
        for conf_name, conf_value in cluster_map["conf"].items():
            conf_items.append({"conf_name": conf_name, "conf_value": conf_value, "op_type": OpType.UPDATE})
        data = DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": cluster_map["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": self.namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_map["domain_name"],
            }
        )
        # 备份相关的配置，需要单独写进去。只有cache类型的的集群，才会去修改fullbackup的参数
        if self.namespace in cache_cluster_type_list:
            if "backup_config" in cluster_map:
                if "cache_backup_mode" in cluster_map["backup_config"]:
                    set_backup_mode(
                        cluster_map["domain_name"],
                        self.bk_biz_id,
                        self.namespace,
                        cluster_map["backup_config"]["cache_backup_mode"],
                    )

        return data

    def delete_redis_config(self, cluster_map: dict):
        conf_items = [
            {"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name, _ in cluster_map["conf"].items()
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

    @staticmethod
    def get_dbconfig_for_swap(
        bill_id: int,
        src_cluster_addr: str,
        dst_cluster_addr: str,
        bk_biz_id: str,
        cluster_domain: str,
        cluster_version: str,
        cluste_type: str,
        conf_type: str,
        data_type: str,
    ) -> dict:
        # 先从表中获取,如果获取不到,则从dbconfig中获取
        try:
            row = TbTendisDtsSwitchBackup.objects.get(
                bill_id=bill_id, src_cluster=src_cluster_addr, dst_cluster=dst_cluster_addr, data_type=data_type
            )
            if row.data:
                return json.loads(row.data)
        except TbTendisDtsSwitchBackup.DoesNotExist:
            pass
        # 从dbconfig中获取,然后保存到表中,便于重试
        resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": cluster_version,
                "conf_type": conf_type,
                "namespace": cluste_type,
                "format": FormatType.MAP,
            }
        )
        row = TbTendisDtsSwitchBackup()
        row.bill_id = bill_id
        row.src_cluster = src_cluster_addr
        row.dst_cluster = dst_cluster_addr
        row.data_type = data_type
        row.data = json.dumps(resp)
        row.save()
        return resp

    @staticmethod
    def redis_conf_names_by_cluster_type(cluster_type: str, cluster_version: str) -> list:
        conf_names: list = []
        if (
            is_redis_instance_type(cluster_type) and cluster_version != RedisVersion.Redis20
        ) or is_tendisplus_instance_type(cluster_type):
            conf_names.append("cluster-enabled")
        if is_redis_instance_type(cluster_type) or is_tendisssd_instance_type(cluster_type):
            conf_names.append("maxmemory")
            conf_names.append("databases")
        return conf_names

    def dts_swap_redis_config(self, cluster_map: dict):
        """交换源集群和目标集群的redis配置"""
        logger.info(_("开始交换源集群和目标集群的redis配置"))

        bill_id = cluster_map["bill_id"]
        src_cluster_addr = cluster_map["src_cluster_domain"] + IP_PORT_DIVIDER + str(cluster_map["src_cluster_port"])
        dst_cluster_addr = cluster_map["dst_cluster_domain"] + IP_PORT_DIVIDER + str(cluster_map["dst_cluster_port"])
        bk_biz_id = cluster_map["bk_biz_id"]
        conf_type = ConfigTypeEnum.DBConf

        logger.info(_("获取源集群:{} redis配置").format(cluster_map["src_cluster_domain"]))
        data_type = "src_dbconf"
        src_resp = self.get_dbconfig_for_swap(
            bill_id,
            src_cluster_addr,
            dst_cluster_addr,
            bk_biz_id,
            cluster_map["src_cluster_domain"],
            cluster_map["src_cluster_version"],
            cluster_map["src_cluster_type"],
            conf_type,
            data_type,
        )

        src_conf_names = self.redis_conf_names_by_cluster_type(
            cluster_map["src_cluster_type"], cluster_map["src_cluster_version"]
        )
        src_conf_items = []
        for conf_name in src_conf_names:
            if conf_name in src_resp["content"]:
                src_conf_items.append(
                    {"conf_name": conf_name, "conf_value": src_resp["content"][conf_name], "op_type": OpType.UPDATE}
                )

        logger.info(_("获取目标集群:{} redis配置").format(cluster_map["dst_cluster_domain"]))
        data_type = "dst_dbconf"
        dst_resp = self.get_dbconfig_for_swap(
            bill_id,
            src_cluster_addr,
            dst_cluster_addr,
            bk_biz_id,
            cluster_map["dst_cluster_domain"],
            cluster_map["dst_cluster_version"],
            cluster_map["dst_cluster_type"],
            conf_type,
            data_type,
        )

        dst_conf_names = self.redis_conf_names_by_cluster_type(
            cluster_map["dst_cluster_type"], cluster_map["dst_cluster_version"]
        )
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
            "bk_biz_id": str(cluster_map["bk_biz_id"]),
            "level_name": LevelName.CLUSTER,
            "level_value": "",  # 需要替换成真实值
        }

        if cluster_map["src_cluster_type"] != cluster_map["dst_cluster_type"]:
            # 源集群、目标集群类型有变化, 先删除原有的配置,再更新配置,避免残留
            src_remove_items = [{"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name in src_conf_names]
            upsert_param["conf_file_info"]["namespace"] = cluster_map["src_cluster_type"]
            upsert_param["conf_file_info"]["conf_file"] = cluster_map["src_cluster_version"]
            upsert_param["conf_items"] = src_remove_items
            upsert_param["level_value"] = cluster_map["src_cluster_domain"]
            logger.info(_("删除源集群:{} redis配置,upsert_param:{}".format(cluster_map["src_cluster_domain"], upsert_param)))
            DBConfigApi.upsert_conf_item(upsert_param)

            dst_remove_items = [{"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name in dst_conf_names]
            upsert_param["conf_file_info"]["namespace"] = cluster_map["dst_cluster_type"]
            upsert_param["conf_file_info"]["conf_file"] = cluster_map["dst_cluster_version"]
            upsert_param["conf_items"] = dst_remove_items
            upsert_param["level_value"] = cluster_map["dst_cluster_domain"]
            logger.info(_("删除目标集群:{} redis配置,upsert_param:{}").format(cluster_map["dst_cluster_domain"], upsert_param))
            DBConfigApi.upsert_conf_item(upsert_param)
            time.sleep(2)
        # 源集群 写入目标集群的配置,除了 dst_conf_items 以外,其他conf_items基本用默认值
        upsert_param["conf_file_info"]["namespace"] = cluster_map["dst_cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = cluster_map["dst_cluster_version"]
        upsert_param["conf_items"] = dst_conf_items
        upsert_param["level_value"] = cluster_map["src_cluster_domain"]
        logger.info(_("更新源集群redis配置 为 目标集群的配置,upsert_param:{}".format(upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)
        # 目标集群 写入源集群的配置,除了 src_conf_items 以外,其他conf_items基本用默认值
        upsert_param["conf_file_info"]["namespace"] = cluster_map["src_cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = cluster_map["src_cluster_version"]
        upsert_param["conf_items"] = src_conf_items
        upsert_param["level_value"] = cluster_map["dst_cluster_domain"]
        logger.info(_("更新目标集群redis配置 为 源集群的配置,upsert_param:{}".format(upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)

        # 交换源集群和目标集群的redis 密码,proxy密码不会变化
        src_passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster_map["src_cluster_domain"])
        dst_passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster_map["dst_cluster_domain"])
        PayloadHandler.redis_save_password_by_domain(
            immute_domain=cluster_map["src_cluster_domain"],
            redis_password=dst_passwd_ret.get("redis_password"),
        )
        PayloadHandler.redis_save_password_by_domain(
            immute_domain=cluster_map["dst_cluster_domain"],
            redis_password=src_passwd_ret.get("redis_password"),
        )

    def delete_proxy_config(self, cluster_map: dict):
        conf_items = [
            {"conf_name": conf_name, "op_type": OpType.REMOVE} for conf_name, _ in cluster_map["conf"].items()
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
        passwd_ret = PayloadHandler.redis_get_password_by_domain(domain_name)
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
        if conf_type == ConfigTypeEnum.ProxyConf.value:
            if passwd_ret.get("redis_password"):
                data["content"]["redis_password"] = passwd_ret.get("redis_password")
            if passwd_ret.get("redis_proxy_password"):
                data["content"]["password"] = passwd_ret.get("redis_proxy_password")
            if passwd_ret.get("redis_proxy_admin_password"):
                data["content"]["redis_proxy_admin_password"] = passwd_ret.get("redis_proxy_admin_password")
        elif conf_type == ConfigTypeEnum.DBConf.value:
            if passwd_ret.get("redis_password"):
                data["content"]["requirepass"] = passwd_ret.get("redis_password")

        return data["content"]

    def set_proxy_config(self, cluster_map: dict) -> Any:
        """
        集群初始化的时候twemproxy没做变动，直接写入集群就OK
        """
        # 密码随机化
        PayloadHandler.redis_save_password_by_domain(
            immute_domain=cluster_map["domain_name"],
            redis_password=cluster_map["pwd_conf"]["redis_pwd"],
            redis_proxy_password=cluster_map["pwd_conf"]["proxy_pwd"],
            redis_proxy_admin_password=cluster_map["pwd_conf"]["proxy_admin_pwd"],
        )

        conf_items = []
        for conf_name, conf_value in cluster_map["conf"].items():
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
                "level_value": cluster_map["domain_name"],
            }
        )
        return data

    def dts_swap_proxy_config(self, cluster_map: dict) -> Any:
        """
        交换源集群和目标集群 dbconfig 中的proxy版本信息,有可能 twemproxy集群 切换到 predixy集群
        """
        src_proxy_conf_names = ["port"]
        dst_proxy_conf_names = ["port"]

        # 如果类型相同, 需要处理的就是 twemproxy hash_tag:
        # - 都是twemproxy类型且 hash_tag 不同，需要交换一下，其他的端口这些都不用管;
        # - 都是predixy类型完全没有需要变化的，如果实在要变化，也应该是目的集群跟着原集群的变;
        # 如果类型不同, 主要处理的就是集群类型、proxy版本这些，同时保留port不变:
        # - twemproxy 变成 predixy类型，先删除 twemproxy的配置，然后插入predixy配置;
        # - predixy 变成 twemproxy 类型，先删除predixy 配置，然后插入twemproxy的配置, twemproxy hash_tag默认开启满足预期;
        logger.info(_("交换源集群和目标集群 dbconfig 中的proxy版本信息"))

        bill_id = cluster_map["bill_id"]
        src_cluster_addr = cluster_map["src_cluster_domain"] + IP_PORT_DIVIDER + str(cluster_map["src_cluster_port"])
        dst_cluster_addr = cluster_map["dst_cluster_domain"] + IP_PORT_DIVIDER + str(cluster_map["dst_cluster_port"])
        bk_biz_id = str(cluster_map["bk_biz_id"])
        conf_type = ConfigTypeEnum.ProxyConf

        logger.info(_("获取源集群:{} proxy配置").format(cluster_map["src_cluster_domain"]))
        data_type = "src_proxyconf"
        src_resp = self.get_dbconfig_for_swap(
            bill_id,
            src_cluster_addr,
            dst_cluster_addr,
            bk_biz_id,
            cluster_map["src_cluster_domain"],
            cluster_map["src_proxy_version"],
            cluster_map["src_cluster_type"],
            conf_type,
            data_type,
        )
        logger.info(_("获取目标集群:{} proxy配置").format(cluster_map["dst_cluster_domain"]))
        data_type = "dst_proxyconf"
        dst_resp = self.get_dbconfig_for_swap(
            bill_id,
            src_cluster_addr,
            dst_cluster_addr,
            bk_biz_id,
            cluster_map["dst_cluster_domain"],
            cluster_map["dst_proxy_version"],
            cluster_map["dst_cluster_type"],
            conf_type,
            data_type,
        )
        # src_conf_upsert_items 目前赋值的是源集群中不能更改的项,如port不能变
        src_conf_upsert_items = []
        for conf_name in src_proxy_conf_names:
            src_conf_upsert_items.append(
                {"conf_name": conf_name, "conf_value": src_resp["content"][conf_name], "op_type": OpType.UPDATE}
            )
        # dst_conf_upsert_items 目前赋值的是目的集群中不能更改的项,如port不能变
        dst_conf_upsert_items = []
        for conf_name in dst_proxy_conf_names:
            dst_conf_upsert_items.append(
                {"conf_name": conf_name, "conf_value": dst_resp["content"][conf_name], "op_type": OpType.UPDATE}
            )
        # 如果集群类型相同
        if cluster_map["src_cluster_type"] == cluster_map["dst_cluster_type"]:
            # 如果都是predixy类型的集群,直接返回
            if is_predixy_proxy_type(cluster_map["src_cluster_type"]):
                return
            elif is_twemproxy_proxy_type(cluster_map["src_cluster_type"]):
                # 如果都是twemproxy类型且 hash_tag 相同,直接返回
                if src_resp["content"]["hash_tag"] == dst_resp["content"]["hash_tag"]:
                    return
        # 如果都是twemproxy类型集群 且 hash_tag 不同,则需要交换一下
        if is_twemproxy_proxy_type(cluster_map["src_cluster_type"]) and is_twemproxy_proxy_type(
            cluster_map["dst_cluster_type"]
        ):
            if src_resp["content"]["hash_tag"] != dst_resp["content"]["hash_tag"]:
                src_conf_upsert_items.append(
                    {"conf_name": "hash_tag", "conf_value": dst_resp["content"]["hash_tag"], "op_type": OpType.UPDATE}
                )
                dst_conf_upsert_items.append(
                    {"conf_name": "hash_tag", "conf_value": src_resp["content"]["hash_tag"], "op_type": OpType.UPDATE}
                )

        logger.info(_("src_conf_upsert_items==>{}".format(src_conf_upsert_items)))
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
            "bk_biz_id": str(cluster_map["bk_biz_id"]),
            "level_name": LevelName.CLUSTER,
            "level_value": "",  # 需要替换成真实值
        }

        if cluster_map["src_cluster_type"] != cluster_map["dst_cluster_type"]:
            # 如果集群类型不同,才需要删除原有dbconfig中proxy配置
            remove_items = []
            for conf_name in src_proxy_conf_names:
                remove_items.append({"conf_name": conf_name, "op_type": OpType.REMOVE})
            # 删除源集群的proxy配置
            src_remove_param = copy.deepcopy(upsert_param)
            src_remove_param["conf_file_info"]["conf_file"] = cluster_map["src_proxy_version"]
            src_remove_param["conf_file_info"]["namespace"] = cluster_map["src_cluster_type"]
            src_remove_param["conf_items"] = remove_items
            src_remove_param["level_value"] = cluster_map["src_cluster_domain"]
            logger.info(
                _("删除源集群:{} proxy配置,src_remove_param:{}").format(cluster_map["src_cluster_domain"], src_remove_param)
            )
            DBConfigApi.upsert_conf_item(src_remove_param)

            remove_items = []
            for conf_name in dst_proxy_conf_names:
                remove_items.append({"conf_name": conf_name, "op_type": OpType.REMOVE})
            # 删除目标集群的proxy配置
            dst_remove_param = copy.deepcopy(upsert_param)
            dst_remove_param["conf_file_info"]["conf_file"] = cluster_map["dst_proxy_version"]
            dst_remove_param["conf_file_info"]["namespace"] = cluster_map["dst_cluster_type"]
            dst_remove_param["conf_items"] = remove_items
            dst_remove_param["level_value"] = cluster_map["dst_cluster_domain"]
            logger.info(
                _("删除目标集群:{} proxy配置,dst_remove_param:{}").format(cluster_map["dst_cluster_domain"], dst_remove_param)
            )
            DBConfigApi.upsert_conf_item(dst_remove_param)

            time.sleep(2)

        # 更新源集群的proxy版本、集群类型等信息
        src_upsert_param = copy.deepcopy(upsert_param)
        src_upsert_param["conf_file_info"]["conf_file"] = cluster_map["dst_proxy_version"]
        src_upsert_param["conf_file_info"]["namespace"] = cluster_map["dst_cluster_type"]
        src_upsert_param["conf_items"] = src_conf_upsert_items
        src_upsert_param["level_value"] = cluster_map["src_cluster_domain"]
        logger.info(
            _("更新源集群:{} dbconfig 中proxy版本等信息,src_upsert_param:{}").format(
                cluster_map["src_cluster_domain"], src_upsert_param
            )
        )
        DBConfigApi.upsert_conf_item(src_upsert_param)

        # 更新目的集群的proxy版本、集群类型等信息
        dst_upsert_param = copy.deepcopy(upsert_param)
        dst_upsert_param["conf_file_info"]["conf_file"] = cluster_map["src_proxy_version"]
        dst_upsert_param["conf_file_info"]["namespace"] = cluster_map["src_cluster_type"]
        dst_upsert_param["conf_items"] = dst_conf_upsert_items
        dst_upsert_param["level_value"] = cluster_map["dst_cluster_domain"]
        logger.info(
            _("更新目标集群:{} dbconfig 中proxy版本等信息,dst_upsert_param:{}").format(
                cluster_map["dst_cluster_domain"], dst_upsert_param
            )
        )
        DBConfigApi.upsert_conf_item(dst_upsert_param)

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        初始化机器
        """
        redis_os_account = PayloadHandler.redis_get_os_account()
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": RedisActuatorActionEnum.Sysinit.value,
            "payload": {"user": redis_os_account["os_user"], "password": redis_os_account["os_password"]},
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
                "predixyadminpasswd": proxy_config["redis_proxy_admin_password"],
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
        cluster = Cluster.objects.get(immute_domain=self.cluster["domain_name"])
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Backup.value,
            "payload": {
                "bk_biz_id": self.bk_biz_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "ip": ip,
                "ports": self.cluster[ip],
                "backup_type": self.cluster["backup_type"],
                "domain": self.cluster["domain_name"],
                "without_to_backup_sys": not BACKUP_SYS_STATUS,
                "backup_client_storage_type": "",  # 留空,使用系统默认
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

    def __is_all_instances_shutdown(self, ip: str, port: list) -> bool:
        """
        判断所有实例是否都已经下架
        """
        insts = StorageInstance.objects.filter(machine__ip=ip)
        for inst in insts:
            if inst.port not in port:
                return False
        return True

    def redis_shutdown_payload(self, **kwargs) -> dict:
        """
        redis下架
        """
        ip = kwargs["ip"]
        ports = self.cluster[ip]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            "payload": {
                "ip": ip,
                "ports": ports,
                "is_all_instances_shutdown": self.__is_all_instances_shutdown(ip, ports),
            },
        }

    def redis_flush_data_payload(self, **kwargs) -> dict:
        """
        redis清档
        """
        ip = kwargs["ip"]
        params = kwargs["params"]
        domain_name = params.get("domain_name", self.cluster["domain_name"])
        db_version = params.get("db_version", self.cluster["db_version"])
        cluster_type = params.get("cluster_type", self.cluster["cluster_type"])
        ports = params.get("ports", self.cluster[ip])
        force = params.get("force", self.cluster["force"])
        db_list = params.get("db_list", self.cluster["db_list"])
        flushall = params.get("flushall", self.cluster["flushall"])

        redis_config = self.__get_cluster_config(domain_name, db_version, ConfigTypeEnum.DBConf)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.FlushData.value,
            "payload": {
                "ip": ip,
                "db_type": cluster_type,
                "ports": ports,
                "is_force": force,
                "password": redis_config["requirepass"],
                "db_list": db_list,
                "is_flush_all": flushall,
            },
        }

    def redis_reupload_old_backup_records_payload(self, **kwargs) -> dict:
        """
        重新上传旧备份记录
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.REUPLOAD_OLD_BACKUP_RECORDS.value,
            "payload": {
                "bk_biz_id": params["bk_biz_id"],
                "bk_cloud_id": params["bk_cloud_id"],
                "server_ip": params["server_ip"],
                "server_ports": params["server_ports"],
                "cluster_domain": params["cluster_domain"],
                "cluster_type": params["cluster_type"],
                "meta_role": params["meta_role"],
                "server_shards": params.get("server_shards", {}),
                "records_file": params["records_file"],
                "force": True,
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

    @staticmethod
    def get_bkdbmon_payload_header(bk_biz_id: str) -> dict:
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        tools_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        fullbackup_config = RedisActPayload.get_common_config(
            bk_biz_id=bk_biz_id,
            namespace=NameSpaceEnum.RedisCommon,
            conf_file=ConfigFileEnum.FullBackup,
            conf_type=ConfigTypeEnum.Config,
        )
        binlogbackup_config = RedisActPayload.get_common_config(
            bk_biz_id=bk_biz_id,
            namespace=NameSpaceEnum.RedisCommon,
            conf_file=ConfigFileEnum.BinlogBackup,
            conf_type=ConfigTypeEnum.Config,
        )
        heartbeat_config = RedisActPayload.get_common_config(
            bk_biz_id=bk_biz_id,
            namespace=NameSpaceEnum.RedisCommon,
            conf_file=ConfigFileEnum.Heartbeat,
            conf_type=ConfigTypeEnum.Config,
        )
        monitor_config = RedisActPayload.get_common_config(
            bk_biz_id=bk_biz_id,
            namespace=NameSpaceEnum.RedisCommon,
            conf_file=ConfigFileEnum.Monitor,
            conf_type=ConfigTypeEnum.Config,
        )
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        monitor_config["bkmonitor_event_data_id"] = bkm_dbm_report["event"]["data_id"]
        monitor_config["bkmonitor_event_token"] = bkm_dbm_report["event"]["token"]
        monitor_config["bkmonitor_metric_data_id"] = bkm_dbm_report["metric"]["data_id"]
        monitor_config["bkmonitor_metirc_token"] = bkm_dbm_report["metric"]["token"]

        keylife_config = {
            "stat_dir": DirEnum.REDIS_KEY_LIFE_DIR,
            **RedisActPayload.get_common_config(
                bk_biz_id=bk_biz_id,
                namespace=NameSpaceEnum.RedisCommon,
                conf_file=ConfigFileEnum.Base,
                conf_type=ConfigTypeEnum.Config,
            ),
            "hotkey_conf": RedisActPayload.get_common_config(
                bk_biz_id=bk_biz_id,
                namespace=NameSpaceEnum.RedisCommon,
                conf_file=ConfigFileEnum.HotKey,
                conf_type=ConfigTypeEnum.Config,
            ),
            "bigkey_conf": RedisActPayload.get_common_config(
                bk_biz_id=bk_biz_id,
                namespace=NameSpaceEnum.RedisCommon,
                conf_file=ConfigFileEnum.BigKey,
                conf_type=ConfigTypeEnum.Config,
            ),
        }
        return {
            "bkdbmonpkg": {"pkg": bkdbmon_pkg.name, "pkg_md5": bkdbmon_pkg.md5},
            "dbtoolspkg": {"pkg": tools_pkg.name, "pkg_md5": tools_pkg.md5},
            "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
            "beat_path": env.MYSQL_CROND_BEAT_PATH,
            "backup_client_storage_type": "",  # 留空,使用系统默认
            "redis_fullbackup": fullbackup_config,
            "redis_binlogbackup": binlogbackup_config,
            "redis_heartbeat": heartbeat_config,
            "redis_monitor": monitor_config,
            "redis_keylife": keylife_config,
        }

    def bkdbmon_install(self, **kwargs) -> dict:
        """
        redis bk-dbmon安装
        """

        return {
            "db_type": DBActuatorTypeEnum.Bkdbmon.value,
            "action": DBActuatorTypeEnum.Bkdbmon.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": self.get_bkdbmon_payload_header(str(self.bk_biz_id)),
        }

    @staticmethod
    def get_bkdbmon_servers_params(cluster: Cluster, ip: str) -> dict:
        app = AppCache.get_app_attr(cluster.bk_biz_id, "db_app_abbr")
        app_name = AppCache.get_app_attr(cluster.bk_biz_id, "bk_biz_name")
        ret = {
            "app": app,
            "app_name": app_name,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "cluster_domain": cluster.immute_domain,
            "cache_backup_mode": get_cache_backup_mode(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id),
            "meta_role": "",
            "server_ip": ip,
            "server_ports": [],
            "server_shards": {},
        }
        proxys = cluster.proxyinstance_set.filter(machine__ip=ip)
        storages = cluster.storageinstance_set.filter(machine__ip=ip)
        ports = set()
        if proxys:
            for p in proxys:
                ports.add(p.port)
            ret["server_ports"] = list(ports)
            ret["meta_role"] = proxys.first().machine_type
            return ret
        if storages:
            twemproxy_server_shards = get_twemproxy_cluster_server_shards(
                bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id, other_to_master={}
            )
            for s in storages:
                ports.add(s.port)
            ret["server_ports"] = list(ports)
            ret["meta_role"] = storages.first().instance_role
            ret["server_shards"] = twemproxy_server_shards.get(ip, {})
            return ret
        raise Exception(_("集群{}中没有找到{}相关实例").format(cluster.immute_domain, ip))

    def bkdbmon_install_new(self, **kwargs) -> dict:
        """
        redis new bk-dbmon安装,参数只需传入下面两个
        {
            "clluster_domain":"cache.test.testapp.db",
            "ip":"a.a.a.a"
        }
        """
        params = kwargs["params"]
        cluster: Cluster = None
        try:
            cluster = Cluster.objects.get(immute_domain=params["cluster_domain"])
        except Cluster.DoesNotExist:
            raise Exception("redis cluster {} does not exist".format(params["cluster_domain"]))
        payload = self.get_bkdbmon_payload_header(str(cluster.bk_biz_id))
        if params["is_stop"]:
            payload["servers"] = []
        else:
            payload["servers"] = [RedisActPayload.get_bkdbmon_servers_params(cluster, params["ip"])]
        return {
            "db_type": DBActuatorTypeEnum.Bkdbmon.value,
            "action": DBActuatorTypeEnum.Bkdbmon.value + "_" + RedisActuatorActionEnum.Install.value,
            "payload": payload,
        }

    # 场景化需求
    def __get_redis_pkg(self, cluster_type, db_version):
        if cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.Redis, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.TendisPlus, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.TendisSsd, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TendisPredixyRedisCluster.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.Redis, db_type=DBType.Redis
            )
        elif cluster_type == ClusterType.TendisRedisInstance.value:
            self.redis_pkg = Package.get_latest_package(
                version=db_version, pkg_type=MediumEnum.Redis, db_type=DBType.Redis
            )
        else:
            raise Exception("unknown cluster type:" + cluster_type)

    # redis批量建立主从关系（单实例上架）
    def redis_init_batch_replicate(self, **kwargs) -> dict:
        """
        各实例的密码可能不一样
        [{
            "master_ip":
            "master_port":
            "master_auth":
            "slave_ip":
            "slave_port":
            "slave_password"
        }]
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Replicaof.value,
            "payload": {"replica_pairs": params["replica_pairs"]},
        }

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
        passwd_ret = PayloadHandler.redis_get_password_by_domain(params["immute_domain"])

        replica_pairs = []
        for pair in params["ms_link"]:
            replica_pairs.append(
                {
                    "master_ip": pair["master_ip"],
                    "master_port": int(pair["master_port"]),
                    "slave_ip": pair["slave_ip"],
                    "slave_port": int(pair["slave_port"]),
                    "master_auth": passwd_ret.get("redis_password"),
                    "slave_password": passwd_ret.get("redis_password"),
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
        如果是扩缩容，则可能会有一个origin_db_version表示老集群版本。安装需要拿新版本的二进制，但是配置还是要用老的
        """
        params = kwargs["params"]
        self.namespace = params["cluster_type"]
        self.__get_redis_pkg(params["cluster_type"], params["db_version"])
        if "origin_db_version" in params:
            redis_config = self.__get_cluster_config(
                params["immute_domain"], params["origin_db_version"], ConfigTypeEnum.DBConf
            )
        else:
            redis_config = self.__get_cluster_config(
                params["immute_domain"], params["db_version"], ConfigTypeEnum.DBConf
            )

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
        if is_twemproxy_proxy_type(self.namespace):
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
                # 以下为流程中需要补充的参数
                "ip": params["exec_ip"],
                # "inst_num": params["inst_num"],
                # "start_port": int(params["start_port"]),
            },
        }

    # redis 备份
    def redis_cluster_backup_4_scene(self, **kwargs) -> dict:
        """
        redis 备份
        {"backup_instance":30001,"exec_ip":"","bk_biz_id":1,"immute_domain":"xx","ssd_log_count":{}}
        """
        params = kwargs["params"]
        cluster = Cluster.objects.get(immute_domain=params["immute_domain"])
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Backup.value,
            "payload": {
                "bk_biz_id": str(params["bk_biz_id"]),
                "bk_cloud_id": cluster.bk_cloud_id,
                "domain": params["immute_domain"],
                "ip": params["backup_host"],
                "ports": params["backup_instances"],
                # "start_port":30000,
                # "inst_num":10,
                "backup_type": "normal_backup",
                "without_to_backup_sys": True,  # // 是否上传到备份系统,默认false
                "backup_client_storage_type": "",  # 留空,使用系统默认
                "ssd_log_count": params["ssd_log_count"],
            },
        }

    def redis_shutdown_4_scene(self, **kwargs) -> dict:
        params = kwargs["params"]

        ip = params["exec_ip"]
        ports = params["shutdown_ports"]

        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            "payload": {
                "ip": ip,
                "ports": ports,
                "is_all_instances_shutdown": self.__is_all_instances_shutdown(ip, ports),
            },
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
                "ignore_kill": params["ignore_kill"],
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
        # 需要实时拿
        instances = nosqlcomm.other.get_cluster_proxies(cluster_id=params["cluster_id"])
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorTypeEnum.Twemproxy.value + "_" + RedisActuatorActionEnum.CheckProxysMd5.value,
            "payload": {"instances": instances, "cluster_type": params["cluster_type"]},
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
        if is_twemproxy_proxy_type(self.namespace):
            proxy_version = ConfigFileEnum.Twemproxy
        elif is_predixy_proxy_type(self.namespace):
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
                "src_cluster_name": params["src_cluster_name"],
                "dst_proxy_ip": dst_proxy_ip,
                "dst_proxy_port": int(params["dst_proxy_port"]),
                "dst_proxy_password": params["dst_proxy_password"],
                "dst_cluster_type": params["dst_cluster_type"],
                "dst_redis_ip": params["dst_redis_ip"],
                "dst_redis_port": int(params["dst_redis_port"]),
                "dst_cluster_name": params["dst_cluster_name"],
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
                "src_cluster_name": params["src_cluster_name"],
                "dst_proxy_ip": dst_proxy_ip,
                "dst_proxy_port": int(params["dst_proxy_port"]),
                "dst_proxy_password": params["dst_proxy_password"],
                "dst_cluster_type": params["dst_cluster_type"],
                "dst_redis_ip": params["dst_redis_ip"],
                "dst_redis_port": int(params["dst_redis_port"]),
                "dst_cluster_name": params["dst_cluster_name"],
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
        redis 数据构造 新备份系统
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.DATA_STRUCTURE.value,
            "payload": {
                "source_ip": params["source_ip"],
                "source_ports": params["source_ports"],
                "new_temp_ip": params["new_temp_ip"],
                "new_temp_ports": params["new_temp_ports"],
                "recovery_time_point": params["recovery_time_point"],
                "tendis_type": params["tendis_type"],
                "dest_dir": params["dest_dir"],
                "full_file_list": params["full_file_list"],
                "binlog_file_list": params["binlog_file_list"],
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
         # slots 方式扩容，新节点加到源集群和做主从，这里都可以完成，按下面参数传递就行
        "meet_instances":[
        {
            "master_ip":"aa.bb.cc.dd",
            "master_port":30000,
            "slave_ip":"aa.bb.cc.ff",
            "slave_port":30000
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

    # redis 原地升级
    def redis_cluster_version_update_online_payload(self, **kwargs) -> dict:
        params = kwargs["params"]
        db_version = params["db_version"]
        redis_pkg = get_latest_redis_package_by_version(db_version)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.VERSION_UPDATE.value,
            "payload": {
                "pkg": redis_pkg.name,
                "pkg_md5": redis_pkg.md5,
                "ip": params["ip"],
                "ports": params["ports"],
                "password": params["password"],
                "role": params["role"],
            },
        }

    # redis 原地升级更新dbconfig
    def redis_cluster_version_update_dbconfig(self, cluster_map: dict):
        # 如果版本没变化，不需要更新
        if cluster_map["current_version"] == cluster_map["target_version"]:
            return
        src_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster_map["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_map["cluster_domain"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": cluster_map["current_version"],
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": cluster_map["cluster_type"],
                "format": FormatType.MAP,
            }
        )
        conf_names = self.redis_conf_names_by_cluster_type(cluster_map["cluster_type"], cluster_map["current_version"])
        conf_items = []
        for conf_name in conf_names:
            if conf_name in src_resp["content"]:
                conf_items.append(
                    {"conf_name": conf_name, "conf_value": src_resp["content"][conf_name], "op_type": OpType.UPDATE}
                )
        remove_items = []
        for conf_name in conf_names:
            if conf_name == "cluster-enabled" and cluster_map["current_version"] == RedisVersion.Redis20.value:
                continue
            remove_items.append({"conf_name": conf_name, "op_type": OpType.REMOVE})
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
            "bk_biz_id": str(cluster_map["bk_biz_id"]),
            "level_name": LevelName.CLUSTER,
            "level_value": "",  # 需要替换成真实值
        }
        # 先删除
        upsert_param["conf_file_info"]["namespace"] = cluster_map["cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = cluster_map["current_version"]
        upsert_param["conf_items"] = remove_items
        upsert_param["level_value"] = cluster_map["cluster_domain"]
        logger.info(_("删除集群:{} redis配置,upsert_param:{}".format(cluster_map["cluster_domain"], upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)

        # 再写入
        upsert_param["conf_file_info"]["namespace"] = cluster_map["cluster_type"]
        upsert_param["conf_file_info"]["conf_file"] = cluster_map["target_version"]
        upsert_param["conf_items"] = conf_items
        upsert_param["level_value"] = cluster_map["cluster_domain"]
        logger.info(_("更新集群:{} redis配置 为 目标集群的配置,upsert_param:{}".format(cluster_map["cluster_domain"], upsert_param)))
        DBConfigApi.upsert_conf_item(upsert_param)

    # redis proxy 原地升级
    def redis_proxy_upgrade_online_payload(self, **kwargs) -> dict:
        params = kwargs["params"]
        proxy_pkg: Package = None
        if is_twemproxy_proxy_type(params["cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=TwemproxyVersion.TwemproxyLatest, pkg_type=MediumEnum.Twemproxy, db_type=DBType.Redis
            )
        elif is_predixy_proxy_type(params["cluster_type"]):
            proxy_pkg = Package.get_latest_package(
                version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
            )
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.PROXY_VERSION_UPGRADE.value,
            "payload": {
                "pkg": proxy_pkg.name,
                "pkg_md5": proxy_pkg.md5,
                "ip": params["ip"],
                "port": params["port"],
                "password": params["password"],
                "cluster_type": params["cluster_type"],
            },
        }

    # redis cluster failover
    def redis_cluster_failover(self, **kwargs) -> dict:
        """
        params:
        {
            "redis_password":"xxxx",
            "redis_master_slave_pairs":[
                {
                    "master": {"ip":"a.a.a.a","port":"30000"},
                    "slave": {"ip":"b.b.b.b","port":"30000"}
                },
                {
                    "master": {"ip":"a.a.a.a","port":"30001"},
                    "slave": {"ip":"b.b.b.b","port":"30001"}
                }
            ],
            "force":false
        }
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.CLUSTER_FAILOVER.value,
            "payload": {
                "redis_password": params["redis_password"],
                "redis_master_slave_pairs": params["redis_master_slave_pairs"],
                "force": False,
            },
        }

    # redis slots 迁移，redis slots migrate

    def redis_slots_migrate_4_expansion(self, **kwargs) -> dict:
        """
        {
            "src_node":{
                "ip":"a.0.0.1",
                "port":40000,
                "password":"xxxx"
            },
            "dst_node":{
                "ip":"b.0.0.1",
                "port":47001,
                "password":"xxxx"
            },
            "is_delete_node":false,
            "migrate_specified_slot":false,
            "to_be_del_nodes_addr":[]
            "slots":""
        }
        """
        params = kwargs["params"]
        print(f"params:{params}")
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendisplus.value + "_" + RedisActuatorActionEnum.SLOTS_MIGRATE.value,
            "payload": {
                "src_node": params["src_node"],
                "dst_node": params["dst_node"],
                "is_delete_node": False,
                "to_be_del_nodes_addr": [],
                "migrate_specified_slot": False,
                "slots": "",
            },
        }

    def redis_slots_migrate_4_hotkey(self, **kwargs) -> dict:
        """
        {
            "src_node":{
                "ip":"a.0.0.1",
                "port":40000,
                "password":"xxxx"
            },
            "dst_node":{
                "ip":"b.0.0.1",
                "port":47001,
                "password":"xxxx"
            },
            "slots":"0-100"
            "is_delete_node":false,
            "migrate_specified_slot":true,
            "to_be_del_nodes_addr":[]
        }
        """
        params = kwargs["params"]
        print(f"params:{params}")
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendisplus.value + "_" + RedisActuatorActionEnum.SLOTS_MIGRATE.value,
            "payload": {
                "src_node": params["src_node"],
                "dst_node": params["dst_node"],
                "slots": params["slots"],
                "migrate_specified_slot": True,
                "is_delete_node": False,
                "to_be_del_nodes_addr": [],
            },
        }

    def redis_slots_migrate_4_contraction(self, **kwargs) -> dict:
        """
        {
            "src_node":{
                "ip":"a.0.0.1",
                "port":40000,
                "password":"xxxx"
            },
            "dst_node":{
                "ip":"b.0.0.1",
                "port":47001,
                "password":"xxxx"
            },
            "is_delete_node":True,
            to_be_del_nodes_addr:[xx,xx]
            "migrate_specified_slot":false,
            "slots":""
        }
        """
        params = kwargs["params"]
        print(f"params:{params}")
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Tendisplus.value + "_" + RedisActuatorActionEnum.SLOTS_MIGRATE.value,
            "payload": {
                "src_node": params["src_node"],
                "dst_node": params["dst_node"],
                "is_delete_node": True,
                "to_be_del_nodes_addr": params["to_be_del_nodes_addr"],
                "migrate_specified_slot": False,
                "slots": "",
            },
        }

    def predixy_config_servers_rewrite(self, **kwargs) -> dict:
        """
        Predixy配置文件servers rewrite
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": RedisActuatorActionEnum.PREDIXY_CONFIG_SERVERS_REWRITE.value,
            "payload": {
                "predixy_ip": params["predixy_ip"],
                "predixy_port": params["predixy_port"],
                "to_remove_servers": params.get("to_remove_servers", []),
            },
        }

    def redis_maxmemory_dynamically_set(self, **kwargs) -> dict:
        """
        Redis动态设置 maxmemory
        """
        params = kwargs["params"]
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.MAXMEMORY_DYNAMICALLY_SET.value,
            "payload": {
                "ip": params["ip"],
                "ports": params["ports"],
            },
        }

    def redis_client_conns_kill(self, **kwargs) -> dict:
        """
        Redis kill客户端连接
        """
        params = kwargs["params"]
        cluster = Cluster.objects.get(id=params["cluster_id"])
        # proxy ips排除在kill client conn之外
        proxy_ips = set()
        for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            proxy_ips.add(proxy.machine.ip)
        # 获取 ip 上的ports
        ports = []
        for inst in cluster.storageinstance_set.filter(machine__ip=params["ip"]):
            ports.append(inst.port)
        return {
            "db_type": DBActuatorTypeEnum.Redis.value,
            "action": DBActuatorTypeEnum.Redis.value + "_" + RedisActuatorActionEnum.CLIENT_CONNS_KILL.value,
            "payload": {"ip": params["ip"], "ports": ports, "excluded_ips": list(proxy_ips), "is_force": False},
        }
