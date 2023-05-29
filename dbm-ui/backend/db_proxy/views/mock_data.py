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
# db meta相关mock data
INSTANCE_DATA_RESPONSE = {
    "data": [
        {
            "bk_idc_city_id": 0,
            "bk_idc_city_name": "shenzhen",
            "logical_city_id": 3,
            "logical_city_name": "shenzhen",
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
            "port": 20000,
            "ip": "127.0.0.1",
            "db_module_id": 507,
            "bk_biz_id": 2005000194,
            "cluster": "testdb.admin.dba.db",
            "access_layer": "storage",
            "machine_type": "backend",
            "instance_role": "backend_slave",
            "instance_inner_role": "slave",
            "cluster_type": "tendbha",
            "status": "running",
            "receiver": [],
            "ejector": [{"ip": "127.0.0.1", "port": 20000}],
            "bind_entry": {"dns": ["testdr.admin.dba.db"]},
            "proxyinstance_set": [],
        },
    ]
}

# dbconfig相关mock data
QUERY_CONF_ITEM_DATA_RESPONSE = [
    {
        "bk_biz_id": "string",
        "conf_file": "MySQL-5.7",
        "conf_file_lc": "5.7_conf",
        "conf_type": "dbconf",
        "conf_type_lc": "DBconf",
        "content": {"additionalProp1": {}},
        "created_at": "string",
        "description": "string",
        "level_name": "cluster",
        "level_value": "string",
        "namespace": "tendbha",
        "namespace_info": "MySQL 5.7",
        "updated_at": "string",
        "updated_by": "string",
    }
]

BATCH_GET_DATA_RESPONSE = {
    "conf_file": "MySQL-5.7",
    "conf_name": "requirepass",
    "conf_type": "dbconf",
    "content": {
        "additionalProp1": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"},
        "additionalProp2": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"},
        "additionalProp3": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"},
    },
    "level_name": "instance",
    "namespace": "tendbha",
}

# gcs dns相关mock data
GET_ALL_DOMAIN_LIST_DATA_RESPONSE = {
    "detail": [
        {"domain_name": "test.1.1.1.db.", "ip": "127.0.0.1"},
        {"domain_name": "test.3.3.3.db.", "ip": "4.4.4.4"},
        {"domain_name": "test.3.3.3.db.", "ip": "4.4.4.5"},
        {"domain_name": "test.3.3.4.db.", "ip": "2.2.2.2"},
    ],
    "rowsNum": 4,
}

GET_DOMAIN_DATA_RESPONSE = {
    "detail": [
        {
            "app": "redistest",
            "dns_str": "",
            "domain_name": "test.domain.db.",
            "domain_type": 0,
            "ip": "2.2.2.2",
            "last_change_time": "2021-06-02T20:19:16+08:00",
            "manager": "DBA",
            "port": 0,
            "remark": "",
            "start_time": "2021-06-02T20:19:16+08:00",
            "status": "1",
            "uid": 217176,
        }
    ],
    "rowsNum": 1,
}

DELETE_DOMAIN_DATA_RESPONSE = {"rowsAffected": 3}

BATCH_DELETE_DOMAIN_DATA_RESPONSE = {"rowsAffected": 3}

POST_DOMAIN_DATA_RESPONSE = {"rowsAffected": 3}

PUT_DOMAIN_DATA_RESPONSE = {"rowsAffected": 3}

# jobapi相关mock data
JOB_API_FAST_EXECUTE_SCRIPT_DATA_RESPONSE = {
    "job_instance_id": 000000,
    "job_instance_name": "test_ls",
    "step_instance_id": 111111,
}

JOB_API_GET_JOB_INSTANCE_STATUS_DATA_RESPONSE = {
    "job_instance": {
        "bk_biz_id": 1111,
        "job_instance_id": 000000,
        "name": "test_ls",
        "bk_scope_type": "biz",
        "start_time": 1684487083852,
        "bk_scope_id": "2005000194",
        "create_time": 1684487083752,
        "status": 3,
        "end_time": 1684487085090,
        "total_time": 1238,
    },
    "finished": True,
    "step_instance_list": [
        {
            "status": 3,
            "total_time": 1201,
            "name": "test_ls",
            "start_time": 1684487083875,
            "step_instance_id": 20003693380,
            "step_ip_result_list": [
                {
                    "status": 9,
                    "total_time": 308,
                    "ip": "1.1.1.1",
                    "start_time": 1684487084023,
                    "bk_host_id": 1111111,
                    "exit_code": 0,
                    "bk_cloud_id": 0,
                    "tag": "",
                    "end_time": 1684487084331,
                    "error_code": 0,
                },
                {
                    "status": 9,
                    "total_time": 388,
                    "ip": "2.2.2.2",
                    "start_time": 1684487084026,
                    "bk_host_id": 22222222,
                    "exit_code": 0,
                    "bk_cloud_id": 0,
                    "tag": "",
                    "end_time": 1684487084414,
                    "error_code": 0,
                },
            ],
            "create_time": 1684487083752,
            "end_time": 1684487085076,
            "execute_count": 0,
            "type": 1,
        }
    ],
}

JOB_API_GET_JOB_INSTANCE_IP_LOG_DATA_RESPONSE = {
    "job_instance_id": 000000,
    "file_task_logs": None,
    "script_task_logs": [
        {"host_id": 2000059954, "ipv6": None, "log_content": "xxxxx\n", "bk_cloud_id": 0, "ip": "1.1.1.1"},
        {"host_id": 2000059953, "ipv6": None, "log_content": "yyyyy\n", "bk_cloud_id": 0, "ip": "2.2.2.2"},
    ],
    "step_instance_id": 20003693380,
    "log_type": 1,
}

TRANSFER_FILE_DATA_RESPONSE = {
    "code": 0,
    "job_request_id": "07ab3b72d80c9cb0294485a54aeb41c9",
    "result": True,
    "request_id": "01ae87e2-f879-499d-b6ea-a9e4601de6f5",
    "message": "",
    "data": {
        "job_instance_id": 000000,
        "job_instance_name": "fast_transfer_file_task_20230520105153641",
        "step_instance_id": 11111,
    },
}
