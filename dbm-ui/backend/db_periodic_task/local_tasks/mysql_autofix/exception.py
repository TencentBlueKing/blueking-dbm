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

from backend.exceptions import AppBaseException, ErrorCode


class MySQLAutofixException(AppBaseException):
    MODULE_CODE = ErrorCode.MYSQL_AUTOFIX_CODE
    MESSAGE = _("MySQL 自愈异常")


class MySQLDBHAAutofixUnsupportedMachineType(MySQLAutofixException):
    ERROR_CODE = "000"
    MESSAGE_TPL = _("check_id: {}, ip: {}, machine_type: {machine_type} 未支持")


class MySQLDBHAAutofixBadTodoRecord(MySQLAutofixException):
    ERROR_CODE = "001"
    MESSAGE_TPL = _("check_id: {check_id} 上报记录异常")


class MySQLDBHAAutofixMissingRecord(MySQLAutofixException):
    ERROR_CODE = "002"


class MySQLDBHAAutofixWaitTimeout(MySQLAutofixException):
    ERROR_CODE = "003"
    MESSAGE_TPL = _("check_id: {check_id} 等待超时")


class MySQLDBHAAutofixBadInstanceStatus(MySQLAutofixException):
    ERROR_CODE = "004"
    MESSAGE_TPL = _("{machine_type} {ip} 实例状态不全是 UNAVAILABLE 和 online")


class MySQLDBHAAutofixSpiderMultiClusters(MySQLAutofixException):
    ERROR_CODE = "005"
    MESSAGE_TPL = _("check_id: {check_id} {ip} 属于多个集群 {cluster_ids}")


class MySQLDBHAAutofixRemoteMultiClusters(MySQLAutofixException):
    ERROR_CODE = "006"
    MESSAGE_TPL = _("check_id: {check_id} {ip} 属于多个集群 {cluster_ids}")
