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

from backend.exceptions import AppBaseException, ErrorCode


class DBMMcpBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.MCP_CODE
    MESSAGE = _("mcp tools 异常")
    MESSAGE_TPL = "{msg}"


class DBMMcpDuplicateToolNameException(DBMMcpBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("mcp tools 重名")
    MESSAGE_TPL = _("{tool_name} 重名")


class DBMMcpNotSupportClusterTypeException(DBMMcpBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("不支持的集群类型")
    MESSAGE_TPL = _("{cluster_type} 不支持当前操作")


class DBMMcpNotSupportMachineTypeException(DBMMcpBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("不支持的机器类型")
    MESSAGE_TPL = _("{machine_type} 不支持当前操作")


class DBMMcpUsernameNotFoundException(DBMMcpBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("username 未找到")


class DBMMcpMySQLApplyPrivAccountNotFoundException(DBMMcpBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("账号规则未找到")
    MESSAGE_TPL = _("{msg}")


class DBMMcpMySQLApplyPrivDBRuleNotFoundException(DBMMcpBaseException):
    ERROR_CODE = "006"
    MESSAGE = _("DB 规则未找到")
    MESSAGE_TPL = _("{msg}")


class DBMMcpNoneBillSubmittedException(DBMMcpBaseException):
    ERROR_CODE = "007"
    MESSAGE = _("单据未提交")
    MESSAGE_TPL = _("{msg}")


class DBMMcpClusterNotFoundException(DBMMcpBaseException):
    ERROR_CODE = ("008",)
    MESSAGE = _("集群未找到")
    MESSAGE_TPL = _("{msg}")


class DBMMcpNotBusinessDBAPrimaryException(DBMMcpBaseException):
    ERROR_CODE = "009"
    MESSAGE = _("用户不是业务 DBA 主负责人")
    MESSAGE_TPL = _("用户 {username} 不是业务 {bk_biz_id} 的 {db_type} DBA 主负责人")


class DBMMcpBadTicketStatusException(DBMMcpBaseException):
    ERROR_CODE = "010"
    MESSAGE = _("单据类型不支持当前操作")
    MESSAGE_TPL = _("{msg}")
