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


class DorisResOpType(str, StructuredEnum):
    """
    定义执行Doris资源的操作类型
    """

    CREATE_AND_BIND = EnumField("create_bind", _("创建资源及绑定集群"))
    BIND_ONLY = EnumField("bind_only", _("仅绑定集群资源"))
    UNTIE_AND_DELETE = EnumField("untie_delete", _("解绑及删除资源"))
    UNTIE_ONLY = EnumField("untie_only", _("仅解绑集群资源"))


class DorisResourceTag(str, StructuredEnum):
    """
    定义Doris 资源标记
    """

    PUBLIC = EnumField("public", _("公共资源"))
    PRIVATE = EnumField("private", _("独立集群资源"))


class DorisResourceGrant(str, StructuredEnum):
    """
    定义Doris 资源是否受DBM管控
    """

    DBM = EnumField("dbm", _("由DBM创建及删除"))
    OTHERS = EnumField("others", _("其他"))


DORIS_ROLE_ALL = "all"
DORIS_FOLLOWER_MUST_COUNT = 3
DORIS_OBSERVER_NOT_COUNT = 1
DORIS_BACKEND_NOT_COUNT = 0

DEFAULT_BE_WEB_PORT = 8040
DEFAULT_FE_WEB_PORT = 8030

# Doris资源名称最大长度，由Doris集群限制
DORIS_RES_NAME_MAX_LENGTH = 64
# Doris使用COS存储桶名称最大长度，由腾讯云COS限制
DORIS_BUCKET_NAME_MAX_LENGTH = 30
# DORIS资源名称模板
DORIS_RES_NAME_TMPL = "dbm-{bk_biz_id}-{cluster_name}"
