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

from blue_krill.data_types.enum import EnumField, StructuredEnum


class DorisConfigEnum(str, StructuredEnum):
    FrontendHttpPort = EnumField("fe.http_port", _("fe http端口"))
    FrontendQueryPort = EnumField("fe.query_port", _("fe query 端口"))
    Frontend = EnumField("fe", _("fe"))
    Backend = EnumField("be", _("be"))
    UserName = EnumField("username", _("访问Doris 管理员账户名"))
    Password = EnumField("password", _("访问Doris 管理员密码"))


class DorisMetaOperation(str, StructuredEnum):
    Add = EnumField("ADD", _("ADD"))
    Drop = EnumField("DROP", _("DROP"))
    Decommission = EnumField("DECOMMISSION", _("DECOMMISSION"))
    ForceDrop = EnumField("DROPP", _("DROPP"))


class DorisNodeOperation(str, StructuredEnum):
    Start = EnumField("start", _("start"))
    Stop = EnumField("stop", _("stop"))
    Restart = EnumField("restart", _("restart"))


DORIS_ROLE_ALL = "all"
DORIS_FOLLOWER_MUST_COUNT = 3
DORIS_OBSERVER_NOT_COUNT = 1
DORIS_BACKEND_NOT_COUNT = 0
