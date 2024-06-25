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


class DorisFlowBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.FLOW_CODE
    MESSAGE = _("Flow模块Doris异常")


class NormalDorisFlowException(DorisFlowBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("通用异常")
    MESSAGE_TPL = _("{message}")


class RoleMachineCountException(DorisFlowBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("机器数量异常")
    MESSAGE_TPL = _("Doris集群角色{doris_role}数量不能为{machine_count}")


class RoleMachineCountMustException(DorisFlowBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("机器数量异常")
    MESSAGE_TPL = _("Doris集群角色{doris_role}机器数量必须为{must_count}")


class BeMachineCountException(DorisFlowBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("机器数量异常")
    MESSAGE_TPL = _("Doris集群数据节点(热+冷)机器数量之和不能为{must_count}")


class FollowerScaleUpUnsupportedException(DorisFlowBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("机器数量异常")
    MESSAGE_TPL = _("Doris集群Follower不支持扩容, 当前选择扩容机器数量为{machine_count}")


class ReplaceMachineCountException(DorisFlowBaseException):
    ERROR_CODE = "006"
    MESSAGE = _("Doris替换机器数量不一致")
    MESSAGE_TPL = _("Doris集群替换角色{doris_role}数量不一致,已选旧节点个数{old_count},新节点个数{new_count}")
