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

import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.permission.constants import PrivilegeType
from backend.db_services.mysql.permission.db_account import mock_data
from backend.db_services.mysql.permission.db_account.dataclass import AccountMeta
from backend.db_services.mysql.permission.db_account.handlers import AccountHandler


class DBAccountBaseSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"))
    password = serializers.CharField(help_text=_("账号密码"))

    def validate_user(self, value):
        """校验账号是否符合规则"""

        pattern = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z\-._]{0,31}$")

        if not re.match(pattern, value):
            raise serializers.ValidationError(_("账号名称不符合要求, 请重新账号名"))

        return value

    def validate_password(self, value):
        """将密码进行解密并校验密码强度"""

        account = AccountMeta(password=value)
        verify_result = AccountHandler.verify_password_strength(account)
        if not verify_result["is_strength"]:
            raise serializers.ValidationError(_("密码强度不符合要求, 请重新输入密码"))

        return verify_result["password"]


class CreateMySQLAccountSerializer(DBAccountBaseSerializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_ACCOUNT_REQUEST}


class VerifyPasswordStrengthSerializer(serializers.Serializer):
    password = serializers.CharField(help_text=_("待校验密码"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.CHECK_PASSWORD_STRENGTH_REQUEST}


class VerifyPasswordStrengthInfoSerializer(serializers.Serializer):
    is_strength = serializers.BooleanField(help_text=_("密码是否满足强度"))
    password_verify_info = serializers.DictField(help_text=_("密码校验信息字典"), child=serializers.BooleanField())

    class Meta:
        swagger_schema_fields = {"example": mock_data.VERIFY_PASSWORD_STRENGTH_INFO_RESPONSE}


class DeleteMySQLAccountSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(help_text=_("账号ID"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_ACCOUNT_REQUEST}


class UpdateMySQLAccountSerializer(DBAccountBaseSerializer):
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    user = serializers.CharField(help_text=_("账号名称"), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.UPDATE_ACCOUNT_REQUEST}


class MySQLAccountInfoSerializer(DBAccountBaseSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    user = serializers.CharField(help_text=_("账号名称"))
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    creator = serializers.CharField(help_text=_("创建者"))
    create_time = serializers.DateTimeField(help_text=_("创建时间"))


class MySQLAccountRulesInfoSerializer(serializers.Serializer):
    rule_id = serializers.IntegerField(help_text=_("规则ID"))
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    access_db = serializers.CharField(help_text=_("访问DB"))
    privilege = serializers.CharField(help_text=_("规则列表"))
    creator = serializers.CharField(help_text=_("创建者"))
    create_time = serializers.DateTimeField(help_text=_("创建时间"))


class MySQLAccountRulesDetailSerializer(serializers.Serializer):
    account = MySQLAccountInfoSerializer(help_text=_("账号信息"))
    rules = serializers.ListSerializer(
        help_text=_("权限列表信息"), allow_empty=True, child=MySQLAccountRulesInfoSerializer()
    )


class FilterMySQLAccountRulesSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"), required=False)
    access_db = serializers.CharField(help_text=_("访问DB"), required=False)
    privilege = serializers.CharField(help_text=_("规则列表"), required=False)


class QueryMySQLAccountRulesSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"))
    access_dbs = serializers.ListField(help_text=_("访问DB列表"), child=serializers.CharField(), required=False)


class ListMySQLAccountRulesSerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text=_("规则数量"))
    results = serializers.ListSerializer(
        help_text=_("规则信息"), allow_empty=True, child=MySQLAccountRulesDetailSerializer()
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_MYSQL_ACCOUNT_RULE_RESPONSE}


class MySQLRuleTypeSerializer(serializers.Serializer):
    dml = serializers.ListField(
        help_text=_("dml"), child=serializers.ChoiceField(choices=PrivilegeType.DML.get_choices()), required=False
    )
    ddl = serializers.ListField(
        help_text=_("dml"), child=serializers.ChoiceField(choices=PrivilegeType.DDL.get_choices()), required=False
    )
    glob = serializers.ListField(
        help_text=_("glob"), child=serializers.ChoiceField(choices=PrivilegeType.GLOBAL.get_choices()), required=False
    )


class AddMySQLAccountRuleSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    access_db = serializers.CharField(help_text=_("访问DB"))
    privilege = MySQLRuleTypeSerializer()

    class Meta:
        swagger_schema_fields = {"example": mock_data.ADD_MYSQL_ACCOUNT_RULE_REQUEST}


class ModifyMySQLAccountRuleSerializer(AddMySQLAccountRuleSerializer):
    rule_id = serializers.IntegerField(help_text=_("规则ID"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.MODIFY_MYSQL_ACCOUNT_RULE_REQUEST}


class DeleteMySQLAccountRuleSerializer(serializers.Serializer):
    rule_id = serializers.IntegerField(help_text=_("规则ID"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_MYSQL_ACCOUNT_RULE_REQUEST}
