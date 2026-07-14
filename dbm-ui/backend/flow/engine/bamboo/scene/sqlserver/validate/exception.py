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

from backend.flow.engine.validate.exceptions import FlowValidateBaseException


class DBNotInBackupListException(FlowValidateBaseException):
    ERROR_CODE = "37001"
    MESSAGE = _("待构造的DB不在备份记录范围内")
    MESSAGE_TPL = _("待构造的DB不在备份记录范围内：{message}")


class LogBackupNotContinuousException(FlowValidateBaseException):
    ERROR_CODE = "37002"
    MESSAGE = _("日志备份存在缺失或不连续")
    MESSAGE_TPL = _("日志备份存在缺失或不连续： {message}")


class DuplicateDStClusterException(FlowValidateBaseException):
    ERROR_CODE = "37003"
    MESSAGE = _("定点构造中，目标集群存在重复")
    MESSAGE_TPL = _("定点构造中，目标集群存在重复: {message}")


class DuplicateSRCClusterException(FlowValidateBaseException):
    ERROR_CODE = "37004"
    MESSAGE = _("原地回档中，集群存在重复")
    MESSAGE_TPL = _("原地回档中，集群存在重复: {message}")
