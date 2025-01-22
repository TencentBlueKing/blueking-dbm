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

from backend.db_meta.enums import MachineType
from backend.db_meta.enums.spec import SpecClusterType

BK_BIZ_ID = 2005000002
BK_SET_ID = 1
BK_MODULE_ID = 11
BK_MODULE_ID2 = 22
DB_MODULE_ID = 111
CLUSTER_NAME = "fake_cluster"
CLUSTER_IMMUTE_DOMAIN = "fake.db.com"

TICKET_TYPE = "MYSQL_SINGLE_APPLY"
DB_TYPE = "mysql"
TICKET_STATUS = "PENDING"
TASK_UID = 1
TASK_ROOT_ID = "202304250963aa"
TASK_STATUS = "FINISHED"
INSTANCE_VERSION = "latest"
INSTANCE_PORT = 8000
INSTANCE_NAME = "zookeeper"

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
INIT_MACHINE_DATA = {
    # "ip": "1.1.1.4",
    # "bk_host_id": 1,
    "creator": "admin",
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
    "bk_biz_id": BK_BIZ_ID,
    "db_module_id": 0,
    "access_layer": "",
    "machine_type": "",
    "cluster_type": "",
    "bk_os_name": "",
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
    "spec_config": '{"id": 440, "cpu": {"max": 4, "min": 2}, "mem": {"max": 8, "min": 4}, '
    '"qps": {"max": 0, "min": 0}, "name": "1核_4G_20G", "count": 1, "device_class": [], '
    '"storage_spec": [{"size": 20, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
    ' {"size": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
    "spec_id": 3,
    "bk_agent_id": "",
}
