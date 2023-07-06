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
RESOURCE_TAG = "db_services/resources/redis"

SQL_QUERY_STORAGE_INSTANCES = (
    "SELECT m.bk_host_id, m.bk_cloud_id, m.ip, m.spec_config, c.cluster_id, i.instance_inner_role as role, "
    "count(port) AS instance_count FROM db_meta_storageinstance i "
    "LEFT JOIN db_meta_machine m ON i.machine_id = m.bk_host_id "
    "LEFT JOIN db_meta_storageinstance_cluster c ON i.id = c.storageinstance_id "
    "{where} "
    "GROUP BY ip, role, bk_host_id, bk_cloud_id, cluster_id "
    "{having}"
)

SQL_QUERY_PROXY_INSTANCES = (
    "SELECT m.bk_host_id, m.bk_cloud_id, m.ip, m.spec_config, c.cluster_id, 'proxy' as role, "
    "count(port) AS instance_count FROM db_meta_proxyinstance i "
    "LEFT JOIN db_meta_machine m ON i.machine_id = m.bk_host_id "
    "LEFT JOIN db_meta_proxyinstance_cluster c ON i.id = c.proxyinstance_id "
    "{where} "
    "GROUP BY ip, role, bk_host_id, bk_cloud_id, cluster_id "
    "{having}"
)

SQL_QUERY_INSTANCES = f"({SQL_QUERY_STORAGE_INSTANCES}) UNION ({SQL_QUERY_PROXY_INSTANCES}) " + " {limit} {offset}"
