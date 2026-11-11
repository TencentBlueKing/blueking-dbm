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

DOMAIN_SUFFIX = ".db"
DOMAIN_MAX_LENGTH = 253
DOMAIN_LABEL_MAX_LENGTH = 63
REMARK_MAX_LENGTH = 500
AUDIT_SCOPE_DOMAIN = "domain"
AUDIT_SCOPE_GLOBAL = "global"


class MaintainType(StrStructuredEnum):
    SELF = EnumField("self", _("自主维护"))
    CLUSTER = EnumField("cluster", _("集群托管"))


class AuditAction(StrStructuredEnum):
    CREATE = EnumField("create", _("创建域名"))
    UPDATE_IP = EnumField("update_ip", _("修改 IP"))
    UPDATE_REMARK = EnumField("update_remark", _("修改备注"))
    UPDATE_OWNER = EnumField("update_owner", _("修改负责人"))
    DELETE = EnumField("delete", _("删除域名"))
