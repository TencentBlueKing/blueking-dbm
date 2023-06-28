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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from .query import ListRetrieveResource

REF_NAME = "dbha"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "cluster_name": "bk-dbm",
            "master_domain": "gamedb.bk-dbm.blueking.db",
            "proxies": ["0.0.0.1#10000", "0.0.0.2#10000"],
            "masters": ["0.0.0.3#30000"],
            "slaves": ["0.0.0.4#30000"],
            "...": "...",
        }
    ],
}

resource_topo_graph_example = {
    "node_id": "module-name-db.ha-test2.blueking.db",
    "nodes": [
        {"node_id": "master_ip#port", "node_type": "backend::backend_master"},
        {"node_id": "slave_ip#port", "node_type": "backend::backend_slave"},
        {"node_id": "module-name-dr.ha-test2.blueking.db", "node_type": "entry_dns"},
        {"node_id": "proxy1#port", "node_type": "proxy"},
        {"node_id": "module-name-db.ha-test2.blueking.db", "node_type": "entry_dns"},
        {"node_id": "proxy2#port", "node_type": "proxy"},
    ],
    "groups": [
        {"node_id": "backend::backend_master", "children_id": ["master_ip#port"]},
        {"node_id": "backend::backend_slave", "children_id": ["slave_ip#port"]},
        {
            "node_id": "entry_dns",
            "children_id": ["module-name-dr.ha-test2.blueking.db", "module-name-db.ha-test2.blueking.db"],
        },
        {"node_id": "proxy", "children_id": ["proxy1#port", "proxy2#port"]},
    ],
    "lines": [
        {
            "source": "master_ip#port",
            "source_type": "node",
            "target": "slave_ip#port",
            "target_type": "node",
            "label": "rep",
        },
        {
            "source": "module-name-dr.ha-test2.blueking.db",
            "source_type": "node",
            "target": "slave_ip#port",
            "target_type": "node",
            "label": "bind",
        },
        {
            "source": "proxy",
            "source_type": "group",
            "target": "backend::backend_master",
            "target_type": "group",
            "label": "access",
        },
        {
            "source": "module-name-db.ha-test2.blueking.db",
            "source_type": "node",
            "target": "proxy",
            "target_type": "group",
            "label": "bind",
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
