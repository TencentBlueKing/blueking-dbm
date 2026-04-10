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

from django.utils.translation import gettext as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class AppManagedStatus(StrStructuredEnum):
    """业务纳管状态"""

    MANAGED = EnumField("managed", _("已纳管"))
    UNMANAGED = EnumField("unmanaged", _("未纳管"))


class AppOperateType(StrStructuredEnum):
    DBA_CHANGE = EnumField("dba_change", _("人员变更"))
    MANAGED = EnumField("managed", _("纳管"))
    CANCEL_MANAGED = EnumField("cancel_managed", _("取消纳管"))
    TAG_CHANGE = EnumField("tag_change", _("标签变更"))
    DEFAULT_DBA_CHANGE = EnumField("default_dba_change", _("默认dba变更"))
