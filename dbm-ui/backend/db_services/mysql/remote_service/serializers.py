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
    FLASHBACK_CHECK_DATA,
    SHOW_DATABASES_REQUEST_DATA,
    SHOW_DATABASES_RESPONSE_DATA,
    SHOW_TABLES_RESPONSE_DATA,
)
from backend.flow.consts import TenDBBackUpLocation
from backend.ticket.builders.mysql.base import DBTableField


class ShowDatabasesRequestSerializer(serializers.Serializer):
    class QueryClusterRoleDatabaseSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID列表"))
        role = serializers.ChoiceField(
            help_text=_("查询的备份角色"), choices=TenDBBackUpLocation.get_choices(), required=False
        )

    # 支持两种模式查询 集群ID列表/集群角色信息列表
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), required=False)
    cluster_infos = serializers.ListSerializer(
        help_text=_("集群信息列表"), child=QueryClusterRoleDatabaseSerializer(), required=False
    )

    class Meta:
        swagger_schema_fields = {"example": SHOW_DATABASES_REQUEST_DATA}


class ShowTablesRequestSerializer(serializers.Serializer):
    class DbInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID列表"))
        dbs = serializers.ListField(help_text=_("查询的DB列表"), child=DBTableField(db_field=True))

    cluster_db_infos = serializers.ListSerializer(help_text=_("集群数据库信息"), child=DbInfoSerializer())


class ShowTablesResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": SHOW_TABLES_RESPONSE_DATA}


class ShowDatabasesResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": SHOW_DATABASES_RESPONSE_DATA}


class CheckClusterDatabaseSerializer(serializers.Serializer):
    class CheckInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        db_names = serializers.ListField(help_text=_("DB名列表"), child=serializers.CharField(help_text=_("DB名")))

    infos = serializers.ListSerializer(help_text=_("集群校验信息"), child=CheckInfoSerializer())

    class Meta:
        swagger_schema_fields = {"example": CHECK_CLUSTER_DATABASE_REQUEST_DATA}


class CheckClusterDatabaseResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": CHECK_CLUSTER_DATABASE_RESPONSE_DATA}


class CheckFlashbackInfoSerializer(serializers.Serializer):
    class FlashbackSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
        databases_ignore = serializers.ListField(help_text=_("忽略库列表"), child=DBTableField(db_field=True))
        tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
        tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField())

    infos = serializers.ListSerializer(help_text=_("flashback信息"), child=FlashbackSerializer(), allow_empty=False)


class CheckFlashbackInfoResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": FLASHBACK_CHECK_DATA}
