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
    "SELECT m.bk_host_id, m.bk_cloud_id, m.ip, m.spec_config, c.cluster_id, i.instance_role as role, "
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

SQL_QUERY_MASTER_SLAVE_STATUS = (
    "select mim.ip as ip, "
    "count(si.id) as total_slave, "
    "count(mi.id) as total_master, "
    "sum(case when si.status='running' then 1 else 0 end) as running_slave, "
    "sum(case when si.status='unavailable' then 1 else 0 end) as unavailable_slave, "
    "sum(case when mi.status='running' then 1 else 0 end) as running_master, "
    "sum(case when mi.status='unavailable' then 1 else 0 end) as unavailable_master "
    "from db_meta_storageinstancetuple t "
    "left join db_meta_storageinstance mi on mi.id = t.ejector "
    "left join db_meta_storageinstance si on si.id = t.receiver "
    "left join db_meta_machine mim on mim.bk_host_id = mi.machine_id "
    "left join db_meta_machine sim on sim.bk_host_id = si.machine_id "
    "{where} "
    "group by mim.ip"
)
