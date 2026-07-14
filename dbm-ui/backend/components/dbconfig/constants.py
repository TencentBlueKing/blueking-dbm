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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

DEPLOY_FILE_NAME = "deploy_info"


class LevelName(StrStructuredEnum):
    """层级名称枚举"""

    PLAT = EnumField("plat", _("平台层级"))
    APP = EnumField("app", _("业务层级"))
    MODULE = EnumField("module", _("模块层级"))
    CLUSTER = EnumField("cluster", _("集群层级"))
    INSTANCE = EnumField("instance", _("实例层级"))
    CLOUD = EnumField("bk_cloud_id", _("云区域层级"))


class ConfType(StrStructuredEnum):
    """配置类型枚举"""

    DEPLOY = EnumField("deploy", _("部署配置"))
    DBCONF = EnumField("dbconf", _("数据库配置"))
    BACKUP = EnumField("backup", _("备份配置"))
    PROXY = EnumField("proxyconf", _("Proxy配置"))
    CONFIG = EnumField("config", _("公共配置"))
    MYSQL_MONITOR = EnumField("mysql_monitor", _("MySQL监控配置"))
    CHECKSUM = EnumField("checksum", _("Checksum配置"))
    BACKUP_CLIENT = EnumField("backup_client", _("备份客户端配置"))
    ALARM = EnumField("alarm", _("告警配置"))
    DORIS_RUNTIME_CONFIG = EnumField("doris_runtime_config", _("Doris运行时配置"))


class OpType(StrStructuredEnum):
    """操作类型枚举"""

    ADD = EnumField("add", _("新增"))
    UPDATE = EnumField("update", _("更新"))
    REMOVE = EnumField("remove", _("删除"))


class ReqType(StrStructuredEnum):
    """请求类型枚举"""

    SAVE_ONLY = EnumField("SaveOnly", _("仅保存"))
    GENERATE_AND_SAVE = EnumField("GenerateAndSave", _("生成并保存"))
    SAVE_AND_PUBLISH = EnumField("SaveAndPublish", _("保存并发布"))
    GENERATE_AND_PUBLISH = EnumField("GenerateAndPublish", _("生成并发布"))


class FormatType(StrStructuredEnum):
    """格式枚举"""

    LIST = EnumField("list", _("列表"))
    MAP = EnumField("map", _("字典"))
    MAP_LEVEL = EnumField("map.", _("分级字典"))


class ConfFile(StrStructuredEnum):
    """配置文件枚举

    MySQL:
      存储层参数: conf_type=dbconf, conf_file=MySQL-XX (如 MySQL-5.7)
      接入层参数: conf_type=dbconf, conf_file=Spider-xxx (仅 tendbcluster)
    Redis:
      存储层参数: conf_type=dbconf, conf_file=Redis-XX / TendisSSD-xxx / Tendisplus-xxx
      代理参数: conf_type=proxyconf, conf_file=Twemproxy-latest / Predixy-latest
    MongoDB:
      ReplicaSet: conf_type=dbconf, conf_file=mongod.conf
      ShardedCluster: conf_type=dbconf, conf_file=shardsvr.conf / configsvr.conf / mongos.conf
      兼容旧版: mongodb-M.m / Mongodb-M（仅存量读/迁移）
      bk-dbmon: conf_type=config, conf_file=bk-dbmon (segment.key 形式，见 cluster_config.go)
    ES/Kafka/HDFS/Pulsar/Doris:
      conf_type=dbconf, conf_file=x.x.x (版本号)
    """

    DEPLOY_INFO = EnumField("deploy_info", _("部署信息"))
    # ----- MySQL -----
    ITEMS_CONFIG = EnumField("items-config.yaml", _("本地监控配置"))
    DBBACKUP_INI = EnumField("dbbackup.ini", _("全备配置选项"))
    DBBACKUP_OPTIONS = EnumField("dbbackup.options", _("全备控制选项"))
    BINLOG_ROTATE = EnumField("binlog_rotate.yaml", _("Binlog备份配置"))
    CHECKSUM = EnumField("checksum.yaml", _("校验配置"))
    COSINFO = EnumField("cosinfo.toml", _("备份远程存储配置"))

    # ----- Redis -----
    BACKUP = EnumField("backup", _("备份参数"))
    FULLBACKUP = EnumField("fullbackup", _("全备参数"))
    BINLOGBACKUP = EnumField("binlogbackup", _("Binlog备份参数"))
    MONITOR = EnumField("monitor", _("监控参数"))
    TWEMPROXY = EnumField("Twemproxy-latest", _("Twemproxy代理配置"))
    PREDIXY = EnumField("Predixy-latest", _("Predixy代理配置"))

    # ----- MongoDB -----
    OSCONF = EnumField("osconf", _("OS公共配置"))
    MONGOD = EnumField("mongod.conf", _("mongod配置"))
    SHARDSVR = EnumField("shardsvr.conf", _("shardsvr配置"))
    CONFIGSVR = EnumField("configsvr.conf", _("configsvr配置"))
    MONGOS = EnumField("mongos.conf", _("mongos配置"))

    # ----- SQLServer -----
    DBBACKUP_CONF = EnumField("dbbackup.conf", _("备份配置"))
    ALARM_CONF = EnumField("alarm.conf", _("告警配置"))


class MysqlDefaultDeployConfig:
    """MySQL默认部署配置"""

    DB_VERSION = "MySQL-5.7"
    CHARSET = "utf8mb4"
