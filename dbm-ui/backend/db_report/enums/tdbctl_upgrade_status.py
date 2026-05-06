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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class TdbctlUpgradeStatus(StrStructuredEnum):
    """tdbctl 升级状态枚举"""

    PENDING = EnumField("pending", _("待升级"))
    RUNNING = EnumField("running", _("升级中"))
    SUCCESS = EnumField("success", _("升级成功"))
    FAILED = EnumField("failed", _("升级失败"))
    SKIPPED = EnumField("skipped", _("已跳过-版本已是最新"))


class TdbctlInstanceRole(StrStructuredEnum):
    """tdbctl 实例角色枚举"""

    PRIMARY = EnumField("primary", _("主节点"))
    SECONDARY = EnumField("secondary", _("从节点"))
