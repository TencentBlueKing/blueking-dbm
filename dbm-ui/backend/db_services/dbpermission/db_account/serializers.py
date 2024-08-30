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

from backend.configuration.constants import DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import ClusterType
from backend.db_services.dbpermission import constants
from backend.db_services.dbpermission.constants import AccountType, FormatType, PrivilegeType
from backend.db_services.dbpermission.db_account import mock_data


class DBAccountBaseSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"), required=False)
    password = serializers.CharField(help_text=_("账号密码"))
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())

    @classmethod
    def check_username_valid(cls, account_type, user):
        if account_type == AccountType.MONGODB:
            user_pattern = re.compile(r"^[0-9a-zA-Z]{1,31}\.[0-9a-zA-Z\-._]{1,31}$")
        else:
            user_pattern = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z\-._]{0,31}$")

        if not re.match(user_pattern, user):
            raise serializers.ValidationError(_("账号名称不符合要求, 请重新更改账号名"))

        if len(user) > constants.MAX_ACCOUNT_LENGTH:
            raise serializers.ValidationError(_("账号名称不符合过长，请不要超过31位"))

    @classmethod
    def check_password_valid(cls, password, account_type):
        security_type = DBPrivSecurityType.db_type_to_security_type(account_type)
        verify_result = DBPasswordHandler.verify_password_strength(password, security_type=security_type, echo=True)
        if not verify_result["is_strength"]:
            raise serializers.ValidationError(_("密码强度不符合要求，请重新输入密码。"))
        return verify_result["password"]

    def validate(self, attrs):
        # 校验账号是否符合规则
        if attrs.get("user"):
            self.check_username_valid(attrs["account_type"], attrs.get("user"))
        # 将密码进行解密并校验密码强度
        attrs["password"] = self.check_password_valid(attrs["password"], attrs["account_type"])
        return attrs

    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_ACCOUNT_REQUEST}


class CreateAccountSerializer(DBAccountBaseSerializer):
    user = serializers.CharField(help_text=_("账号名称"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_ACCOUNT_REQUEST}


class DeleteAccountSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())

    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_ACCOUNT_REQUEST}


class UpdateAccountPasswordSerializer(DBAccountBaseSerializer):
    account_id = serializers.IntegerField(help_text=_("账号ID"))
    user = serializers.CharField(help_text=_("账号名称"), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.UPDATE_ACCOUNT_REQUEST}


class AccountRulesDetailSerializer(serializers.Serializer):
    class AccountInfoSerializer(DBAccountBaseSerializer):
        bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
        user = serializers.CharField(help_text=_("账号名称"))
        account_id = serializers.IntegerField(help_text=_("账号ID"))
        creator = serializers.CharField(help_text=_("创建者"))
        create_time = serializers.DateTimeField(help_text=_("创建时间"))

    class AccountRulesInfoSerializer(serializers.Serializer):
        rule_id = serializers.IntegerField(help_text=_("规则ID"))
        account_id = serializers.IntegerField(help_text=_("账号ID"))
        bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
        access_db = serializers.CharField(help_text=_("访问DB"))
        privilege = serializers.CharField(help_text=_("规则列表"))
        creator = serializers.CharField(help_text=_("创建者"))
        create_time = serializers.DateTimeField(help_text=_("创建时间"))

    account = AccountInfoSerializer(help_text=_("账号信息"))
    rules = serializers.ListSerializer(help_text=_("权限列表信息"), allow_empty=True, child=AccountRulesInfoSerializer())


class FilterAccountRulesSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())
    rule_ids = serializers.CharField(help_text=_("规则ID列表(通过,分割)"), required=False)
    user = serializers.CharField(help_text=_("账号名称"), required=False)
    access_db = serializers.CharField(help_text=_("访问DB"), required=False)
    privilege = serializers.CharField(help_text=_("规则列表"), required=False)


class PageAccountRulesSerializer(FilterAccountRulesSerializer):
    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class AccountUserSerializer(serializers.Serializer):
    ips = serializers.CharField(help_text=_("过滤ip，多个ip以逗号分割"))
    immute_domains = serializers.CharField(help_text=_("集群域名，多个域名以逗号分割"))
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class AccountPrivSerializer(AccountUserSerializer):
    users = serializers.CharField(help_text=_("账号名称，多个账号以逗号分割"))
    dbs = serializers.CharField(help_text=_("访问DB，多个DB以逗号分割"), required=False)
    format_type = serializers.ChoiceField(
        help_text=_("format格式"), choices=FormatType.get_choices(), default=FormatType.IP
    )


class FilterPrivSerializer(AccountPrivSerializer):
    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class QueryAccountRulesSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"))
    access_dbs = serializers.ListField(help_text=_("访问DB列表"), child=serializers.CharField(), required=False)
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())


class ListAccountRulesSerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text=_("规则数量"))
    results = serializers.ListSerializer(help_text=_("规则信息"), allow_empty=True, child=AccountRulesDetailSerializer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_MYSQL_ACCOUNT_RULE_RESPONSE}


class AddAccountRuleSerializer(serializers.Serializer):
    class RuleTypeSerializer(serializers.Serializer):
        dml = serializers.ListField(
            help_text=_("dml"),
            child=serializers.ChoiceField(choices=PrivilegeType.MySQL.DML.get_choices()),
            required=False,
        )
        ddl = serializers.ListField(
            help_text=_("dml"),
            child=serializers.ChoiceField(choices=PrivilegeType.MySQL.DDL.get_choices()),
            required=False,
        )
        glob = serializers.ListField(
            help_text=_("glob"),
            child=serializers.ChoiceField(choices=PrivilegeType.MySQL.GLOBAL.get_choices()),
            required=False,
        )
        mongo_user = serializers.ListField(
            help_text=_("mongo用户权限"),
            child=serializers.ChoiceField(choices=PrivilegeType.MongoDB.USER.get_choices()),
            required=False,
        )
        mongo_manager = serializers.ListField(
            help_text=_("mongo管理权限"),
            child=serializers.ChoiceField(choices=PrivilegeType.MongoDB.MANAGER.get_choices()),
            required=False,
        )
        sqlserver_dml = serializers.ListField(
            help_text=_("sqlserver-dml权限"),
            child=serializers.ChoiceField(choices=PrivilegeType.SQLServer.DML.get_choices()),
            required=False,
        )
        sqlserver_owner = serializers.ListField(
            help_text=_("sqlserver-owner权限"),
            child=serializers.ChoiceField(choices=PrivilegeType.SQLServer.OWNER.get_choices()),
            required=False,
        )

    account_id = serializers.IntegerField(help_text=_("账号ID"))
    access_db = serializers.CharField(help_text=_("访问DB"), required=False)
    privilege = RuleTypeSerializer(help_text=_("授权规则"), required=False)
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())

    class Meta:
        swagger_schema_fields = {"example": mock_data.ADD_MYSQL_ACCOUNT_RULE_REQUEST}


class ModifyAccountRuleSerializer(AddAccountRuleSerializer):
    rule_id = serializers.IntegerField(help_text=_("规则ID"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.MODIFY_MYSQL_ACCOUNT_RULE_REQUEST}


class DeleteAccountRuleSerializer(ModifyAccountRuleSerializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_MYSQL_ACCOUNT_RULE_REQUEST}
