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

from backend.db_services.mysql.cluster.mock_data import (
    FIND_RELATED_CLUSTERS_BY_ID_REQUEST_DATA,
    FIND_RELATED_CLUSTERS_BY_ID_RESPONSE_DATA,
    FIND_RELATED_CLUSTERS_BY_INSTANCE_REQUEST_DATA,
    FIND_RELATED_CLUSTERS_BY_INSTANCE_RESPONSE_DATA,
)


class FindRelatedClustersByClusterIdRequestSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": FIND_RELATED_CLUSTERS_BY_ID_REQUEST_DATA}


class FindRelatedClustersByClusterIdResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": FIND_RELATED_CLUSTERS_BY_ID_RESPONSE_DATA}


class FindRelatedClustersByInstancesRequestSerializer(serializers.Serializer):
    class InstanceSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        ip = serializers.CharField(help_text=_("IP地址"))
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        port = serializers.IntegerField(help_text=_("端口号"))

    instances = serializers.ListField(help_text=_("实例列表"), child=InstanceSerializer())

    class Meta:
        swagger_schema_fields = {"example": FIND_RELATED_CLUSTERS_BY_INSTANCE_REQUEST_DATA}


class FindRelatedClustersByInstancesResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": FIND_RELATED_CLUSTERS_BY_INSTANCE_RESPONSE_DATA}
