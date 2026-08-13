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
from django.utils.translation import gettext as _

from backend.db_services.dbpermission.constants import AccountType
from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum

# 平台业务ID
PLAT_BIZ_ID = 0
# mysql的用户登录admin账号名称
MYSQL_ADMIN_USER = "ADMIN"
# sqlserver的用户登录admin账号名称
SQLSERVER_ADMIN_USER = "dbm_admin"
MYSQL_DATA_RESTORE_TIME = 259200
MYSQL_USUAL_JOB_TIME = 7200
MYSQL8_VER_PARSE_NUM = 8000000


class ProfileLabel(StrStructuredEnum):
    SQL = EnumField("SQL", _("个人收藏SQL"))


class MySQLMonitorPauseTime(IntStructuredEnum):
    RESTORE_DATA = EnumField(1440, _("数据同步时监控屏蔽"))
    SLAVE_DELAY = EnumField(240, _("数据同步时监控屏蔽"))


class DBPrivSecurityType(StrStructuredEnum):
    MYSQL_PASSWORD = EnumField("mysql_password", _("mysql密码策略"))
    REDIS_PASSWORD = EnumField("redis_password_v2", _("redis密码策略"))
    TENDBCLUSTER_PASSWORD = EnumField("tendbcluster_password", _("tendbcluster密码策略"))
    ES_PASSWORD = EnumField("es_password", _("es密码策略"))
    KAFKA_PASSWORD = EnumField("kafka_password", _("kafka密码策略"))
    HDFS_PASSWORD = EnumField("hdfs_password", _("hdfs密码策略"))
    PULSAR_PASSWORD = EnumField("pulsar_password", _("pulsar密码策略"))
    INFLUXDB_PASSWORD = EnumField("influxdb_password", _("influxdb密码策略"))
    SQLSERVER_PASSWORD = EnumField("sqlserver_password", _("sqlserver密码策略"))
    MONGODB_PASSWORD = EnumField("mongodb_password", _("mongodb密码策略"))
    DORIS_PASSWORD = EnumField("doris_password", _("doris密码策略"))

    @classmethod
    def db_type_to_security_type(cls, db_type):
        attr = f"{db_type.upper()}_PASSWORD"
        if not hasattr(cls, attr):
            raise ValueError(_("该组件类型{}没有对应的密码规则").format(db_type))
        return getattr(cls, attr).value


class AdminPasswordRole(StrStructuredEnum):
    """
    定义每个集群中每个node的内置账号名称
    """

    TDBCTL = EnumField("tdbctl", _("tdbctl"))
    SPIDER = EnumField("spider", _("spider"))
    STORAGE = EnumField("storage", _("storage"))


class AffinityEnum(StrStructuredEnum):
    """
    亲和性枚举类
    """

    # 这个swtich 拼写错误不要改, 可能会影响老集群
    SAME_SUBZONE_CROSS_SWTICH = EnumField("SAME_SUBZONE_CROSS_SWTICH", _("指定园区"))
    SAME_SUBZONE = EnumField("SAME_SUBZONE", _("指定园区(无机架要求)"))
    CROS_SUBZONE = EnumField("CROS_SUBZONE", _("跨园区"))
    CROSS_RACK = EnumField("CROSS_RACK", _("不限园区"))
    NONE = EnumField("NONE", _("无"))
    MAX_EACH_ZONE_EQUAL = EnumField("MAX_EACH_ZONE_EQUAL", _("每个subzone尽量均匀分布"))
    # mongodb专属
    CROSS_SUBZONE_STRONG = EnumField("CROSS_SUBZONE_STRONG", _("跨园区(强)"))
    CROSS_SUBZONE_WEAK = EnumField("CROSS_SUBZONE_WEAK", _("跨园区(弱)"))


class DBType(StrStructuredEnum):
    MySQL = EnumField("mysql", _("MySQL"))
    TenDBCluster = EnumField("tendbcluster", _("TenDBCluster"))
    Redis = EnumField("redis", _("Redis"))
    MongoDB = EnumField("mongodb", _("MongoDB"))
    Kafka = EnumField("kafka", _("Kafka"))
    Hdfs = EnumField("hdfs", _("HDFS"))
    Es = EnumField("es", _("ElasticSearch"))
    Pulsar = EnumField("pulsar", _("Pulsar"))
    InfluxDB = EnumField("influxdb", _("InfluxDB"))
    Riak = EnumField("riak", _("Riak"))
    Sqlserver = EnumField("sqlserver", _("SQLServer"))
    Doris = EnumField("doris", _("Doris"))
    Vm = EnumField("vm", _("Vm"))
    Oracle = EnumField("oracle", _("Oracle"))
    # K8s 容器化集群：与 mysql、es 等同级，一种集群类型对应一个 DBType（值与 ClusterType 一致）
    K8sSurrealdb = EnumField("k8s_surrealdb", _("K8s SurrealDB"))
    K8sVictoriametrics = EnumField("k8s_victoriametrics", _("K8s VictoriaMetrics"))
    K8sRisingwave = EnumField("k8s_risingwave", _("K8s Risingwave"))
    K8sMilvus = EnumField("k8s_milvus", _("K8s Milvus"))
    K8sQdrant = EnumField("k8s_qdrant", _("K8s Qdrant"))
    K8sGreptimedb = EnumField("k8s_greptimedb", _("K8s GreptimeDB"))

    # 不属于DB类型，仅用于云区域组件的单据部署的分组
    Cloud = EnumField("cloud", _("Cloud"))

    # 不属于DB类型，仅用于TBinlogDumper实例的管控
    TBinlogDumper = EnumField("tbinlogdumper", _("TBinlogDumper"))


class SystemSettingsEnum(StrStructuredEnum):
    """配置的枚举项，建议将系统配置都录入到这里方便统一管理"""

    MANAGE_TOPO = EnumField("MANAGE_TOPO", _("DBM系统的管理集群拓扑"))
    DBM_SSL = EnumField("DBM_SSL", _("DBM_SSL"))
    BKM_DBM_TOKEN = EnumField("BKM_DBM_TOKEN", _("监控数据源token"))
    BKM_DBM_REPORT = EnumField("BKM_DBM_REPORT", _("mysql/redis-监控自定义上报: dataid/token"))
    BKM_SUBSCRIBE_METRIC = EnumField("BKM_SUBSCRIBE_METRIC", _("订阅指标"))
    FREE_BK_MODULE_ID = EnumField("FREE_BK_MODULE_ID", _("业务空闲模块ID"))
    VIRTUAL_USERS = EnumField("VIRTUAL_USERS", _("平台调用的虚拟账号列表"))
    # 主机默认统一转移到 DBM 业务下托管，若业务 ID 属于这个列表，则转移到对应的业务下
    INDEPENDENT_HOSTING_BIZS = EnumField("INDEPENDENT_HOSTING_BIZS", _("独立托管机器的业务列表"))
    BF_WHITELIST_BIZS = EnumField("BF_WHITELIST_BIZS", _("BF业务白名单"))
    SPEC_OFFSET = EnumField("SPEC_OFFSET", _("默认的规格参数偏移量"))
    DEVICE_CLASSES = EnumField("DEVICE_CLASSES", _("机型列表"))
    BKM_DUTY_NOTICE = EnumField("BKM_DUTY_NOTICE", _("轮值通知设置"))
    DBM_MIGRATE_USER = EnumField("DBM_MIGRATE_USER", _("具备迁移权限的人员名单"))
    BIZ_CONFIG = EnumField("BIZ_CONFIG", _("全业务通用配置信息"))
    AFFINITY = EnumField("AFFINITY", _("容灾要求(各个环境可能不同，比如SG为空)"))
    SYSTEM_MSG_TYPE = EnumField("SYSTEM_MSG_TYPE", _("系统消息通知方式"))
    PADDING_PROXY_CLUSTER_LIST = EnumField("PADDING_PROXY_CLUSTER_LIST", _("补全proxy的集群域名列表"))
    EXCLUSIVE_TICKET_MAP = EnumField("EXCLUSIVE_TICKET_MAP", _("单据互斥表(全局)"))
    # 巡检配置
    DB_REPORT_EXCLUDE_BIZS = EnumField("DB_REPORT_EXCLUDE_BIZS", _("巡检报告排除业务列表"))
    # ITSM配置
    BK_ITSM_SERVICE_ID = EnumField("BK_ITSM_SERVICE_ID", _("DBM的流程服务ID"))
    ITSM_APPROVAL_KEY = EnumField("ITSM_APPROVAL_KEY", _("ITSM审批意见key"))
    ITSM_REMARK_KEY = EnumField("ITSM_REMARK_KEY", _("ITSM备注key"))
    ITSM_V4_SYSTEM_ID = EnumField("ITSM_V4_SYSTEM_ID", _("ITSM V4系统ID"))
    ITSM_V4_WORKFLOW_KEY = EnumField("ITSM_V4_WORKFLOW_KEY", _("ITSM V4工作流key"))
    # SYNC_META 同步元数据
    SYNC_TENDBHA_CLUSTERS = EnumField("SYNC_TENDBHA_CLUSTERS", _("同步TenDBHA集群列表"))
    # 成本预估配置
    COST_ESTIMATE = EnumField("COST_ESTIMATE", _("COST_ESTIMATE"))
    # 主机属性配置
    MACHINE_PROPERTY = EnumField("MACHINE_PROPERTY", _("主机属性开关"))
    PADDING_PROXY_APPS = EnumField("PADDING_PROXY_APPS", _("补全proxy业务"))
    DISABLE_DBHA_APPS_CLUSTER_TYPE = EnumField("DISABLE_DBHA_APPS_CLUSTER_TYPE", _("禁用DBHA业务"))
    # 内置标签列表
    BUILTIN_LABELS = EnumField("BUILTIN_LABELS", _("内置标签列表"))
    # 反向上报事件类型
    # REVERSE_REPORT_EVENT_TYPES = EnumField("REVERSE_REPORT_EVENT_TYPES", _("反向上报事件类型"))
    # 大数据管理端域名映射
    DBM_MANAGE_ADDRESS = EnumField("DBM_MANAGE_ADDRESS", _("大数据管理端域名映射"))
    # Doris使用COS地域映射
    DORIS_COS_REGION = EnumField("DORIS_COS_REGION", _("Doris使用COS地域映射"))
    # Doris使用COS标签
    DORIS_COS_TAGGING = EnumField("DORIS_COS_TAGGING", _("Doris使用COS标签"))
    # Doris 低频存储开关
    DORIS_COS_SWITCH = EnumField("DORIS_COS_SWITCH", _("Doris低频存储开关"))
    # Doris 原地升级版本映射: 取版本号前两位作为 key, value 为允许升级到的 版本号列表
    DORIS_UPGRADE_VERSION_MAP = EnumField("DORIS_UPGRADE_VERSION_MAP", _("Doris原地升级版本映射"))
    # 小额绿通单据申请
    QUICK_MINOR_POAA = EnumField("QUICK_MINOR_POAA", _("小额绿通单据申请"))
    # 资源池独立业务,如果配置该变量,需要联动修改 MANAGE_TOPO::resource.idle.module的值
    RESOURCE_INDEPENDENT_BIZ = EnumField("RESOURCE_INDEPENDENT_BIZ", _("资源池独立业务"))
    # redie删除key限速配置
    REDIS_DELETE_RATE = EnumField("REDIS_DELETE_RATE", _("redie删除key限速配置"))
    # 集群负载判定配置
    CLUSTER_LOAD_RULE = EnumField("CLUSTER_LOAD_RULE", _("集群负载判定配置"))
    # 平台管理运营数据开关
    OPERATION_DATA_SWITCH = EnumField("OPERATION_DATA_SWITCH", _("运营数据开关"))
    # 常用城市配置
    COMMON_CITIES = EnumField("COMMON_CITIES", _("常用城市配置"))
    # 各组件负责的机器人
    DBA_ROBOT = EnumField("DBA_ROBOT", _("各组件负责的机器人"))
    # Redis 回档演练配置
    REDIS_ROLLBACK_EXERCISE = EnumField("REDIS_ROLLBACK_EXERCISE", _("Redis回档演练配置"))
    # Redis 巡检相关配置
    REDIS_CONF_CHECK = EnumField("REDIS_CONF_CHECK", _("Redis配置检查配置"))
    REDIS_ENTRY_CHECK = EnumField("REDIS_ENTRY_CHECK", _("Redis访问入口一致性校验配置"))
    REDIS_AFFINITY_CHECK = EnumField("REDIS_AFFINITY_CHECK", _("Redis亲和性校验配置"))
    REDIS_CLUSTER_CAPACITY_GROWTH_CHECK = EnumField("REDIS_CLUSTER_CAPACITY_GROWTH_CHECK", _("Redis集群容量增长检查配置"))
    REDIS_BACKEND_LOAD_SKEW_CHECK = EnumField("REDIS_BACKEND_LOAD_SKEW_CHECK", _("Redis后端负载倾斜检查配置"))
    REDIS_BACKEND_DATA_SKEW_CHECK = EnumField("REDIS_BACKEND_DATA_SKEW_CHECK", _("Redis后端数据倾斜检查配置"))
    REDIS_REPORT_ADDING_MODE = EnumField("REDIS_REPORT_ADDING_MODE", _("Redis报告写入模式配置"))
    REDIS_BACKUP_CHECK = EnumField("REDIS_BACKUP_CHECK", _("Redis备份巡检配置"))
    # 补货相关配置(内部独有)
    HCM_APPLY_RESOURCE_BIZ = EnumField("HCM_APPLY_RESOURCE_BIZ", _("HCM申请资源业务"))
    HCM_OS_NAME_IMAGE_MAP = EnumField("HCM_OS_NAME_IMAGE_MAP", _("HCM操作系统与镜像ID映射"))
    HCM_REPLENISH_MAINTAINER = EnumField("HCM_REPLENISH_MAINTAINER", _("HCM补货维护人"))
    REPLENISH_RATIO_MAP = EnumField("REPLENISH_RATIO_MAP", _("补货比例"))
    REPLENISH_OS_MAP = EnumField("REPLENISH_OS_MAP", _("补货操作系统映射"))
    REPLENISH_SUBZONE_MAP = EnumField("REPLENISH_SUBZONE_MAP", _("补货园区映射"))
    REPLENISH_EXCLUDED_CITY = EnumField("REPLENISH_EXCLUDED_CITY", _("补货排除城市"))
    # 主机池转移开发配置
    HOST_DISSOLVED_SWITCH = EnumField("HOST_DISSOLVED_SWITCH", _("判断待裁撤主机开关"))
    HOST_TO_FAULT_SWITCH = EnumField("HOST_TO_FAULT_SWITCH", _("转入故障池主机开关"))
    WINDOWS_HOST_TO_RECYCLE_SWITCH = EnumField("WINDOWS_HOST_TO_RECYCLE_SWITCH", _("判断windows主机开关"))
    # AIDEV相关配置
    AI_CODE_SCENE_MAP = EnumField("AI_CODE_SCENE_MAP", _("智能体code场景映射关系表"))
    AGENT_TOKEN_CONFIG = EnumField("AGENT_TOKEN_CONFIG", _("Agent Token配置"))
    # 机器初始化时需要写入 /etc/hosts 的条目，格式：{domain: ip}
    # 示例：{"example.internal.domain": "127.0.0.1"}
    INIT_OS_HOSTS = EnumField("INIT_OS_HOSTS", _("机器初始化hosts配置"))
    # 每日代办提醒配置
    DBM_DAILY_TODO_REMIND = EnumField("DBM_DAILY_TODO_REMIND", _("每日代办提醒配置"))
    # 代办类型和用户映射信息
    DBM_USER_TODO_TYPE_MAP = EnumField("DBM_USER_TODO_TYPE_MAP", _("代办类型和用户映射信息"))
    # 配置介质支持的操作系统列表和版本
    PACKAGE_SUPPORT_SYSTEMS = EnumField("PACKAGE_SUPPORT_SYSTEMS", _("介质支持的操作系统"))
    DB_PACKAGE_SETTINGS = EnumField("DB_PACKAGE_SETTINGS", _("DB介质配置表"))
    DISABLE_DBHA_AUTOFIX_APPS = EnumField("DISABLE_DBHA_AUTOFIX_APPS", _("DBHA业务自动修复开关"))
    # 平台内置兜底告警组信息
    PLATFORM_ALERT_GROUP_INFO = EnumField("PLATFORM_ALERT_GROUP_INFO", _("平台内置兜底告警组信息"))


class DisableDBHAAutofixLevel(StrStructuredEnum):
    CLUSTER_TYPE = EnumField("cluster_type", _("集群类型"))
    CLUSTER = EnumField("cluster", _("集群"))
    MACHINE_TYPE = EnumField("machine_type", _("机器类型"))


class BizSettingsEnum(StrStructuredEnum):
    """配置的枚举项，建议将业务配置都录入到这里方便统一管理"""

    OPEN_AREA_VARS = EnumField("OPEN_AREA_VARS", _("开区模板的渲染变量"))
    INDEPENDENT_HOSTING_DB_TYPES = EnumField("INDEPENDENT_HOSTING_DB_TYPES", _("独立托管机器的数据库类型"))
    # TODO: SKIP_GRAMMAR_CHECK 后续待删除
    SKIP_GRAMMAR_CHECK = EnumField("SKIP_GRAMMAR_CHECK", _("是否跳过语义检查"))
    SQL_IMPORT_FORCE_ITSM = EnumField("SQL_IMPORT_FORCE_ITSM", _("是否变更SQL强制需要审批流"))
    BIZ_ASSISTANCE_VARS = EnumField("BIZ_ASSISTANCE_VARS", _("业务协助人员变量"))
    BIZ_ASSISTANCE_SWITCH = EnumField("BIZ_ASSISTANCE_SWITCH", _("业务协助开关"))
    NOTIFY_CONFIG = EnumField("NOTIFY_CONFIG", _("业务通知渠道配置"))


class RedisFastRecoverEnum(StrStructuredEnum):
    """Redis 快速剔除、恢复 统一入口管理"""

    PROXY_ENTRY_KICKOFF = EnumField("PROXY_ENTRY_KICKOFF", _("踢掉所有接入层"))
    PROXY_ENTRY_FIX = EnumField("PROXY_ENTRY_FIX", _("修复接入层"))
    SLAVE_REUSE_FIX = EnumField("SLAVE_REUSE_FIX", _("SLAVE重启后复用"))


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

# 默认的规格预估成本模板
COST_ESTIMATE_TEMPLATE = {
    # cpu核数价格
    "cpu": 0,
    # 内存/G
    "mem": 0,
    # 磁盘/G
    "storage": {"SSD": 0, "CLOUD_SSD": 0, "HDD": 0, "LOCAL_HDD": 0, "ALL": 0},
}

# 磁盘类型，目前固定写死
DISK_CLASSES = ["SSD", "CLOUD_SSD", "HDD", "LOCAL_HDD", "ALL"]
# 磁盘类型和海磊(腾讯云)申请盘映射
HCM_DISK_CLASS_MAP = {"CLOUD_SSD": "CLOUD_SSD", "HDD": "CLOUD_PREMIUM", "ALL": "CLOUD_PREMIUM"}

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
    "OPEN_AREA_VARS": [{"desc": "APP", "name": "APP", "builtin": True}],
    # 业务单据通知默认变量
    "NOTIFY_CONFIG": {
        "TODO": {"rtx": True},
        "FAILED": {"rtx": True},
        "APPROVE": {"rtx": True},
        "SUCCEEDED": {"rtx": True},
        "INNER_TODO": {"rtx": True},
        "TERMINATED": {"rtx": True},
        "RESOURCE_REPLENISH": {"rtx": True},
    },
}

# 默认的环境容灾要求: 同城同园区，同城跨园区，同城无园区
AFFINITY_VALUE = [
    {
        "value": AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
        "label": AffinityEnum.get_choice_label(AffinityEnum.SAME_SUBZONE_CROSS_SWTICH),
    },
    {"value": AffinityEnum.CROSS_RACK, "label": AffinityEnum.get_choice_label(AffinityEnum.CROSS_RACK)},
    {"value": AffinityEnum.CROS_SUBZONE, "label": AffinityEnum.get_choice_label(AffinityEnum.CROS_SUBZONE)},
]

# 默认机器属性设置
DEFAULT_MACHINE_PROPERTY = {
    "rack_id": True,  # 机架
    "city_meta": True,  # 地域
    "device_class": True,  # 机型
    "sub_zone_meta": True,  # 园区
    "storage_device": True,  # 磁盘
}

# 默认介质支持的操作系统
DEFAULT_PACKAGE_SUPPORT_SYSTEMS = {"linux": ["ubuntu", "centos7", "centos8"], "windows": ["win7", "win10"]}

# 默认智能体场景映射表
DEFAULT_AI_CODE_SCENE_MAP = {"log_analysis": {"default": "LogAnalysis"}}

# DEFAULT_REVERSE_REPORT_EVENT_TYPES = ["mysql_dbbackup_result", "mysql_dbbackup_progress", "mysql_binlog_result"]

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
    [SystemSettingsEnum.AFFINITY, "list", AFFINITY_VALUE, _("环境的容灾要求")],
    [SystemSettingsEnum.SYSTEM_MSG_TYPE, "list", ["weixin", "mail"], _("系统消息通知方式")],
    [SystemSettingsEnum.PADDING_PROXY_CLUSTER_LIST, "list", [], _("补全proxy的集群域名列表")],
    [SystemSettingsEnum.VIRTUAL_USERS, "list", [], _("平台调用的虚拟账户列表")],
    [SystemSettingsEnum.MACHINE_PROPERTY, "dict", DEFAULT_MACHINE_PROPERTY, _("主机属性开关配置")],
    [SystemSettingsEnum.PADDING_PROXY_APPS, "list", [], _("补全proxy业务")],
    [SystemSettingsEnum.DISABLE_DBHA_APPS_CLUSTER_TYPE, "dict", {}, _("禁用DBHA业务")],
    # [SystemSettingsEnum.REVERSE_REPORT_EVENT_TYPES, "list", DEFAULT_REVERSE_REPORT_EVENT_TYPES, _("反向上报事件类型")],
    [SystemSettingsEnum.OPERATION_DATA_SWITCH.value, "bool", False, _("运营数据开关")],
    [SystemSettingsEnum.AI_CODE_SCENE_MAP.value, "str", DEFAULT_AI_CODE_SCENE_MAP, _("智能体code场景映射关系表")],
    # list[dict], 每条规则: {
    #     "bk_biz_id": int,                 (必填) 业务ID
    #     "cluster_type": str,              (必填) 集群类型, 如 "tendbha", "tendbcluster"
    #     "disable_level": str,             (必填) DisableDBHAAutofixLevel 枚举值: "cluster_type" | "cluster" | "machine_type"
    #     "disable_value": str/int,         disable_level 为 "cluster_type" 时无意义;
    #                                       为 "cluster" 时填 cluster_id;
    #                                       为 "machine_type" 时填 machine_type 字符串, 如 "proxy", "backend"
    # }
    [SystemSettingsEnum.DISABLE_DBHA_AUTOFIX_APPS, "list", [], _("禁用DBHA自动修复配置")],
    [SystemSettingsEnum.PACKAGE_SUPPORT_SYSTEMS.value, "dict", DEFAULT_PACKAGE_SUPPORT_SYSTEMS, _("介质支持的操作系统")],
]

# 环境配置项 是否支持DNS解析 pulsar flow used
DOMAIN_RESOLUTION_SUPPORT = "DOMAIN_RESOLUTION_SUPPORT"

# DB组件和admin用户的映射
DB_ADMIN_USER_MAP = {
    DBType.TenDBCluster: MYSQL_ADMIN_USER,
    DBType.MySQL: MYSQL_ADMIN_USER,
    DBType.Sqlserver: SQLSERVER_ADMIN_USER,
}

# 权限规则账号创建不允许的账号名映射
ACCOUNT_RULES_MAP = {
    AccountType.SQLServer: ["mssql_exporter", "dbm_admin", "sa", "sqlserver"],
    AccountType.MONGODB: ["dba", "apppdba", "monitor", "appmonitor"],
    AccountType.MYSQL: [
        "gcs_admin",
        "gcs_dba",
        "MONITOR",
        "GM",
        "ADMIN",
        "repl",
        "dba_bak_all_sel",
        "yw",
        "partition_yw",
        "spider",
        "mysql.session",
        "mysql.sys",
        "gcs_spider",
        "sync",
    ],
    AccountType.TENDBCLUSTER: [
        "gcs_admin",
        "gcs_dba",
        "MONITOR",
        "GM",
        "ADMIN",
        "repl",
        "dba_bak_all_sel",
        "yw",
        "partition_yw",
        "spider",
        "mysql.session",
        "mysql.sys",
        "gcs_spider",
        "sync",
    ],
}

DAILY_TODO_REMIND_DEFAULT = {
    "is_enable": False,
    "remind_time": {
        "minute": "0",
        "hour": "9",
    },
    "notice": [{"type": "rtx", "value": ""}],
}

DBM_USER_TODO_TYPE_MAP_DEFAULT = {
    "types": {
        "ticket_todo": _("单据待办"),
        "inspect_todo": _("巡检待办"),
        "cluster_disable_todo": _("集群下架待办"),
        "host_todo": _("主机处理待办"),
        "alarm_todo": _("告警事件待办"),
        "risk_memo_todo": _("风险备忘录"),
    },
    "ordinary": ["ticket_todo", "cluster_disable_todo"],
    "dba": ["ticket_todo", "inspect_todo", "cluster_disable_todo", "host_todo", "alarm_todo", "risk_memo_todo"],
}

BIZ_DEFAULT_CONFIGS = {
    "NOTIFY_CONFIG": {
        "APPROVE": {"rtx": True},
        "FAILED": {"rtx": True},
        "INNER_TODO": {"rtx": True},
        "PENDING": {"rtx": True},
        "RESOURCE_REPLENISH": {"rtx": True},
        "REVOKED": {"rtx": True},
        "SUCCEEDED": {"rtx": True},
        "TERMINATED": {"rtx": True},
        "TODO": {"rtx": True},
        "AI_TASK_GUARDIAN": {"rtx": True},
    },
    "DEFAULT_BIZ_AI_NOTIFY_CONFIG": {"AI_TASK_GUARDIAN": {"rtx": True}},
    "BIZ_ASSISTANCE_SWITCH": False,
    "BIZ_ASSISTANCE_VARS": [],
    "INDEPENDENT_HOSTING_DB_TYPES": [],
}
