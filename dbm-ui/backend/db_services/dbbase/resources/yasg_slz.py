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

paginated_machine_resource_example = {
    "count": 1,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "bk_host_id": 247,
            "ip": "127.0.0.1",
            "bk_cloud_id": 0,
            "bk_cloud_name": "cloud area",
            "cluster_type": "tendbcluster",
            "machine_type": "spider",
            "instance_role": "proxy",
            "create_at": "2023-12-04T14:53:29+08:00",
            "spec_id": 243,
            "spec_config": {
                "id": 243,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {"max": 111111, "min": 1},
                "name": "test spec",
                "count": 1,
                "device_class": [],
                "storage_spec": [],
            },
            "host_info": {
                "meta": {"scope_type": "biz", "scope_id": "3", "bk_biz_id": 3},
                "host_id": 247,
                "ip": "127.0.0.1",
                "ipv6": "",
                "bk_host_outerip": "",
                "cloud_id": 0,
                "cloud_vendor": None,
                "agent_id": "",
                "host_name": "VM-79-7-xxxx",
                "os_name": "linux centos",
                "os_type": "1",
                "alive": 1,
                "cloud_area": {"id": 0, "name": "Default Area"},
                "biz": {"id": 3, "name": "DBA"},
                "bk_mem": 7696,
                "bk_disk": 196,
                "bk_cpu": 2,
                "bk_idc_name": None,
                "bk_idc_id": None,
                "bk_cpu_architecture": "x86",
                "bk_cpu_module": "Intel(R) Xeon(R) Platinum xxxx",
            },
        },
    ],
}


class ResourceTreeSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "db_module_id": 0,
                    "db_module_name": "default",
                    "children": [
                        {"cluster_id": 1, "cluster_name": "db", "master_domain": "dbhadb.dbha111.blueking.db"}
                    ],
                }
            ]
        }
