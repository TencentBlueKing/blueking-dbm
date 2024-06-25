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

from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.flow.consts import MediumEnum
from blue_krill.data_types.enum import EnumField, StructuredEnum

DB_PACKAGE_TAG = "db_package"
PARSE_FILE_EXT = re.compile(r"^.*?[.](?P<ext>tar\.gz|tar\.bz2|\w+)$")


class PackageMode(str, StructuredEnum):
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
