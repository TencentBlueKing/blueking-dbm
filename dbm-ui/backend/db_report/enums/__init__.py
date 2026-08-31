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

from .ai_analysis_sub_type import AiAnalysisSubType
from .dbmon_heartbeat_report_sub_type import DbmonHeartbeatReportSubType
from .kafka_affinity_check_sub_type import KafkaAffinityCheckSubType
from .meta_check_sub_type import MetaCheckSubType
from .mysqlbackup_check_sub_type import MysqlBackupCheckSubType
from .redis_rollback_exercise_task_stage import FAILED_STAGES as REDIS_ROLLBACK_EXER_FAILED_STAGES
from .redis_rollback_exercise_task_stage import RedisRollbackExerciseTaskStage
from .redisbackup_check_sub_type import RedisBackupCheckSubType
from .tdbctl_upgrade_status import TdbctlInstanceRole, TdbctlUpgradeStatus

SWAGGER_TAG = _("巡检报告")

REPORT_COUNT_CACHE_KEY = "{user}_report_count_key"


class ReportKind(StrStructuredEnum):
    """报告种类"""

    INSPECT = EnumField("inspect", _("巡检报告"))
    DRILL = EnumField("drill", _("演练报告"))


class ReportFieldFormat(StrStructuredEnum):
    TEXT = EnumField("text", _("文本渲染"))
    STATUS = EnumField("status", _("状态渲染"))
    LINK = EnumField("link", _("链接渲染"))
    TIME = EnumField("time", _("时间渲染"))
    LOG = EnumField("log", _("日志渲染"))
    # 数据校验失败详情字段
    FAIL_SLAVE_INSTANCE = EnumField("fail_slave_instance", _("数据校验失败详情渲染"))


class ReportType(StrStructuredEnum):
    """巡检报告类型，定义的顺序决定在页面展示的顺序"""

    META_CHECK = EnumField("meta_check", _("元数据检查"))
    FULL_BACKUP_CHECK = EnumField("full_backup_check", _("全备检查"))
    BINLOG_BACKUP_CHECK = EnumField("binlog_backup_check", _("binlog检查"))
    CHECKSUM = EnumField("checksum", _("数据校验检查"))

    ALONE_INSTANCE_CHECK = EnumField("alone_instance_check", _("孤立实例检查"))
    STATUS_ABNORMAL_CHECK = EnumField("status_abnormal_check", _("实例异常状态检查"))
    AFFINITY_CHECK = EnumField("affinity_check", _("亲和性检查"))
    CONF_CHECK = EnumField("conf_check", _("配置检查"))
    ENTRY_CHECK = EnumField("entry_check", _("访问入口一致性检查"))
    REDIS_DBMON_HEARTBEAT_CHECK = EnumField("dbmon_heartbeat_check", _("dbmon心跳超时检查"))

    EXPORTER_CHECK = EnumField("exporter_check", _("exporter监控上报检查"))
    AGENT_UNIVERSAL_CHECK = EnumField("agent_universal_check", _("Agent通用检查"))

    # SQLSERVER
    SQLSERVER_APP_SETTING_CHECK = EnumField("sqlserver_app_setting_check", _("AppSetting表数据巡检检查"))
    SQLSERVER_SYS_JOB_CHECK = EnumField("sqlserver_sys_job_check", _("系统作业的状态巡检"))
    SQLSERVER_JOB_SYNC_CHECK = EnumField("sqlserver_job_sync_check", _("业务Job的同步巡检"))
    SQLSERVER_LINK_SERVER_SYNC_CHECK = EnumField("sqlserver_link_server_sync_check", _("业务Linkserver的同步巡检"))
    SQLSERVER_USER_SYNC_CHECK = EnumField("sqlserver_user_sync_check", _("业务账号同步巡检"))
    SQLSERVER_FULL_BACKUP_CHECK_BY_MODEL = EnumField("sqlserver_full_backup_check_by_model", _("全量备份文件异常报告"))
    SQLSERVER_LOG_BACKUP_CHECK_BY_MODEL = EnumField("sqlserver_log_backup_check_by_model", _("增量备份文件异常报告"))

    FAIL_OVER_DRILL = EnumField("fail_over_drill", _("切换演练任务报告"))
    BACKUP_RECOVER_DRILL = EnumField("backup_recover_drill", _("回档演练任务报告"))

    # ES
    ES_STATUS_CHECK = EnumField("es_status_check", _("ES集群状态巡检"))
    ES_VERSION_CHECK = EnumField("es_version_check", _("ES集群版本巡检"))
    ES_DATANODE_CHECK = EnumField("es_datanode_check", _("ES集群数据节点亲合度巡检"))
    ES_MASTER_CHECK = EnumField("es_master_check", _("ES集群master节点巡检"))
    ES_DOMAIN_CHECK = EnumField("es_domain_check", _("ES集群域名巡检"))
    ES_ACCOUNT_CHECK = EnumField("es_account_check", _("ES集群账户巡检"))

    # Kafka
    KAFKA_ZOOKEEPER_AFFINITY_CHECK = EnumField("kafka_zookeeper_affinity_check", _("Kafka Zookeeper亲和性巡检"))
    KAFKA_BROKER_AFFINITY_CHECK = EnumField("kafka_broker_affinity_check", _("Kafka Broker亲和性巡检"))


class ReportStateType(StrStructuredEnum):
    NORMAL = EnumField("normal", _("正常"))
    WARNING = EnumField("warning", _("预警"))
    ABNORMAL = EnumField("abnormal", _("异常"))


class DrillFilterType(StrStructuredEnum):
    TIME = EnumField("time", _("时间"))
    TEXT = EnumField("text", _("文本"))
    ENUM = EnumField("enum", _("枚举"))
    BIZ = EnumField("biz", _("业务"))
