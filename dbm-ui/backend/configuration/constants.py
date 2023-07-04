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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import ugettext as _

# 平台业务ID
from backend.db_services.ipchooser.constants import DEFAULT_CLOUD

PLAT_BIZ_ID = 0


class DBType(str, StructuredEnum):
    MySQL = EnumField("mysql", _("MySQL"))
    Tendb = EnumField("tendbcluster", _("TendbCluster"))
    Redis = EnumField("redis", _("Redis"))
    Kafka = EnumField("kafka", _("Kafka"))
    Hdfs = EnumField("hdfs", _("HDFS"))
    Es = EnumField("es", _("ElasticSearch"))
    Pulsar = EnumField("pulsar", _("Pulsar"))
    InfluxDB = EnumField("influxdb", _("InfluxDB"))
    Riak = EnumField("riak", _("Riak"))

    # 不属于DB类型，仅用于云区域组件的单据部署的分组
    Cloud = EnumField("cloud", _("Cloud"))


DEFAULT_DB_ADMINISTRATORS = ["admin"]

# TODO 域名模板是否可配置，调整后会带来额外的管理成本？
MASTER_DOMAIN_INITIAL_VALUE = "{db_module_name}db.{cluster_name}.{db_app_abbr}.db"
SLAVE_DOMAIN_INITIAL_VALUE = "{db_module_name}dr.{cluster_name}.{db_app_abbr}.db"

# 初始化密码校验规则
INIT_PASSWORD_POLICY = {
    "follow": {
        "limit": 4,
        "letters": False,
        "numbers": False,
        "repeats": False,
        "symbols": False,
        "keyboards": False,
    },
    "numbers": True,
    "symbols": True,
    "lowercase": True,
    "uppercase": True,
    "max_length": 32,
    "min_length": 8,
}

DBM_SSL = "DBM_SSL"
# 监控数据源token
BKM_DBM_TOKEN = "BKM_DBM_TOKEN"
# mysql/redis-监控自定义上报: dataid/token
BKM_DBM_REPORT = "BKM_DBM_REPORT"
# 默认资源池空闲模块
RESOURCE_TOPO = "RESOURCE_TOPO"


# 业务空闲模块ID
FREE_BK_MODULE_ID = "FREE_BK_MODULE_ID"

# 监控数据自定义上报配置
DBM_REPORT_INITIAL_VALUE = {
    "proxy": {DEFAULT_CLOUD: _("请补充：指定云区域的proxy信息")},
    "metric": {
        "data_id": _("请补充：自定义指标-数据ID"),
        "token": _("请补充：自定义指标-Token"),
    },
    "event": {
        "data_id": _("请补充：自定义事件-数据ID"),
        "token": _("请补充：自定义事件-Token"),
    },
}

DEFAULT_SETTINGS = [
    # [key, 类型，初始值, 描述]
    [BKM_DBM_TOKEN, "str", "", _("监控数据源token")],
    [BKM_DBM_REPORT, "dict", DBM_REPORT_INITIAL_VALUE, _("监控数据源上报配置")],
    [FREE_BK_MODULE_ID, "str", "0", _("业务空闲模块ID")],
]

# 环境配置项 是否支持DNS解析 pulsar flow used
DOMAIN_RESOLUTION_SUPPORT = "DOMAIN_RESOLUTION_SUPPORT"
