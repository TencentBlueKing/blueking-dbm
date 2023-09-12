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
    TenDBCluster = EnumField("tendbcluster", _("TendbCluster"))
    Redis = EnumField("redis", _("Redis"))
    MongoDB = EnumField("mongodb", _("MongoDB"))
    Kafka = EnumField("kafka", _("Kafka"))
    Hdfs = EnumField("hdfs", _("HDFS"))
    Es = EnumField("es", _("ElasticSearch"))
    Pulsar = EnumField("pulsar", _("Pulsar"))
    InfluxDB = EnumField("influxdb", _("InfluxDB"))
    Riak = EnumField("riak", _("Riak"))

    # 不属于DB类型，仅用于云区域组件的单据部署的分组
    Cloud = EnumField("cloud", _("Cloud"))


class SystemSettingsEnum(str, StructuredEnum):
    """配置的枚举项，建议将系统配置都录入到这里方便统一管理"""

    BK_ITSM_SERVICE_ID = EnumField("BK_ITSM_SERVICE_ID", _("DBM的流程服务ID"))
    MANAGE_TOPO = EnumField("MANAGE_TOPO", _("DBM系统的管理集群拓扑"))
    DBM_SSL = EnumField("DBM_SSL", _("DBM_SSL"))
    BKM_DBM_TOKEN = EnumField("BKM_DBM_TOKEN", _("监控数据源token"))
    BKM_DBM_REPORT = EnumField("BKM_DBM_REPORT", _("mysql/redis-监控自定义上报: dataid/token"))
    FREE_BK_MODULE_ID = EnumField("FREE_BK_MODULE_ID", _("业务空闲模块ID"))
    # 主机默认统一转移到 DBM 业务下托管，若业务 ID 属于这个列表，则转移到对应的业务下
    INDEPENDENT_HOSTING_BIZS = EnumField("INDEPENDENT_HOSTING_BIZS", _("独立托管机器的业务列表"))
    SPEC_OFFSET = EnumField("SPEC_OFFSET", _("默认的规格参数偏移量"))


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

# 默认的规格参数偏移量，磁盘为0，内存偏移1G
SPEC_OFFSET_VALUE = {"mem": 1024, "disk": 0}

DEFAULT_SETTINGS = [
    # [key, 类型，初始值, 描述]
    [SystemSettingsEnum.BKM_DBM_TOKEN.value, "str", "", _("监控数据源token")],
    [SystemSettingsEnum.BKM_DBM_REPORT.value, "dict", DBM_REPORT_INITIAL_VALUE, _("监控数据源上报配置")],
    [SystemSettingsEnum.FREE_BK_MODULE_ID.value, "str", "0", _("业务空闲模块ID")],
    [SystemSettingsEnum.INDEPENDENT_HOSTING_BIZS.value, "list", [], _("独立托管机器的业务列表")],
    [SystemSettingsEnum.SPEC_OFFSET.value, "dict", SPEC_OFFSET_VALUE, _("默认的规格参数偏移量")],
]

# 环境配置项 是否支持DNS解析 pulsar flow used
DOMAIN_RESOLUTION_SUPPORT = "DOMAIN_RESOLUTION_SUPPORT"
