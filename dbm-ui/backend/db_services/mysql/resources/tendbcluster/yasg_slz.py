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

from backend.db_services.dbbase.resources.yasg_slz import paginated_machine_resource_example

from .query import ListRetrieveResource

REF_NAME = "dbha"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "id": 16,
            "phase": "online",
            "status": "normal",
            "operations": [],
            "cluster_name": "spidertest",
            "cluster_type": "tendbcluster",
            "cluster_spec": {
                "creator": "admin",
                "updater": "admin",
                "spec_id": 3,
                "spec_name": "test_msql",
                "spec_cluster_type": "tendbsingle",
                "spec_machine_type": "single",
                "cpu": {"max": "12", "min": "12"},
                "mem": {"max": "2", "min": "1"},
                "device_class": [],
                "storage_spec": [{"size": 10, "type": "HDD", "mount_point": "/data123"}],
                "desc": "qqwrqr",
                "instance_num": 1,
                "qps": {},
            },
            "cluster_capacity": 10.0,
            "major_version": "MySQL-5.7",
            "region": "xxx",
            "master_domain": "spider.spidertest.db",
            "slave_domain": "",
            "bk_biz_id": 3,
            "bk_biz_name": "DBA",
            "bk_cloud_id": 0,
            "bk_cloud_name": "xxx",
            "spider_master": [
                {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 25000,
                    "instance": "127.0.0.1:25000",
                    "status": "running",
                    "phase": "",
                    "bk_instance_id": 1052,
                    "bk_host_id": 165,
                    "bk_cloud_id": 0,
                    "bk_biz_id": 3,
                },
                {"...": "...."},
            ],
            "spider_slave": [
                {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 20000,
                    "instance": "127.0.0.1:20000",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1051,
                    "bk_host_id": 107,
                    "bk_cloud_id": 0,
                    "bk_biz_id": 3,
                }
            ],
            "spider_mnt": [
                {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 20000,
                    "instance": "127.0.0.1:20000",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1051,
                    "bk_host_id": 107,
                    "bk_cloud_id": 0,
                    "bk_biz_id": 3,
                }
            ],
            "cluster_shard_num": 2,
            "remote_shard_num": 2,
            "machine_pair_cnt": 1,
            "remote_db": [
                {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 20001,
                    "instance": "127.0.0.1:20001",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1049,
                    "bk_host_id": 107,
                    "bk_cloud_id": 0,
                    "bk_biz_id": 3,
                },
                {"...": "...."},
            ],
            "remote_dr": [
                {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 20001,
                    "instance": "127.0.0.1:20001",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1048,
                    "bk_host_id": 108,
                    "bk_cloud_id": 0,
                    "bk_biz_id": 3,
                },
                {"...": "...."},
            ],
            "db_module_id": 554,
            "db_module_name": "",
            "creator": "admin",
            "create_at": "2023-07-03 19:25:23",
        }
    ],
}

paginated_instance_resource_example = {
    "count": 18,
    "next": "http://127.0.0.1:8001/apis/mysql/bizs/3/spider_resources/list_instances/?limit=10&offset=10",
    "previous": "",
    "results": [
        {
            "id": 9,
            "cluster_id": 16,
            "cluster_type": "tendbcluster",
            "cluster_name": "spidertest",
            "version": "MySQL-5.7",
            "db_module_id": 554,
            "bk_cloud_id": 0,
            "bk_cloud_name": "xxx",
            "ip": "127.0.0.1",
            "port": 26000,
            "instance_address": "127.0.0.1:26000",
            "bk_host_id": 165,
            "role": "spider_ctl",
            "master_domain": "spider.spidertest.db",
            "slave_domain": "",
            "status": "running",
            "create_at": "2023-07-03 19:25:23",
        }
    ],
}

resource_topo_graph_example = {
    "node_id": "spider.spidertest.abc.db",
    "nodes": [
        {
            "node_id": "127.0.0.1:25000",
            "node_type": "spider_master",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:25000/details",
        },
        {
            "node_id": "127.0.0.1:25000",
            "node_type": "spider_master",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:25000/details",
        },
        {"node_id": "spider.spidertest.abc.db", "node_type": "entry_dns", "url": ""},
        {
            "node_id": "127.0.0.1:20001",
            "node_type": "remote::remote_master",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:20001/details",
        },
        {
            "node_id": "127.0.0.1:20000",
            "node_type": "remote::remote_master",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:20000/details",
        },
        {
            "node_id": "127.0.0.1:20001",
            "node_type": "remote::remote_slave",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:20001/details",
        },
        {
            "node_id": "127.0.0.1:20000",
            "node_type": "remote::remote_slave",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:20000/details",
        },
        {
            "node_id": "127.0.0.1:26000",
            "node_type": "controller_node",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:25000/details",
        },
        {
            "node_id": "127.0.0.1:26000",
            "node_type": "controller_node",
            "url": "/database/3/tendbcluster-instance/28/127.0.0.1:25000/details",
        },
    ],
    "groups": [
        {
            "node_id": "spider_master",
            "group_name": "Spider Master",
            "children_id": ["127.0.0.1:25000", "127.0.0.1:25000"],
        },
        {"node_id": "spider_master_entry_bind", "group_name": "xxx", "children_id": ["spider.spidertest.abc.db"]},
        {
            "node_id": "remote::remote_master",
            "group_name": "RemoteDB",
            "children_id": ["127.0.0.1:20001", "127.0.0.1:20000"],
        },
        {
            "node_id": "remote::remote_slave",
            "group_name": "RemoteDR",
            "children_id": ["127.0.0.1:20001", "127.0.0.1:20000"],
        },
        {"node_id": "controller_group", "group_name": "xxx", "children_id": ["127.0.0.1:26000", "127.0.0.1:26000"]},
    ],
    "lines": [
        {
            "source": "spider_master_entry_bind",
            "source_type": "group",
            "target": "spider_master",
            "target_type": "group",
            "label": "access",
            "label_name": "xxx",
        },
        {
            "source": "spider_master",
            "source_type": "group",
            "target": "remote::remote_master",
            "target_type": "group",
            "label": "access",
            "label_name": "xxx",
        },
    ],
    "foreign_relations": {"rep_to": [], "rep_from": [], "access_to": [], "access_from": []},
}


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
        swagger_schema_fields = {"example": ListRetrieveResource.get_fields()}
        ref_name = f"{REF_NAME}_ResourceFieldSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"


class ResourceInstanceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_instance_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceInstanceSLZ"


class PaginatedMachineResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_machine_resource_example}
        ref_name = f"{REF_NAME}_PaginatedMachineResourceSLZ"


class ResourceTopoGraphSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": resource_topo_graph_example}
        ref_name = f"{REF_NAME}_ResourceTopoGraphSLZ"
