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


class QueryByIpSerializer(serializers.Serializer):
    ips = serializers.ListField(child=serializers.IPAddressField())

    class Meta:
        swagger_schema_fields = {"example": {
            "ips": ["127.0.0.1"]
        }}


class QueryByIpResultSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    role = serializers.CharField(max_length=32)
    cluster = serializers.JSONField()
    spec = serializers.JSONField()

    class Meta:
        swagger_schema_fields = {"example": [
            {'ip': '127.0.0.1',
             'role': 'redis_master',
             'cluster': {'id': 2,
                         'name': 'online',
                         'cluster_type': 'TwemproxyRedisInstance',
                         'bk_cloud_id': 0,
                         'region': '',
                         'deploy_plan_id': 0},
             'spec': {"id": 1, "name": 2}}
        ]}

