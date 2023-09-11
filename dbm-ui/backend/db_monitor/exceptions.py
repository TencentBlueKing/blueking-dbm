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

from backend.exceptions import AppBaseException


class DBMonitorBaseException(AppBaseException):
    MODULE_CODE = "50"


class BkMonitorSaveAlarmException(DBMonitorBaseException):
    ERROR_CODE = "201"
    MESSAGE = _("监控策略保存失败")
    MESSAGE_TPL = _("监控策略保存失败: {message}")


class BkMonitorDeleteAlarmException(DBMonitorBaseException):
    ERROR_CODE = "202"
    MESSAGE = _("监控策略删除失败")
    MESSAGE_TPL = _("监控策略删除失败: {message}")
