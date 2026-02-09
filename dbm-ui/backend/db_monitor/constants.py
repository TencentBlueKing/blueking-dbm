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
import os

from django.conf import settings
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, MachineType
from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum

DB_MONITOR_TPLS_DIR = os.path.join(settings.BASE_DIR, "backend/db_monitor/tpls")
TPLS_COLLECT_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "collect")
TPLS_ALARM_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "alarm")

SWAGGER_TAG = "db_monitor"


class GroupType(StrStructuredEnum):
    """告警组类别: 平台级->业务级->集群级->一次性"""

    PLATFORM = EnumField("PLATFORM", _("platform"))
    APP = EnumField("APP", _("app"))
    CLUSTER = EnumField("CLUSTER", _("cluster"))
    SINGLE = EnumField("SINGLE", _("single"))


class DutyRuleCategory(StrStructuredEnum):
    """轮值规则分类"""

    REGULAR = EnumField("regular", _("固定值班"))
    HANDOFF = EnumField("handoff", _("交替轮值"))


class TargetLevel(StrStructuredEnum):
    """告警策略类别: 平台级->业务级->模块级->集群级->实例级
    ROLE: 角色不确定所处的位置
    CUSTOM: 用于表达额外过滤条件
    """

    PLATFORM = EnumField("platform", _("platform"))
    APP = EnumField("appid", _("app id"))
    MODULE = EnumField("db_module", _("db module"))
    CLUSTER = EnumField("cluster_domain", _("cluster domain"))
    CUSTOM = EnumField("custom", _("custom"))


class TargetPriority(IntStructuredEnum):
    """监控策略优先级: 0-10000"""

    PLATFORM = EnumField(0, _("platform"))
    APP = EnumField(1, _("app id"))
    MODULE = EnumField(10, _("db module"))
    CLUSTER = EnumField(100, _("cluster domain"))
    CUSTOM = EnumField(5000, _("custom"))


TARGET_LEVEL_TO_PRIORITY = {
    TargetLevel.PLATFORM.value: TargetPriority.PLATFORM,
    TargetLevel.APP.value: TargetPriority.APP,
    TargetLevel.MODULE.value: TargetPriority.MODULE,
    TargetLevel.CLUSTER.value: TargetPriority.CLUSTER,
    TargetLevel.CUSTOM.value: TargetPriority.CUSTOM,
}

# 自定义分组前缀，监控要求PGK:开头，这里设置为PGK:DBM
PRIORITY_KEY_PREFIX = "PGK:DBM"


class PolicyStatus(StrStructuredEnum):
    """监控策略状态"""

    VALID = EnumField("valid", _("有效"))
    TARGET_INVALID = EnumField("target_invalid", _("监控目标已失效"))


class OperatorEnum(StrStructuredEnum):
    """比较操作符"""

    EQ = EnumField("eq", _("等于"))
    NEQ = EnumField("neq", _("不等于"))
    LT = EnumField("lt", _("小于"))
    GT = EnumField("gt", _("大于"))
    LTE = EnumField("lte", _("小于等于"))
    GTE = EnumField("gte", _("大于等于"))


class AlertLevelEnum(IntStructuredEnum):
    """告警级别"""

    HIGH = EnumField(1, _("致命"))
    MID = EnumField(2, _("预警"))
    LOW = EnumField(3, _("提醒"))


class AlertStageEnum(StrStructuredEnum):
    """告警处理阶段"""

    IS_HANDLED = EnumField("is_handled", _("已通知"))
    IS_ACK = EnumField("is_ack", _("已确认"))
    IS_SHIELDED = EnumField("is_shielded", _("已屏蔽"))
    IS_BLOCKED = EnumField("is_blocked", _("已流控"))


class AlertStatusEnum(StrStructuredEnum):
    """告警状态"""

    ABNORMAL = EnumField("ABNORMAL", _("未恢复"))
    RECOVERED = EnumField("RECOVERED", _("已恢复"))
    CLOSED = EnumField("CLOSED", _("已失效"))


class AlertSourceEnum(StrStructuredEnum):
    """告警数据来源"""

    TIME_SERIES = EnumField("time_series", _("时序数据"))
    EVENT = EnumField("event", _("事件数据"))
    LOG = EnumField("log", _("日志关键字"))


class DetectAlgEnum(StrStructuredEnum):
    """检测算法"""

    THRESHOLD = EnumField("Threshold", _("阈值检测"))


class NoticeWayEnum(StrStructuredEnum):
    """通知方式"""

    BY_RULE = EnumField("by_rule", _("基于分派规则通知"))
    ONLY_NOTICE = EnumField("only_notice", _("基于告警组直接通知"))


class DashboardType(StrStructuredEnum):
    """仪表盘类型"""

    CLUSTER = EnumField("cluster", _("集群仪表盘"))
    BUSINESS = EnumField("business", _("业务仪表盘"))
    OVERVIEW = EnumField("overview", _("业务概览仪表盘"))


# 非ui方式监控策略模板占位符
PROMQL_FILTER_TPL = "__COND__"

# 蓝鲸监控保存用户组模板
DEFAULT_ALERT_NOTICE = [
    {
        "time_range": "00:00:00--23:59:00",
        "notify_config": [
            {"notice_ways": [{"name": "rtx"}], "level": 3},
            {"notice_ways": [{"name": "rtx"}], "level": 2},
            {"notice_ways": [{"name": "rtx"}, {"name": "voice"}], "level": 1},
        ],
    }
]

BK_MONITOR_SAVE_USER_GROUP_TEMPLATE = {
    "name": "",
    "desc": "",
    "need_duty": False,
    "duty_arranges": [{"duty_type": "always", "work_time": "always", "users": []}],
    "alert_notice": DEFAULT_ALERT_NOTICE,
    "action_notice": [
        {
            "time_range": "00:00:00--23:59:00",
            "notify_config": [
                {"phase": 3, "notice_ways": [{"name": "mail"}]},
                {"phase": 2, "notice_ways": [{"name": "mail"}]},
                {"phase": 1, "notice_ways": [{"name": "mail"}]},
            ],
        }
    ],
    "channels": ["user"],
    "bk_biz_id": 0,
}

# 分派优先级定义
PLAT_PRIORITY = 100
APP_PRIORITY = 1000

BK_MONITOR_DISPATCH_RULE_MIXIN = {
    "actions": [
        {
            "action_type": "notice",
            "is_enabled": True,
            "upgrade_config": {"is_enabled": False, "user_groups": [], "upgrade_interval": 0},
        }
    ],
    "alert_severity": 0,
    "additional_tags": [],
    "is_enabled": True,
}

# 分派规则模板
BK_MONITOR_SAVE_DISPATCH_GROUP_TEMPLATE = {
    "id": 0,
    "bk_biz_id": 0,
    "priority": PLAT_PRIORITY,
    "name": _("平台级分派给业务"),
    "rules": [
        {
            "id": 2,
            "user_groups": [],
            "conditions": [
                {"field": "alert.strategy_id", "value": ["95"], "method": "eq", "condition": "and"},
                {"field": "appid", "value": ["1", "2", "3"], "method": "eq", "condition": "and"},
            ],
            **BK_MONITOR_DISPATCH_RULE_MIXIN,
        },
    ],
}

MONITOR_EVENTS = "monitor_events"


class MySQLAutofixStep(StrStructuredEnum):
    IN_PLACE_AUTOFIX = EnumField("IN_PLACE_AUTOFIX", _("原地自愈"))
    REPLACE_NEW = EnumField("REPLACE_NEW", _("新机替换"))


AUTOFIX_ACTION_NAME = "dbm_autofix_http_callback"

# 故障自愈模板
AUTOFIX_ACTION_TEMPLATE = {
    "execute_config": {
        "template_detail": {
            "method": "POST",
            "url": f"{env.BK_SAAS_CALLBACK_URL}/apis/monitor/policy/callback/",
            "headers": [],
            "authorize": {
                "auth_config": {"token": env.BKMONITOR_BEARER_TOKEN},
                "auth_type": "bearer_token",
                "insecure_skip_verify": True,
            },
            "body": {
                "data_type": "raw",
                "content_type": "json",
                "content": '{"callback_message": {{alarm.callback_message}},' '"appointees": "{{alarm.appointees}}"}',
                "params": [],
            },
            "query_params": [],
            "need_poll": False,
            "notify_interval": 60,
            "failed_retry": {"is_enabled": True, "max_retry_times": 2, "retry_interval": 2, "timeout": 10},
        },
        "timeout": 600,
    },
    "name": AUTOFIX_ACTION_NAME,
    "desc": "",
    "is_enabled": True,
    # plugin_id = 2 代表 http 回调
    "plugin_id": 2,
    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
}


class MonitorEventType(StrStructuredEnum):
    """
    自定义上报事件名称
    声明后不要轻易修改，如果要修改记得修改对应的监控策略
    """

    MYSQL_DBHA_AUTOFIX_TICKET_FAILED = EnumField("mysql-dbha-autofix-ticket-failed", _("MySQL DBHA自愈单据失败"))
    MYSQL_BACKUP_FAILED = EnumField("mysql-backup-failed", _("MySQL 备份失败"))
    MYSQL_BACKUP_INSPECT_FAILED = EnumField("mysql-backup-inspect-failed", _("MySQL 备份巡检结果异常"))
    DRS_REQUEST_FAILED = EnumField("drs-request-failed", _("drs 请求异常"))
    MYSQL_DBHA_AUTOFIX_VALIDATE_FAILED = EnumField("mysql-dbha-autofix-validate-failed", _("MySQL DBHA 事件校验失败"))


UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    # 单位：s
    "start_time": 1697100405,
    "end_time": 1697101305,
    "slimit": 500,
    "down_sample_range": "1s",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "instant",
}

EXPORTER_UP_QUERY_TEMPLATE = {
    DBType.Redis: {
        "range": 5,
        "dbm_redis_exporter": """count by (cluster_domain) (
            bkmonitor:exporter_dbm_redis_exporter:redis_up{instance_role='redis_master'}
        )""",
    },
    ClusterType.TenDBHA: {
        "range": 5,
        "dbm_mysqld_exporter": """count by (appid,cluster_domain,instance,instance_role) (
            bkmonitor:exporter_dbm_mysqld_exporter:mysql_up{cluster_type='tendbha'}
        )""",
        "dbm_mysqlproxy_exporter": """count by (appid,cluster_domain,instance,instance_role) (
            bkmonitor:exporter_dbm_mysqlproxy_exporter:mysqlproxy_up{cluster_type='tendbha'}
        )""",
    },
    ClusterType.TenDBCluster: {
        "range": 5,
        "dbm_mysqld_exporter": """count by (appid,cluster_domain,instance,instance_role) (
            bkmonitor:exporter_dbm_mysqld_exporter:mysql_up{cluster_type='tendbcluster'}
        )""",
    },
    ClusterType.TenDBSingle: {
        "range": 5,
        "dbm_mysqld_exporter": """count by (appid,cluster_domain,instance,instance_role) (
            bkmonitor:exporter_dbm_mysqld_exporter:mysql_up{cluster_type='tendbsingle'}
        )""",
    },
}

QUERY_TEMPLATE = {
    ClusterType.TendisTwemproxyRedisInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            bkmonitor:exporter_dbm_redis_exporter:redis_memory_used_bytes{instance_role="redis_master",%s}
           )""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, bk_target_ip) (
                    bkmonitor:dbm_system:mem:total{instance_role="redis_master",%s}
            ))""",
    },
    ClusterType.TwemproxyTendisSSDInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
        bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_used_mb{instance_role="redis_master",%s} * 1024 * 1024
        ))""",
        "total": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
        bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_total_mb{instance_role="redis_master",%s} * 1024 *
        1024))""",
    },
    ClusterType.TenDBSingle: {
        "range": 129,
        "used": """max by (cluster_domain, instance, mount_point) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024
            )""",
        "total": """max by (cluster_domain, instance, mount_point) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024
            )""",
    },
    ClusterType.TenDBHA: {
        "range": 129,
        "used": """max by (cluster_domain, instance, mount_point) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="backend_master",%s}[124m]
                ) * 1024 * 1024
            )""",
        "total": """max by (cluster_domain, instance, mount_point) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="backend_master",%s}[124m]
                ) * 1024 * 1024
            )""",
    },
    ClusterType.TenDBCluster: {
        "range": 129,
        "used": """sum by (cluster_domain) (
            avg by (cluster_domain, instance, mount_point) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_du_used_mb{instance_role="remote_master",%s}[124m]
                ) * 1024 * 1024))""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, ip, mount_point) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="remote_master",%s}[124m]
                ) * 1024 * 1024))""",
    },
    ClusterType.SqlserverSingle: {
        "range": 120,
        "used": """sum by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_used{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 * 1024 )""",
        "total": """max by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_total{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 * 1024 )""",
    },
    ClusterType.SqlserverHA: {
        "range": 120,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_used{instance_role="backend_master",%s}[5m]
                ) * 1024 * 1024 * 1024
            ))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_total{instance_role="backend_master",%s}[5m]
                ) * 1024 * 1024 * 1024
            ))""",
    },
    # es采集器本身存在容量统计指标（elasticsearch_filesystem_data_size_bytes、elasticsearch_indices_store_size_bytes）
    # 但数据节点只注册了一个，这里暂时用磁盘容量计算
    ClusterType.Es: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain,bk_target_ip)(
                sum by (cluster_domain,bk_target_ip, instance_port)(bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",
                    instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                    mount_point!~"^(/|/usr/local)$",%s
                    }
                )))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain,bk_target_ip)(
                sum by (cluster_domain,bk_target_ip, instance_port)(bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                    mount_point!~"^(/|/usr/local)$",%s
                }
            )))""",
    },
    ClusterType.Kafka: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",instance_role="broker",mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
        "total": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="broker",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
    },
    ClusterType.Pulsar: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
        "total": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
    },
    ClusterType.Hdfs: {
        "range": 5,
        "used": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_used{%s}[5m]))""",
        "total": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_total{%s}[5m]))""",
    },
    ClusterType.Influxdb: {
        "range": 5,
        "used": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_used{path=~"^/data|/data1$",%s}[5m]))""",
        "total": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_total{path=~"^/data|/data1$",%s}[5m]))""",
    },
    ClusterType.Dbmon: {
        "range": 5,
        "heartbeat": """
        avg by (target,bk_biz_id,app,bk_cloud_id, cluster_domain, cluster_type, instance_role)
        (avg_over_time(custom:dbm_report_channel:redis_dbmon_heart_beat{
            {cluster_domain="{cluster_domain}",%s}
        }[1m]))""",
    },
    ClusterType.Doris: {
        "range": 5,
        "used": """sum by (cluster_domain)(
            bkmonitor:pushgateway_dbm_doris_bkpull:doris_be_disks_local_used_capacity{%s})""",
        "total": """sum by (cluster_domain) (
            bkmonitor:pushgateway_dbm_doris_bkpull:doris_be_disks_total_capacity{%s})""",
    },
}

# 使用相同容量查询模板的集群类型映射
SAME_QUERY_TEMPLATE_CLUSTER_TYPE_MAP = {
    # Redis 内存型
    ClusterType.TendisPredixyRedisCluster.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.RedisInstance.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisCluster.value: ClusterType.TendisTwemproxyRedisInstance.value,
    # Redis 磁盘型
    ClusterType.TendisPredixyTendisplusCluster.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTwemproxyTendisplusIns.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisSSDInstance.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisplusInsance.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisplusCluster.value: ClusterType.TwemproxyTendisSSDInstance.value,
}

# Redis组件负载表达式模板
REDIS_LOAD_QUERY_TEMPLATE = {
    # predixy 主机cpu
    "predixy_host_cpu": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:cpu_summary:usage{"
    'cluster_domain=~"{cluster_domains}",instance_role="proxy"}[1m]))',
    # twemproxy实例cpu
    "twemproxy_instance_cpu": "sum by(cluster_domain,instance_host) (irate("
    'bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_process_cpu{cluster_domain=~"{'
    'cluster_domains}"}[1m]))/100',
    # 主机cpu使用率
    "redis_host_cpu": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:cpu_summary:usage{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # 主机磁盘使用率
    "redis_host_disk": "max by (cluster_domain,bk_target_cloud_id) ("
    'bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_usage{cluster_domain="{'
    'cluster_domain}",instance_role="redis_master"})',
    # "主机io"
    "redis_host_io": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:io:util{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # redis主机内存使用率
    "redis_host_mem": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:mem:pct_used{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # redis proxy主机内存使用率
    "proxy_host_mem": 'max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="{'
    'cluster_domain}",instance_role="proxy"}[1m]))',
    # redis连接数
    "redis_connections": "sum by (cluster_domain,instance) ("
    'bkmonitor:exporter_dbm_redis_exporter:redis_connected_clients{cluster_domain="{'
    'cluster_domain}",instance_role="redis_master"})',
    # predixy连接数
    "predixy_connections": "sum by (cluster_domain,instance_host) (bkmonitor:exporter_dbm_predixy_exporter"
    ':predixy_cluster_connections{cluster_domain=~"{cluster_domains}"})',
    # twemproxy连接数
    "twemproxy_connections": "sum by (cluster_domain,instance_host) (bkmonitor:exporter_dbm_twemproxy_exporter"
    ':twemproxy_connections_curr{cluster_domain=~"{cluster_domains}"})',
}

# 集群机器负载查询组合字典
CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE = {
    MachineType.REDIS: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_connections"], "max": 20000, "min": 2000},
    },
    MachineType.TWEMPROXY: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["twemproxy_instance_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["proxy_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["twemproxy_connections"], "max": 20000, "min": 2000},
    },
    MachineType.PREDIXY: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["predixy_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["proxy_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["predixy_connections"], "max": 20000, "min": 2000},
    },
    MachineType.TENDISSSD: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 70, "min": 20},
        "disk": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_disk"], "max": 20000, "min": 2000},
        "io": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_io"], "max": 20000, "min": 2000},
    },
    MachineType.TENDISPLUS: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 85, "min": 20},
        "disk": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_disk"], "max": 20000, "min": 2000},
        "io": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_io"], "max": 20000, "min": 2000},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_connections"], "max": 20000, "min": 2000},
    },
}

CLUSTER_TYPE_LOAD_RULES = {
    ClusterType.RedisInstance: [MachineType.REDIS],
    ClusterType.TendisTwemproxyRedisInstance: [MachineType.REDIS, MachineType.TWEMPROXY],
    ClusterType.TendisPredixyRedisCluster: [MachineType.REDIS, MachineType.PREDIXY],
    ClusterType.TendisPredixyTendisplusCluster: [MachineType.TENDISPLUS, MachineType.PREDIXY],
    ClusterType.TwemproxyTendisSSDInstance: [MachineType.TENDISSSD, MachineType.TWEMPROXY],
}

# ES巡检相关表达式
ES_DAILY_CHECK_TEMPLATE = {
    "cluster_status": {
        "range": 5,
        "template": """
        max by (cluster_domain) (bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_cluster_health_status{%s})
        """,
    }
}


class RedisLoadStatus(StrStructuredEnum):
    LOW = EnumField("low", _("低负载"))
    HIGH = EnumField("high", _("高负载"))


class TimeUnit:
    SECOND = 1
    MINUTE = SECOND * 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24


# 告警屏蔽类型
class MonitorShieldType(StrStructuredEnum):
    DIMENSION = EnumField("dimension", _("基于维度屏蔽"))
    STRATEGY = EnumField("strategy", _("基于策略屏蔽"))
