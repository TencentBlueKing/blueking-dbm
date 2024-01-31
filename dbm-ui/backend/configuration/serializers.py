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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.bk_web.constants import LEN_NORMAL, LEN_SHORT
from backend.bk_web.serializers import AuditedSerializer
from backend.configuration import mock_data
from backend.configuration.constants import DBType
from backend.configuration.mock_data import BIZ_SETTINGS_DATA, PASSWORD_POLICY, VERIFY_PASSWORD_DATA
from backend.configuration.models.function_controller import FunctionController
from backend.configuration.models.ip_whitelist import IPWhitelist
from backend.configuration.models.system import BizSettings, SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_services.dbpermission.constants import AccountType
from backend.ticket.builders.common.field import DBTimezoneField


class SystemSettingsSerializer(serializers.ModelSerializer):
    """系统配置序列化"""

    type = serializers.CharField(required=True, max_length=LEN_NORMAL)
    key = serializers.CharField(required=True, max_length=LEN_NORMAL)

    class Meta:
        model = SystemSettings
        fields = ("id", "type", "key", "value")


class BizSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BizSettings
        fields = ("id", "bk_biz_id", "type", "key", "value")


class ListBizSettingsSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    key = serializers.CharField(help_text=_("查询key"), required=False)


class ListBizSettingsResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": BIZ_SETTINGS_DATA}


class UpdateBizSettingsSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    key = serializers.CharField(help_text=_("更新key"))
    value = serializers.JSONField(help_text=_("更新value"))
    value_type = serializers.CharField(help_text=_("value类型"), default="dict", required=False)


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


class ModifyMySQLPasswordRandomCycleSerializer(serializers.Serializer):
    class CrontabSerializer(serializers.Serializer):
        minute = serializers.CharField(help_text=_("分钟"))
        hour = serializers.CharField(help_text=_("小时"))
        day_of_week = serializers.CharField(help_text=_("每周几天(eg: 1,4,5 表示一周的周一，周四，周五)"), required=False)
        day_of_month = serializers.CharField(help_text=_("每月几天(eg: 1, 11, 13 表示每月的1号，11号，13号)"), required=False)

    crontab = CrontabSerializer(help_text=_("crontab表达式"))


class GetMySQLAdminPasswordSerializer(serializers.Serializer):
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)

    begin_time = DBTimezoneField(help_text=_("开始时间"), required=False)
    end_time = DBTimezoneField(help_text=_("结束时间"), required=False)
    instances = serializers.CharField(help_text=_("过滤的实例列表(通过,分割，实例格式为--ip:port)"), required=False)


class GetMySQLAdminPasswordResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.MYSQL_ADMIN_PASSWORD_DATA}


class ModifyMySQLAdminPasswordSerializer(serializers.Serializer):
    class InstanceInfoSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("实例ip"))
        port = serializers.CharField(help_text=_("实例port"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
        role = serializers.CharField(help_text=_("实例角色"))

    lock_hour = serializers.IntegerField(help_text=_("密码到期小时"))
    password = serializers.CharField(help_text=_("密码"))
    instance_list = serializers.ListSerializer(help_text=_("实例信息"), child=InstanceInfoSerializer())

    def validate(self, attrs):
        invalid_characters = re.compile(r"[`\'\"]")
        if invalid_characters.findall(attrs["password"]):
            raise serializers.ValidationError(_("修改密码中不允许包含单引号，双引号和反引号"))

        return attrs


class PasswordPolicySerializer(serializers.Serializer):
    class PolicySerializer(serializers.Serializer):
        class IncludeRuleSerializer(serializers.Serializer):
            numbers = serializers.BooleanField(help_text=_("是否包含数字"))
            symbols = serializers.BooleanField(help_text=_("是否包含特殊符号"))
            lowercase = serializers.BooleanField(help_text=_("是否包含小写字符"))
            uppercase = serializers.BooleanField(help_text=_("是否包含大写字符"))

        class ExcludeContinuousRuleSerializer(serializers.Serializer):
            limit = serializers.IntegerField(help_text=_("最大连续长度"))
            letters = serializers.BooleanField(help_text=_("是否限制连续字母"))
            numbers = serializers.BooleanField(help_text=_("是否限制连续数字"))
            repeats = serializers.BooleanField(help_text=_("是否限制连续重复字符"))
            symbols = serializers.BooleanField(help_text=_("是否限制连续特殊字符"))
            keyboards = serializers.BooleanField(help_text=_("是否限制连续键盘序"))

        max_length = serializers.IntegerField(help_text=_("最大长度"))
        min_length = serializers.IntegerField(help_text=_("最小长度"))
        include_rule = IncludeRuleSerializer(help_text=_("包含规则"))
        exclude_continuous_rule = ExcludeContinuousRuleSerializer(help_text=_("排除连续性规则"))

    rule = serializers.JSONField(help_text=_("密码安全策略"))
    name = serializers.CharField(help_text=_("密码安全规则策略名称"))
    id = serializers.IntegerField(help_text=_("密码安全规则策略id"))

    class Meta:
        swagger_schema_fields = {"example": PASSWORD_POLICY}

    def validate(self, attrs):
        try:
            if int(attrs["rule"]["max_length"]) < int(attrs["rule"]["min_length"]):
                raise serializers.ValidationError(_("密码最小长度不能大于最大长度"))
        except ValueError:
            raise serializers.ValidationError(_("请确保密码长度范围为整型"))

        return attrs


class VerifyPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(help_text=_("待校验密码"))


class VerifyPasswordResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": VERIFY_PASSWORD_DATA}


class GetPasswordPolicySerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(help_text=_("账号类型"), choices=AccountType.get_choices())


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

    limit = serializers.IntegerField(help_text=_("分页限制"), default=10, required=False)
    offset = serializers.IntegerField(help_text=_("分页起始"), default=0, required=False)


class UpdateDutyNoticeSerializer(serializers.Serializer):
    schedule_table = serializers.JSONField(help_text=_("排期表通知"))
    person_duty = serializers.JSONField(help_text=_("个人轮值通知"))


class FunctionControllerSerializer(serializers.Serializer):
    class Meta:
        model = FunctionController
        fields = "__all__"
