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

from backend.db_services.mysql.remote_service.mock_data import (
    CHECK_CLUSTER_DATABASE_REQUEST_DATA,
    CHECK_CLUSTER_DATABASE_RESPONSE_DATA,
    SHOW_DATABASES_REQUEST_DATA,
    SHOW_DATABASES_RESPONSE_DATA,
)


class ShowDatabasesRequestSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": SHOW_DATABASES_REQUEST_DATA}


class ShowDatabasesResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": SHOW_DATABASES_RESPONSE_DATA}


class CheckClusterDatabaseSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))
    db_names = serializers.ListField(help_text=_("DB名列表"), child=serializers.CharField(help_text=_("DB名")))

    class Meta:
        swagger_schema_fields = {"example": CHECK_CLUSTER_DATABASE_REQUEST_DATA}


class CheckClusterDatabaseResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": CHECK_CLUSTER_DATABASE_RESPONSE_DATA}
