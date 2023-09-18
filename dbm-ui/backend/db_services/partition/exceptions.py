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

from backend.exceptions import AppBaseException, ErrorCode


class DBPartitionCreateException(AppBaseException):
    MODULE_CODE = ErrorCode.DB_PARTITION_CODE
    MESSAGE = _("分区管理创建异常")


class DBPartitionInternalServerError(AppBaseException):
    MODULE_CODE = 10001
    MESSAGE = _("服务器内部错误")


class DBPartitionInvalidFieldException(AppBaseException):
    MODULE_CODE = 10002
    MESSAGE = _("不合法的分区字段")


class DBPartitionConfigNotExistedException(AppBaseException):
    MODULE_CODE = 52022
    MESSAGE = _("分区配置不存在")


class DBPartitionNotSupportedClusterTypeException(AppBaseException):
    MODULE_CODE = 52024
    MESSAGE = _("分区不支持该集群类型")


class DBPartitionNothingToDoException(AppBaseException):
    MODULE_CODE = 52029
    MESSAGE = _("没有需要执行的操作")


class DBPartitionWrongPartitionNameFormatException(AppBaseException):
    MODULE_CODE = 52029
    MESSAGE = _("分区名格式错误")
