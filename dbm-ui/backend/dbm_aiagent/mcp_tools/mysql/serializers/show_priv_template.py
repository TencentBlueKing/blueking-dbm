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
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_cluster_type_choices


class ShowBizMySQLPrivilegeTemplateInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))


class MySQLDBPrivilegeDetail(serializers.Serializer):
    dbname = serializers.CharField(help_text=_("DB 名, 允许包含 %, ?, * 通配符"))
    privileges = serializers.ListField(child=serializers.ListField(), help_text=_("MySQL 权限明细"))


class MySQLPrivilegeTemplateSerializer(serializers.Serializer):
    account_name = serializers.CharField(help_text=_("账户名"))
    db_privileges = serializers.ListField(child=MySQLDBPrivilegeDetail(), help_text=_("db 授权模版"))


class ShowBizMySQLPrivilegeTemplateOutputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    # cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))
    privilege_templates = serializers.ListField(child=MySQLPrivilegeTemplateSerializer(), help_text=_("权限模版列表"))
