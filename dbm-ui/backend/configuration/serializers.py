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
from rest_framework import serializers

from backend.bk_web.constants import LEN_NORMAL, LEN_SHORT
from backend.bk_web.serializers import AuditedSerializer
from backend.configuration import mock_data
from backend.configuration.constants import DBType
from backend.configuration.mock_data import PASSWORD_POLICY
from backend.configuration.models.function_controller import FunctionController
from backend.configuration.models.ip_whitelist import IPWhitelist
from backend.configuration.models.system import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    """系统配置序列化"""

    type = serializers.CharField(required=True, max_length=LEN_NORMAL)
    key = serializers.CharField(required=True, max_length=LEN_NORMAL)

    class Meta:
        model = SystemSettings
        fields = ("id", "type", "key", "value")


class ProfileSerializer(serializers.Serializer):
    label = serializers.CharField(required=True, max_length=LEN_SHORT)
    values = serializers.JSONField()


class ListDBAdminSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class DBAdminSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())
    users = serializers.ListSerializer(help_text=_("人员列表"), child=serializers.CharField())


class UpsertDBAdminSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_admins = serializers.ListSerializer(child=DBAdminSerializer())


class PasswordPolicySerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=DBType.get_choices())
    policy = serializers.JSONField(help_text=_("密码安全策略"))

    class Meta:
        swagger_schema_fields = {"example": PASSWORD_POLICY}

    def validate(self, attrs):
        try:
            if int(attrs["policy"]["max_length"]) < int(attrs["policy"]["min_length"]):
                raise serializers.ValidationError(_("密码最小长度不能大于最大长度"))
        except ValueError:
            raise serializers.ValidationError(_("请确保密码长度范围为整型"))

        return attrs


class GetPasswordPolicySerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=DBType.get_choices())


class IPWhitelistSerializer(AuditedSerializer, serializers.ModelSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    remark = serializers.CharField(help_text=_("备注"))
    ips = serializers.ListSerializer(help_text=_("ip列表"), child=serializers.CharField())

    class Meta:
        model = IPWhitelist
        fields = "__all__"
        read_only_fields = ("id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": mock_data.CREATE_IP_WHITELIST_DATA}


class DeleteIPWhitelistSerializer(serializers.Serializer):
    ids = serializers.ListSerializer(help_text=_("id列表"), child=serializers.CharField())


class ListIPWhitelistSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    ip = serializers.CharField(help_text=_("代过滤IP"), required=False, allow_null=True, allow_blank=True)
    ids = serializers.ListField(child=serializers.IntegerField(help_text=_("待过滤白名单ID")), required=False)


class FunctionControllerSerializer(serializers.Serializer):
    class Meta:
        model = FunctionController
        fields = "__all__"
