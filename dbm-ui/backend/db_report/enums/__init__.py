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


class ReportFieldFormat(str, StructuredEnum):
    TEXT = EnumField("text", _("文本渲染"))
    STATUS = EnumField("status", _("状态渲染"))
    # 数据校验失败详情字段
    FAIL_SLAVE_INSTANCE = EnumField("fail_slave_instance", _("数据校验失败详情渲染"))
