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
from rest_framework import serializers

from .query import VictoriaMetricsStandardListRetrieveResource

REF_NAME = "victoriametricsstandard"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "id": 1,
            "cluster_name": "bk-dbm",
            "write_entry": "vminsert.bk-dbm.blueking.db:8480",
            "query_entry": "vmselect.bk-dbm.blueking.db:8481",
            "storage_entry": "127.0.0.1:8400\n127.0.0.2:8400",
            "status": "normal",
            "tags": ["env:prod"],
            "major_version": "v1.115.0",
            "region": "sh",
            "creator": "admin",
            "create_at": "2024-01-01 10:00:00",
            "...": "...",
        }
    ],
}


class PaginatedResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example}
        ref_name = f"{REF_NAME}_PaginatedResourceSLZ"


class ResourceFieldSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": VictoriaMetricsStandardListRetrieveResource.get_fields()}
        ref_name = f"{REF_NAME}_ResourceFieldSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"


class ResourceTopoGraphSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"nodes": [], "groups": [], "lines": []}}
        ref_name = f"{REF_NAME}_ResourceTopoGraphSLZ"
