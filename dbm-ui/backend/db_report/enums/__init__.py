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
from django.utils.translation import ugettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

from .dbmon_heartbeat_report_sub_type import DbmonHeartbeatReportSubType
from .meta_check_sub_type import MetaCheckSubType
from .mysqlbackup_check_sub_type import MysqlBackupCheckSubType
from .redisbackup_check_sub_type import RedisBackupCheckSubType

SWAGGER_TAG = _("巡检报告")

REPORT_COUNT_CACHE_KEY = "{user}_report_count_key"


class ReportFieldFormat(str, StructuredEnum):
    TEXT = EnumField("text", _("文本渲染"))
    STATUS = EnumField("status", _("状态渲染"))
    # 数据校验失败详情字段
    FAIL_SLAVE_INSTANCE = EnumField("fail_slave_instance", _("数据校验失败详情渲染"))


class ReportType(str, StructuredEnum):
    """巡检报告类型，定义的顺序决定在页面展示的顺序"""

    META_CHECK = EnumField("meta_check", _("元数据检查"))
    FULL_BACKUP_CHECK = EnumField("full_backup_check", _("全备检查"))
    BINLOG_BACKUP_CHECK = EnumField("binlog_backup_check", _("binlog检查"))
    CHECKSUM = EnumField("checksum", _("数据校验检查"))

    ALONE_INSTANCE_CHECK = EnumField("alone_instance_check", _("孤立实例检查"))
    STATUS_ABNORMAL_CHECK = EnumField("status_abnormal_check", _("实例异常状态检查"))
    REDIS_DBMON_HEARTBEAT_CHECK = EnumField("dbmon_heartbeat_check", _("dbmon心跳超时检查"))
