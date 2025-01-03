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

from backend.exceptions import AppBaseException, ErrorCode


class TicketBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.TICKET_CODE
    MESSAGE = _("单据模块异常")


class ItsmTicketNotExistException(TicketBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("ITSM单据不存在")
    MESSAGE_TPL = _("ITSM单据[{sn}]不存在")


class TicketTypeNotSupportedException(TicketBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("单据类型不支持")
    MESSAGE_TPL = _("单据类型不支持{ticket_type}")


class TicketParamsVerifyException(TicketBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("单据参数校验异常")
    MESSAGE_TPL = _("单据{ticket_type}参数校验异常")


class TicketInnerFlowExclusiveException(TicketBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("单据执行互斥")
    MESSAGE_TPL = _("单据{ticket_type}执行互斥")


class TicketDuplicationException(TicketBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("单据提交重复")
    MESSAGE_TPL = _("单据{ticket_type}提交重复")


class TicketTaskTriggerException(TicketBaseException):
    ERROR_CODE = "006"
    MESSAGE = _("单据任务定时触发异常")
    MESSAGE_TPL = _("单据任务{ticket_type}定时触发异常")


class TodoWrongOperatorException(TicketBaseException):
    ERROR_CODE = "007"
    MESSAGE = _("错误的todo处理人")
    MESSAGE_TPL = _("错误的todo处理人{username}")


class TodoDuplicateProcessException(TicketBaseException):
    ERROR_CODE = "010"
    MESSAGE = _("重复操作")
    MESSAGE_TPL = _("重复操作")


class ApprovalWrongOperatorException(TicketBaseException):
    ERROR_CODE = "008"
    MESSAGE = _("审批处理异常")
    MESSAGE_TPL = _("审批处理异常{username}")


class TicketFlowsConfigException(TicketBaseException):
    ERROR_CODE = "009"
    MESSAGE = _("单据流程设置失败")
    MESSAGE_TPL = _("单据流程{ticket_type}设置失败")
