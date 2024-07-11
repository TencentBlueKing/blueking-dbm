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

REF_NAME = "delegated_mysql"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "cluster_name": "bk-dbm",
            "master_domain": "example.domain.db",
            "masters": ["0.0.0.1#30000"],
            "...": "...",
        }
    ],
}


class PaginatedResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example}
        ref_name = f"{REF_NAME}_PaginatedResourceSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"
