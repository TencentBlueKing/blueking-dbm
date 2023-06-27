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

MYSQL_SINGLE_APPLY_GLOBAL_DATA = {
    "uid": 1,
    "city": "上海",
    "spec": "SA2.SMALL1",
    "module": "1",
    "charset": "utf8",
    "domains": [{"key": "kkksc"}],
    "inst_num": 1,
    "bk_biz_id": 2005000002,
    "city_code": "上海",
    "ip_source": "resource_pool",
    "created_by": "admin",
    "db_version": "MySQL-5.7",
    "ticket_type": "MYSQL_SINGLE_APPLY",
    "db_module_id": 1,
    "cluster_count": 1,
    "start_mysql_port": 20000,
    "mysql_ports": [20000],
    "clusters": [{"name": "kkksc", "master": "blueking-moduledb.kkksc.blueking.db", "mysql_port": 20000}],
    "bk_cloud_id": 0,
    "resource_spec": {"backend": {"id": 1}, "proxy": {"id": 1}},
}

RESOURCE_POLL_NODES = [
    {
        "item": "mysql",
        "data": [
            {
                "id": 20728,
                "apply_for": "MySQL",
                "ip": "127.0.0.1",
                "asset_id": "TC220620001891",
                "label": "{}",
                "labels": None,
                "device_class": "S5t.SMALL2",
                "cpu_num": 1,
                "dram_cap": 1000,
                "ssd_cap": 0,
                "hdd_cap": 100,
                "raid": "NORAID",
                "city": "上海",
                "campus": "上海-奉贤",
                "campus_id": 217,
                "idc": "上海电信奉贤DC",
                "idc_id": 1935,
                "equipment": 488573,
                "link_netdevice_id": "831836,831832,831834",
                "is_selled": 2,
                "update_time": "2022-10-08T16:33:41+08:00",
                "create_time": "2022-07-27T15:06:33+08:00",
            }
        ],
    }
]

SERVICE_RUNTIME_ATTRS = {
    "id": "e3f5eeb4d0ec7481b9245fbdd28b8efb1",
    "version": "vde74f5a43b9c4bb382dbf8bae46e6884",
    "top_pipeline_id": "",
    "root_pipeline_id": "",
    "loop": 1,
    "inner_loop": 1,
    "logger": None,
}
