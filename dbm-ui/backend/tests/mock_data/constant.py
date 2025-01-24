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

from collections import namedtuple

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta.enums import AccessLayer, InstancePhase, InstanceStatus, MachineType
from backend.db_meta.enums.spec import SpecClusterType

# 全局cc信息
BK_BIZ_ID = 2005000002
BK_SET_ID = 1
BK_MODULE_ID = 11
BK_MODULE_ID2 = 22

# 全局模块ID
DB_MODULE_ID = 111

CLUSTER_NAME = "fake_cluster"
CLUSTER_IMMUTE_DOMAIN = "fake.db.com"

INIT_MYSQL_CLUSTER_NAME = "fake_mysql_cluster"

Response = namedtuple("Response", ["data", "message", "code"])

# 初始化规格数据
INIT_SPEC_DATA = {
    # "spec_id": 1,
    # "spec_name": "spec_test",
    "cpu": {"max": 1024, "min": 1},
    "mem": {"max": 1024, "min": 1},
    "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
    "spec_cluster_type": SpecClusterType.MySQL.value,
    "spec_machine_type": MachineType.BACKEND.value,
    "device_class": [-1],
    "qps": {"max": 0, "min": 0},
    "enable": 1,
}

# 初始化machine数据
INIT_CC_MACHINE_DATA = {
    # "ip": "1.1.1.4",
    # "bk_host_id": 1,
    # "bk_host_innerip": "",
    "bk_idc_area": "hd",
    "bk_idc_area_id": 5,
    "bk_os_name": "linux release 1.2 (Final)",
    "bk_svr_device_cls_name": "D2-4-50-10",
    "idc_city_id": 1,
    "idc_city_name": "sh",
    "idc_id": 826,
    "idc_name": "sh-dc",
    "rack": "2F-S16",
    "rack_id": "104599",
    "sub_zone": "sh-dc",
    "sub_zone_id": "154",
    "bk_cloud_id": 0,
}

# 初始化实例信息
INIT_STORAGE_INSTANCE_DATA = {
    "creator": "admin",
    "updater": "admin",
    "version": "test_version",
    "port": 10000,
    "db_module_id": DB_MODULE_ID,
    "bk_biz_id": BK_BIZ_ID,
    "status": InstanceStatus.RUNNING.value,
    "name": "test_storage_instance",
    "time_zone": "+08:00",
    "bk_instance_id": 7089,
    "phase": InstancePhase.ONLINE.value,
    "machine_type": "",
    "cluster_type": "",
    "machine_id": "",
    "instance_role": "",
    "instance_inner_role": "",
}

INIT_PROXY_INSTANCE_DATA = {
    "creator": "admin",
    "updater": "admin",
    "version": "test_version",
    "port": 10000,
    "db_module_id": DB_MODULE_ID,
    "bk_biz_id": BK_BIZ_ID,
    "access_layer": AccessLayer.PROXY.value,
    "status": InstanceStatus.RUNNING.value,
    "name": "test_proxy_instance",
    "time_zone": "+08:00",
    "bk_instance_id": 7090,
    "phase": InstancePhase.ONLINE.value,
    "machine_type": "",
    "cluster_type": "",
    "machine_id": "",
}

INIT_TENDBHA_CREATE_API_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "db_module_id": DB_MODULE_ID,
    "creator": "admin",
    "major_version": "latest",
    "time_zone": DEFAULT_TIME_ZONE,
    "bk_cloud_id": 0,
    "resource_spec": {MachineType.BACKEND.value: {"id": 0}, MachineType.PROXY.value: {"id": 0}},
    "region": "",
    "disaster_tolerance_level": "NONE",
}
