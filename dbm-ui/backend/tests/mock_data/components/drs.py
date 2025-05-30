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


class DRSApiMock(object):
    """
    Drs 相关接口的mock
    """

    @classmethod
    def rpc(cls, *args, **kwargs):
        source_data = [
            {
                "address": "5.5.5.5:20001",
                "cmd_results": [
                    {"cmd": "", "table_data": [{"Database": "source_test_db1"}], "rows_affected": 0, "error_msg": ""}
                ],
                "error_msg": "",
            },
            {
                "address": "5.5.5.4:20001",
                "cmd_results": [
                    {"cmd": "", "table_data": [{"Database": "test_db1"}], "rows_affected": 0, "error_msg": ""}
                ],
                "error_msg": "",
            },
        ]
        response_data = []

        for address in args[0]["addresses"]:
            for data in source_data:
                if address == data.get("address"):
                    response_data.append(data)
        return response_data

    @classmethod
    def sqlserver_rpc(cls, *args, **kwargs):
        response_data = [
            {
                "address": "2.2.2.1:10000",
                "cmd_results": [
                    {"cmd": "", "table_data": [{"name": "test_database"}], "rows_affected": 0, "error_msg": ""}
                ],
                "error_msg": "",
            }
        ]
        return response_data
