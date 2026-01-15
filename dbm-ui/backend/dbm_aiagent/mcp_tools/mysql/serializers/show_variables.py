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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import (
    mysql_machine_type_choices,
    mysql_popular_runtime_variables,
)
from backend.dbm_aiagent.utils import list_to_choices


class ShowMySQLVariablesInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    machine_type = serializers.ChoiceField(
        choices=mysql_machine_type_choices, help_text=_("实例的机器类型, 只能是 [single, backend, remote, spider] 中之一")
    )
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    variable_hints = serializers.ListField(
        child=serializers.ChoiceField(choices=list_to_choices(mysql_popular_runtime_variables)),
        help_text=_("运行时参数过滤列表, 不为空时只返回这个列表指定的参数"),  # , default=None
    )


class MySQLRuntimeVariableSerializer(serializers.Serializer):
    variable_name = serializers.CharField(help_text=_("运行时参数名"))
    variable_value = serializers.CharField(help_text=_("运行时参数值"))


class ShowMySQLVariablesOutputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    # address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    runtime_variables = serializers.ListField(child=MySQLRuntimeVariableSerializer(), help_text=_("MySQL 运行时参数列表"))
