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

from backend.db_meta.enums import InstanceRole, InstanceStatus


class QueryByClusterSerializer(serializers.Serializer):
    keywords = serializers.ListSerializer(help_text=_("集群id/name/domain列表"), child=serializers.CharField())

    class Meta:
        swagger_schema_fields = {"example": {"keywords": ["a.b.c", "b.c.d", "1", "2"]}}


class QueryByClusterResultSerializer(serializers.Serializer):
    cluster = serializers.JSONField()
    proxy = serializers.JSONField()
    storage = serializers.JSONField()

    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "cluster": {
                        "id": 4,
                        "name": "abc",
                        "cluster_type": "TwemproxyTendisSSDInstance",
                        "immute_domain": "abc.dba.db",
                        "major_version": "TendisSSD-1.3",
                        "bk_cloud_id": 0,
                        "region": "",
                        "proxy_count": 2,
                        "redis_master_count": 1,
                        "redis_slave_count": 1,
                    },
                    "proxy": [
                        {
                            "id": 6,
                            "machine__ip": "127.0.0.3",
                            "port": 50000,
                            "name": "",
                            "status": "running",
                            "version": "",
                            "machine__spec_config": {
                                "id": 1,
                                "cpu": 1,
                                "mem": 2,
                                "name": 2,
                                "storage_spec": {"size": 500, "type": "ssd", "mount_point": "/data"},
                            },
                        },
                    ],
                    "storage": [
                        {
                            "id": 53,
                            "machine__ip": "127.0.0.1",
                            "port": 30017,
                            "name": "",
                            "status": "running",
                            "version": "",
                            "machine__spec_config": {
                                "id": 1,
                                "cpu": 1,
                                "mem": 2,
                                "name": 2,
                                "storage_spec": {"size": 500, "type": "ssd", "mount_point": "/data"},
                            },
                            "instance_role": "redis_slave",
                        },
                        {
                            "id": 18,
                            "machine__ip": "127.0.0.2",
                            "port": 30000,
                            "name": "",
                            "status": "running",
                            "version": "",
                            "machine__spec_config": {
                                "id": 1,
                                "cpu": 1,
                                "mem": 2,
                                "name": 2,
                                "storage_spec": {"size": 500, "type": "ssd", "mount_point": "/data"},
                            },
                            "instance_role": "redis_master",
                        },
                    ],
                }
            ]
        }


class QueryByIpSerializer(serializers.Serializer):
    ips = serializers.ListField(child=serializers.IPAddressField())

    class Meta:
        swagger_schema_fields = {"example": {"ips": ["127.0.0.1"]}}


class QueryByIpResultSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    role = serializers.CharField(max_length=32)
    cluster = serializers.JSONField()
    spec_config = serializers.JSONField()

    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "ip": "127.0.0.1",
                    "role": "redis_master",
                    "cluster": {
                        "id": 2,
                        "name": "online",
                        "cluster_type": "TwemproxyRedisInstance",
                        "bk_cloud_id": 0,
                        "proxy_count": 2,
                        "redis_master_count": 1,
                        "redis_slave_count": 1,
                        "region": "",
                    },
                    "spec_config": {
                        "id": 1,
                        "name": 2,
                        "cpu": 1,
                        "mem": 2,
                        "storage_spec": {"mount_point": "/data", "size": 500, "type": "ssd"},
                    },
                }
            ]
        }


class QueryMasterSlaveByIpResultSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "cluster": {
                        "id": 2,
                        "name": "online",
                        "cluster_type": "TwemproxyRedisInstance",
                        "bk_cloud_id": 0,
                        "region": "",
                    },
                    "master_ip": "127.0.0.1",
                    "slave_ip": "127.0.0.2",
                    "instances": [
                        {
                            "name": "",
                            "ip": "127.0.0.1",
                            "port": 30003,
                            "instance": "127.0.0.1:30003",
                            "status": "running",
                            "phase": "online",
                            "bk_instance_id": 7,
                            "bk_host_id": 11,
                            "bk_cloud_id": 0,
                            "bk_biz_id": 3,
                        }
                    ],
                }
            ]
        }


class QueryByOneClusterSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"))

    class Meta:
        swagger_schema_fields = {"example": {"cluster_id": 1}}


class QueryClusterIpsSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"), required=False)
    ip = serializers.CharField(max_length=32, required=False)
    limit = serializers.IntegerField(help_text=_("limit"), required=False, min_value=1)
    offset = serializers.IntegerField(help_text=_("offset"), required=False, min_value=1)
    role = serializers.ChoiceField(help_text=_("role"), required=False, choices=InstanceRole.get_choices())
    status = serializers.ChoiceField(help_text=_("status"), required=False, choices=InstanceStatus.get_choices())

    class Meta:
        swagger_schema_fields = {
            "example": {
                "cluster_id": 1,
                "ip": "127.0.0.1",
                "limit": 1,
                "offset": 2,
                "role": "redis_master/redis_slave",
                "status": "running",
            }
        }
