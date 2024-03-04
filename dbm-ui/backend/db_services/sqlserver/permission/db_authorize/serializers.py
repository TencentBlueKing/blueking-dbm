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

from backend.db_meta.enums import ClusterType
from backend.db_services.sqlserver.permission.db_authorize import mock_data


class SQLServerPreCheckAuthorizeRulesSerializer(serializers.Serializer):
    class SQLServerDBUserSerializer(serializers.Serializer):
        user = serializers.CharField(help_text=_("账号名"))
        access_dbs = serializers.ListSerializer(help_text=_("访问DB列表"), child=serializers.CharField())

    sqlserver_users = serializers.ListSerializer(help_text=_("sqlserver账户规则"), child=SQLServerDBUserSerializer())
    target_instances = serializers.ListField(help_text=_("目标集群"), child=serializers.CharField(help_text=_("集群名")))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    cluster_ids = serializers.ListField(
        help_text=_("集群id列表"), child=serializers.IntegerField(), allow_empty=True, required=False
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_AUTHORIZE_RULES_DATA}


class SQLServerPreCheckAuthorizeRulesResponseSerializer(serializers.Serializer):
    pre_check = serializers.BooleanField(help_text=_("前置检查结果"))
    message = serializers.CharField(help_text=_("检查结果信息"))
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    authorize_data = serializers.DictField(help_text=_("授权数据信息"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_AUTHORIZE_RULES_RESPONSE_DATA}
