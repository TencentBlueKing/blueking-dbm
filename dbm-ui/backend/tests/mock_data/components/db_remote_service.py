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


class DbRemoteServiceApiMock(object):
    """remote-service相关接口的mock"""

    @classmethod
    def rpc(cls, *args, **kwargs):
        # 可根据不同入参，mock不同的返回
        params = args[0]
        addresses = params["addresses"]
        results = [
            {
                "address": addresses[0],
                "cmd_results": [
                    {
                        "cmd": "show databases",
                        "table_data": [{"Database": "db1"}, {"Database": "db2"}],
                        "rows_affected": 0,
                        "error_msg": "",
                    }
                ],
                "error_msg": "",
            }
        ]
        if len(addresses) > 1:
            # 添加一个带错误的返回
            err_return_address = addresses[1]
            results.append(
                {
                    "address": err_return_address,
                    "cmd_results": None,
                    "error_msg": f"connect to {err_return_address} failed: dial tcp {err_return_address}: i/o timeout",
                }
            )
        return results
