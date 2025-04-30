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


from backend.db_meta.enums.cluster_type import ClusterType
from backend.tests.mock_data import constant

BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID
CLUSTER_ID = 91


# es 部署集群
ES_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "default",
        "cluster_alias": "",
        "cluster_name": "testes",
        "db_app_abbr": "1",
        "db_version": "7.2.0",
        "disaster_tolerance_level": "MAX_EACH_ZONE_EQUAL",
        "http_port": 9200,
        "ip_source": "resource_pool",
        "resource_spec": {
            "master": {
                "count": 3,
                "spec_id": 391,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_72"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
            "hot": {
                "count": 1,
                "spec_id": 393,
                "cpu": {"max": 256, "min": 1},
                "instance_num": 1,
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_117"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
        },
        "city_name": "无限制",
    },
    "remark": "",
    "ticket_type": "ES_APPLY",
}

# es 集群扩容
ES_SCALE_UP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "cluster_id": CLUSTER_ID,
        "ext_info": {
            "client": {"expansion_disk": 0, "total_disk": 0, "total_hosts": 0},
            "cold": {"expansion_disk": 10, "total_disk": None, "total_hosts": 1},
            "hot": {"expansion_disk": 0, "total_disk": None, "total_hosts": 1},
        },
        "ip_source": "resource_pool",
        "resource_spec": {"cold": {"count": 1, "instance_num": 1, "spec_id": 393}},
    },
    "ticket_type": "ES_SCALE_UP",
}

# es 集群缩容
ES_SHRINK_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "cluster_id": CLUSTER_ID,
        "ext_info": {
            "client": {"shrink_disk": 0, "total_disk": 0, "total_hosts": 0},
            "cold": {"shrink_disk": 0, "total_disk": 0, "total_hosts": 1},
            "hot": {"shrink_disk": 0, "total_disk": 0, "total_hosts": 1},
        },
        "ip_source": "resource_pool",
        "old_nodes": {"client": [], "cold": [{"bk_cloud_id": 0, "bk_host_id": 56, "ip": "1.1.1.2"}], "hot": []},
    },
    "ticket_type": "ES_SHRINK",
}

# es 集群禁用
ES_DISABLE_DATA = {"bk_biz_id": BK_BIZ_ID, "details": {"cluster_id": CLUSTER_ID}, "ticket_type": "ES_DISABLE"}

ES_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2023-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2023-03-13 11:14:48.433116",
        "ip": "1.1.3.4",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": "es_datanode",
        "cluster_type": ClusterType.Es,
        "bk_host_id": 55,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 393, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, "qps": {}, '
        '"name": "1核_1G_10G", "count": 1, "device_class": [], '
        '"storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 393,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "1.1.1.2",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": "es_datanode",
        "cluster_type": ClusterType.Es,
        "bk_host_id": 56,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 393, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, "qps": {}, '
        '"name": "1核_1G_10G", "count": 1, "device_class": [], '
        '"storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 393,
        "bk_agent_id": "",
    },
]

ES_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "randpass",
    "alias": "randpass",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.Es,
    "db_module_id": 0,
    "immute_domain": "es.randpass.dba.db",
    "major_version": "7.10.2",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}

ES_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 391,
        "spec_name": "1核_1G_10G",
        "spec_cluster_type": "es",
        "spec_machine_type": "es_master",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "12",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-15 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-15 11:14:48.433116",
        "spec_id": 393,
        "spec_name": "1核_1G_10G",
        "spec_cluster_type": "es",
        "spec_machine_type": "es_datanode",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "es_datanode",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
]

ES_STORAGE_INSTANCE = [
    {
        "id": 4,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "",
        "port": 9200,
        "machine_id": 55,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "es_datanode",
        "instance_role": "es_datanode_hot",
        "instance_inner_role": "orphan",
        "cluster_type": "es",
        "status": "running",
        "phase": "online",
        "name": "dn-1.1.2.2_1",
        "time_zone": "+08:00",
        "bk_instance_id": 0,
        "is_stand_by": "1",
    },
    {
        "id": 5,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "",
        "port": 9200,
        "machine_id": 56,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "es_datanode",
        "instance_role": "es_datanode_cold",
        "instance_inner_role": "orphan",
        "cluster_type": "es",
        "status": "running",
        "phase": "online",
        "name": "cold-1.1.3.3_1",
        "time_zone": "+08:00",
        "bk_instance_id": 5883,
        "is_stand_by": "1",
    },
]
