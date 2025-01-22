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
import copy

from backend.tests.mock_data.constant import BK_BIZ_ID
from backend.tests.mock_data.utils import raw_response

MACHINE_RESOURCE_DATA = {
    "ip": "1.1.1.1",
    "city": "sh",
    "cpu_num": 2,
    "dram_cap": 3597,
    "total_storage_cap": 147,
    "rack_id": "68123",
    "sub_zone": "sh-qp",
    "bk_biz_id": BK_BIZ_ID,
    "bk_host_id": 0,
    "bk_cloud_id": 0,
    "sub_zone_id": "141",
    "device_class": "SA5.MEDIUM4",
    "storage_device": {
        "/data": {"size": 50, "disk_id": "disk-ofkfne6j", "disk_type": "HDD", "file_type": "ext4"},
        "/data1": {"size": 50, "disk_id": "disk-ofkfne6j", "disk_type": "SSD", "file_type": "ext4"},
    },
}


class DBResourceApiMock(object):
    """Gcs的mock类"""

    @classmethod
    @raw_response
    def resource_pre_apply(cls, params, *args, **kwargs):
        resource_data, start_host_id = [], 100
        for apply_detail in params["details"]:
            machines = []
            # 按照分组生成对应的machine
            for index in range(1, apply_detail["count"] + 1):
                machine = copy.deepcopy(MACHINE_RESOURCE_DATA)
                host_id = start_host_id + index
                machine["bk_biz_id"] = params["for_biz_id"]
                machine["bk_host_id"] = host_id
                machine["ip"] = f"1.1.1.{host_id}"
                machines.append(machine)
            # 获取一组资源信息
            resource_data.append({"item": apply_detail["group_mark"], "data": machines})

        return resource_data

    @classmethod
    def resource_confirm(cls, params):
        return True
