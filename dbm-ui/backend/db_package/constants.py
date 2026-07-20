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
import re

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.flow.consts import MediumEnum
from blue_krill.data_types.enum import EnumField, StrStructuredEnum

DB_PACKAGE_TAG = "db_package"
PARSE_FILE_EXT = re.compile(r"^.*?[.](?P<ext>tar\.gz|tar\.bz2|\w+)$")


class PackageMode(StrStructuredEnum):
    """包模式枚举"""

    USER = EnumField("user", _("用户定义"))
    SYSTEM = EnumField("system", _("系统内置"))


PackageType = MediumEnum

# 各个组件的安装包类型
INSTALL_PACKAGE_LIST = {
    DBType.MySQL: [PackageType.MySQLProxy, PackageType.MySQL, PackageType.Spider, PackageType.tdbCtl],
    DBType.Es: [PackageType.Es],
    DBType.Hdfs: [PackageType.Hdfs],
    DBType.Kafka: [PackageType.Kafka],
    DBType.Pulsar: [PackageType.Pulsar],
    DBType.InfluxDB: [PackageType.Influxdb],
    DBType.Redis: [
        PackageType.Redis,
        PackageType.Twemproxy,
        PackageType.TendisPlus,
        PackageType.TendisSsd,
        PackageType.Predixy,
    ],
    DBType.Sqlserver: [PackageType.Sqlserver],
    DBType.Doris: [PackageType.Doris],
}

# 各个组件的初始化pkg归属
# distributions 声明该 pkg_type 对应的发行版列表 [(发行版名, 引擎), ...]，取值参考 medium.lock；
# 不填则默认 [("DBM", "")]。发行版用于新版本管理(sync_medium 按发行版匹配介质)。
INIT_DB_PKG_SETTINGS = {
    DBType.MySQL.value: [
        # mysql server 介质区分 TMySQL(5.7) 与 Community(8.0)，非 DBM
        {"value": PackageType.MySQL, "version_num": 6, "distributions": [("TMySQL", ""), ("Community", "")]},
        {"value": PackageType.MySQLProxy, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
        {"value": PackageType.DbBackup, "version_num": 3, "distributions": [("Community", "")]},
        {"value": PackageType.DbBackupTXSQL, "version_num": 3},
        {"value": PackageType.MySQLChecksum, "version_num": 3},
        {"value": PackageType.MySQLRotateBinlog, "version_num": 3},
        {"value": PackageType.MySQLToolKit, "version_num": 3},
        {"value": PackageType.MySQLMonitor, "version_num": 3},
        {"value": PackageType.MySQLCrond, "version_num": 3},
        {"value": PackageType.Spider, "version_num": 6, "distributions": [("TMySQL", "")]},
        {"value": PackageType.tdbCtl, "version_num": 6, "distributions": [("TMySQL", "")]},
        {"value": PackageType.TBinlogDumper, "version_num": 6},
    ],
    DBType.Redis.value: [
        {"value": PackageType.Redis, "version_num": 3},
        {"value": PackageType.Twemproxy, "version_num": 6},
        {"value": PackageType.TendisPlus, "version_num": 3},
        {"value": PackageType.TendisSsd, "version_num": 3},
        {"value": PackageType.Predixy, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
        {"value": PackageType.RedisTools, "version_num": 3},
        {"value": PackageType.DbMon, "version_num": 3},
        {"value": PackageType.RedisDts, "version_num": 3},
        {"value": PackageType.RedisModules, "version_num": 3},
    ],
    DBType.MongoDB.value: [
        {"value": PackageType.MongoDB, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
        {"value": PackageType.DbMon, "version_num": 3},
        {"value": PackageType.DBTools, "version_num": 3},
        {"value": PackageType.MongoToolKit, "version_num": 3},
    ],
    DBType.Es.value: [
        {"value": PackageType.Es, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Hdfs.value: [
        {"value": PackageType.Hdfs, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Kafka.value: [
        {"value": PackageType.Kafka, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Pulsar.value: [
        {"value": PackageType.Pulsar, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Riak.value: [
        {"value": PackageType.Riak, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
        {"value": PackageType.RiakMonitor, "version_num": 3},
    ],
    DBType.Sqlserver.value: [
        {"value": PackageType.Sqlserver, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Doris.value: [
        {"value": PackageType.Doris, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
    DBType.Oracle.value: [
        {"value": PackageType.Oracle, "version_num": 3},
        {"value": PackageType.DBActuator, "version_num": 3},
    ],
}
