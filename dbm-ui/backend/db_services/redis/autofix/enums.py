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


class DBHASwitchResult(str, StructuredEnum):
    """切换结果类型枚举"""

    INFO = EnumField("info", _("切换中？"))
    FAIL = EnumField("failed", _("切换失败"))
    SUCC = EnumField("success", _("切换成功"))


class AutofixItem(str, StructuredEnum):
    """切换控制"""

    AUTOFIX_ENABLE = EnumField("enable", _("自愈开关"))
    DBHA_ID = EnumField("last_id", _("监控到的id"))
    QYWX_WEBHOOK = EnumField("qywx_webhook", _("企业微信机器人webhook"))
    QYWX_TOKEN = EnumField("qywx_token", _("企业微信机器人Token"))
    IGNORE_APPS = EnumField("ignore_apps", _("忽略自愈的APP列表"))
    IGNORE_DOMAINS = EnumField("ignore_domains", _("忽略自愈的集群列表"))


class AutofixStatus(str, StructuredEnum):
    """自愈状态"""

    AF_INIT = EnumField("initautofix", _("初始化"))
    AF_TICKET = EnumField("initticket", _("创建单据"))
    AF_SFLOW = EnumField("startflow", _("发起flow流程"))
    AF_WFLOW = EnumField("watchflow", _("监控流程完成状态"))
    AF_INST_JOB = EnumField("waitshutdown", _("等待实例下架"))
    AF_SUCC = EnumField("success", _("自愈成功"))
    AF_FAIL = EnumField("fail", _("自愈失败"))
