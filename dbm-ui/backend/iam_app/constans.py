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

MAX_ACTION_NAME_LEN = 32

# IAM V4 的资源拓扑只能声明一条静态祖先链，平台级(无业务)资源统一挂在该虚拟业务下占位
GLOBAL_BIZ_ID_V4 = 0

# 已废弃的动作分组，该分组下的动作不注册到V4
DEPRECATED_ACTION_GROUP = _("已废弃")


class CommonActionLabel(StrStructuredEnum):
    BIZ_READ_ONLY = EnumField("biz_read_only", _("业务只读"))
    BIZ_MAINTAIN = EnumField("biz_maintain", _("业务运维"))
    DEVELOPER = EnumField("developer", _("开发常用"))
    EXTERNAL_DEVELOPER = EnumField("external_developer", _("外部开发商专用"))

    MYSQL_IMPORT_SQLFILE = EnumField("mysql_import_sqlfile", _("MySQL SQL变更"))
    MYSQL_AUTHORIZE_RULES = EnumField("mysql_authorize_rules", _("MySQL DB授权"))

    TENDBCLUSTER_IMPORT_SQLFILE = EnumField("tendbcluster_import_sqlfile", _("TendbCluster SQL变更"))
    TENDBCLUSTER_AUTHORIZE_RULES = EnumField("tendbcluster_authorize_rules", _("TendbCluster DB授权"))


class RoleActionLabel(StrStructuredEnum):
    """
    IAM V4 的角色标签，打在动作上圈定角色包含哪些动作。
    与常用操作同值的标签直接复用动作已有的 common_labels 声明，其余的打在 role_labels_v4 上
    """

    BIZ_READ_ONLY = EnumField("biz_read_only", _("业务只读"))
    RESOURCE_MANAGE = EnumField("resource_manage", _("资源管理员"))

    # 创建者角色，资源创建后授予创建者，由 ResourceMeta.creator_role_v4 指向
    MYSQL_CREATOR = EnumField("mysql_creator", _("MySQL集群创建者"))
