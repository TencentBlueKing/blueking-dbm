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

from .query import ListRetrieveResource

REF_NAME = "oracle"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "id": 101,
            "db_type": "oracle",
            "phase": "online",
            "phase_name": "normal",
            "status": "normal",
            "operations": [],
            "cluster_time_zone": "+08:00",
            "cluster_name": "110-xxx",
            "cluster_alias": "110xxx",
            "cluster_access_port": 0,
            "cluster_stats": {},
            "cluster_type": "oracle_primary_standby",
            "cluster_type_name": "oracle_ha",
            "disaster_tolerance_level": "disaster_tolerance_level",
            "master_domain": "xxx.1xx.cf.db",
            "slave_domain": "",
            "cluster_entry": [
                {"cluster_entry_type": "dns", "entry": "xxx.1xx.cf.db", "role": "master_entry"},
                {"cluster_entry_type": "dns", "entry": "xxx.1xx.cf.db", "role": "master_entry"},
            ],
            "bk_biz_id": 3,
            "bk_biz_name": "DBA",
            "bk_cloud_id": 0,
            "bk_cloud_name": "xxx",
            "major_version": "1.xx.x",
            "region": "xxx",
            "city": "default",
            "db_module_name": "",
            "db_module_id": 0,
            "creator": "admin",
            "updater": "admin",
            "create_at": "2023-12-30T19:47:31+08:00",
            "update_at": "2023-12-30T19:47:31+08:00",
            "cluster_spec": None,
            "tags": [],
            "primaries": [
                {
                    "name": "CFXX",
                    "ip": "1.1.1.11",
                    "port": 1235,
                    "instance": "1.1.1.11:1235",
                    "status": "running",
                    "version": "",
                    "phase": "online",
                    "bk_instance_id": 0,
                    "bk_host_id": 12,
                    "bk_cloud_id": 0,
                    "spec_config": "",
                    "bk_sub_zone": "",
                    "bk_biz_id": 3,
                    "is_stand_by": True,
                }
            ],
            "standbys": [
                {
                    "name": "CFXX",
                    "ip": "1.1.1.12",
                    "port": 1234,
                    "instance": "1.1.1.12:1234",
                    "status": "running",
                    "version": "",
                    "phase": "online",
                    "bk_instance_id": 0,
                    "bk_host_id": 13,
                    "bk_cloud_id": 0,
                    "spec_config": "",
                    "bk_sub_zone": "",
                    "bk_biz_id": 3,
                    "is_stand_by": True,
                }
            ],
        }
    ],
}

resource_topo_graph_example = {
    "node_id": "xxxx.1xx.cf.db",
    "nodes": [
        {"node_id": "1.1.1.11:1235", "node_type": "oracle::primary", "status": "running"},
        {"node_id": "1.1.1.12:1234", "node_type": "oracle::standby", "status": "running"},
        {"node_id": "xxxx.1xx.cf.db", "node_type": "entry_dns", "status": "normal"},
    ],
    "groups": [
        {"node_id": "oracle::primary", "group_name": "Primary", "children_id": ["1.1.1.12:1234"]},
        {"node_id": "oracle::standby", "group_name": "Standby", "children_id": ["1.1.1.11:1235"]},
        {"node_id": "slave_bind_entry_group", "group_name": "", "children_id": ["xxxx.1xx.cf.db"]},
    ],
    "lines": [
        {
            "source": "1.1.1.12:1234",
            "source_type": "node",
            "target": "1.1.1.11:1235",
            "target_type": "node",
            "label": "rep",
            "label_name": "",
        },
        {
            "source": "slave_bind_entry_group",
            "source_type": "group",
            "target": "oracle::standby",
            "target_type": "group",
            "label": "bind",
            "label_name": "bind",
        },
    ],
    "foreign_relations": {"rep_to": [], "rep_from": [], "access_to": [], "access_from": []},
}


class PaginatedResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example}
        ref_name = f"{REF_NAME}_PaginatedResourceSLZ"


class ResourceFieldSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ListRetrieveResource.get_fields()}
        ref_name = f"{REF_NAME}_ResourceFieldSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"


class ResourceTopoGraphSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": resource_topo_graph_example}
        ref_name = f"{REF_NAME}_ResourceTopoGraphSLZ"
