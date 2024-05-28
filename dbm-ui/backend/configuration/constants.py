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
from django.utils.translation import ugettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 平台业务ID
PLAT_BIZ_ID = 0
DBM_PASSWORD_SECURITY_NAME = "password"
DBM_MYSQL_ADMIN_USER = "ADMIN"
# TODO: job超时时间最大为86400，后续考虑让job平台调大限制
MYSQL_DATA_RESTORE_TIME = 259200
MYSQL_USUAL_JOB_TIME = 7200


class AffinityEnum(str, StructuredEnum):
    """
    亲和性枚举类
    """

    # 这个swtich 拼写错误不要改, 可能会影响老集群
    SAME_SUBZONE_CROSS_SWTICH = EnumField("SAME_SUBZONE_CROSS_SWTICH", _("同城同subzone跨交换机跨机架"))
    SAME_SUBZONE = EnumField("SAME_SUBZONE", _("同城同subzone"))
    CROS_SUBZONE = EnumField("CROS_SUBZONE", _("CROS_SUBZONE"))
    CROSS_RACK = EnumField("CROSS_RACK", _("跨机架"))
    NONE = EnumField("NONE", _("NONE"))
    MAX_EACH_ZONE_EQUAL = EnumField("MAX_EACH_ZONE_EQUAL", _("每个subzone尽量均匀分布"))


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
    Sqlserver = EnumField("sqlserver", _("sqlserver"))

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
    DEVICE_CLASSES = EnumField("DEVICE_CLASSES", _("机型列表"))
    BKM_DUTY_NOTICE = EnumField("BKM_DUTY_NOTICE", _("轮值通知设置"))
    DBM_MIGRATE_USER = EnumField("DBM_MIGRATE_USER", _("具备迁移权限的人员名单"))
    BIZ_CONFIG = EnumField("BIZ_CONFIG", _("全业务通用配置信息"))
    AFFINITY = EnumField("AFFINITY", _("容灾要求(各个环境可能不同，比如SG为空)"))
    SYSTEM_MSG_TYPE = EnumField("SYSTEM_MSG_TYPE", _("系统消息通知方式"))
    PADDING_PROXY_CLUSTER_LIST = EnumField("PADDING_PROXY_CLUSTER_LIST", _("补全proxy的集群域名列表"))


class BizSettingsEnum(str, StructuredEnum):
    """配置的枚举项，建议将业务配置都录入到这里方便统一管理"""

    OPEN_AREA_VARS = EnumField("OPEN_AREA_VARS", _("开区模板的渲染变量"))
    INDEPENDENT_HOSTING_DB_TYPES = EnumField("INDEPENDENT_HOSTING_DB_TYPES", _("独立托管机器的数据库类型"))


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
    "proxy": "127.0.0.1",
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

# 磁盘类型，目前固定写死
DISK_CLASSES = ["SSD", "HDD", "ALL"]

# 默认轮值通知配置
BKM_DUTY_NOTICE_VALUE = {
    "schedule_table": {
        "enable": False,
        "send_at": {"freq": "w", "freq_values": [], "time": ""},
        "send_day": 7,
        "qywx_id": 0,
    },
    "person_duty": {
        "enable": False,
        "send_at": {
            "unit": "h",
            "num": 0,
        },
    },
}

# 默认的全业务配置信息
BIZ_CONFIG_INFO = {
    # 开区默认内置变量
    "OPEN_AREA_VARS": [{"desc": "APP", "name": "APP", "builtin": True}]
}

# 默认的环境容灾要求
AFFINITY_VALUE = []

# 默认具备迁移权限的人员
DBM_DEFAULT_MIGRATE_USER = ["admin"]

DEFAULT_SETTINGS = [
    # [key, 类型，初始值, 描述]
    [SystemSettingsEnum.BKM_DBM_TOKEN.value, "str", "", _("监控数据源token")],
    [SystemSettingsEnum.BKM_DBM_REPORT.value, "dict", DBM_REPORT_INITIAL_VALUE, _("监控数据源上报配置")],
    [SystemSettingsEnum.FREE_BK_MODULE_ID.value, "str", "0", _("业务空闲模块ID")],
    [SystemSettingsEnum.INDEPENDENT_HOSTING_BIZS.value, "list", [], _("独立托管机器的业务列表")],
    [SystemSettingsEnum.SPEC_OFFSET.value, "dict", SPEC_OFFSET_VALUE, _("默认的规格参数偏移量")],
    [SystemSettingsEnum.BKM_DUTY_NOTICE.value, "dict", BKM_DUTY_NOTICE_VALUE, _("默认通知配置")],
    [SystemSettingsEnum.DBM_MIGRATE_USER, "list", DBM_DEFAULT_MIGRATE_USER, _("具备迁移权限的人员名单")],
    [SystemSettingsEnum.BIZ_CONFIG, "dict", BIZ_CONFIG_INFO, _("默认的全业务配置信息")],
    [SystemSettingsEnum.AFFINITY, "list", [], _("环境的容灾要求")],
    [SystemSettingsEnum.SYSTEM_MSG_TYPE, "list", ["weixin", "mail"], _("系统消息通知方式")],
]

# 环境配置项 是否支持DNS解析 pulsar flow used
DOMAIN_RESOLUTION_SUPPORT = "DOMAIN_RESOLUTION_SUPPORT"
