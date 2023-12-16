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

REF_NAME = "mongodb"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "id": 103,
            "phase": "online",
            "phase_name": "normal",
            "status": "normal",
            "operations": [],
            "cluster_name": "mongo-xxx",
            "cluster_type": "MongoShardedCluster",
            "master_domain": "mongodb.mongo-xxx.dba.db",
            "slave_domain": "",
            "bk_biz_id": 3,
            "bk_biz_name": "DBA",
            "bk_cloud_id": 0,
            "bk_cloud_name": "xxxx",
            "major_version": "2.4.0",
            "region": "",
            "mongos": [
                {
                    "name": "",
                    "ip": "1.1.1.1",
                    "port": 10000,
                    "instance": "1.1.1.1:10000",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 0,
                    "bk_host_id": 102,
                    "bk_cloud_id": 0,
                    "spec_config": "",
                    "bk_biz_id": 3,
                    "admin_port": 11000,
                },
                {"...": "..."},
                {"...": "..."},
            ],
            "mongodb": [
                {
                    "name": "",
                    "ip": "2.2.2.2",
                    "port": 20000,
                    "instance": "2.2.2.2:20000",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 0,
                    "bk_host_id": 79,
                    "bk_cloud_id": 0,
                    "spec_config": {"spec_id": 279, "spec_config": ""},
                    "bk_biz_id": 3,
                },
                {"...": "..."},
                {"...": "..."},
            ],
            "mongo_config": [{"...": "..."}, {"...": "..."}, {"...": "..."}],
            "db_module_name": "",
            "db_module_id": 2,
            "creator": "kio",
            "create_at": "2023-12-30T19:47:31+08:00",
        }
    ],
}

paginated_instance_resource_example = {
    "count": 18,
    "next": "http://127.0.0.1:8001/apis/mysql/bizs/3/spider_resources/list_instances/?limit=10&offset=10",
    "previous": "",
    "results": [
        {
            "id": 829,
            "cluster_id": 103,
            "cluster_type": "MongoShardedCluster",
            "cluster_name": "mongo-kio",
            "version": "2.4.0",
            "db_module_id": 2,
            "bk_cloud_id": 0,
            "bk_cloud_name": "xxxx",
            "ip": "1.1.1.1",
            "port": 20000,
            "shard": "S1",
            "instance_address": "1.1.1.1:20000",
            "bk_host_id": 80,
            "role": "mongo_m1",
            "machine_type": "mongo_config",
            "master_domain": "mongodb.mongo-xxx.dba.db",
            "slave_domain": "",
            "status": "running",
            "create_at": "2023-12-30T19:47:26+08:00",
            "spec_config": {"spec_id": 279, "spec_config": ""},
        }
    ],
}

resource_topo_graph_example = {}


class PaginatedResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example}
        ref_name = f"{REF_NAME}_PaginatedResourceSLZ"


class PaginatedInstanceResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_instance_resource_example}
        ref_name = f"{REF_NAME}_PaginatedInstanceResourceSLZ"


class ResourceFieldSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {}}
        ref_name = f"{REF_NAME}_ResourceFieldSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"


class ResourceInstanceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_instance_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceInstanceSLZ"


class ResourceTopoGraphSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": resource_topo_graph_example}
        ref_name = f"{REF_NAME}_ResourceTopoGraphSLZ"
