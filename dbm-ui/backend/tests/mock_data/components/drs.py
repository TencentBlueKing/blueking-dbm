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
                    {
                        "cmd": args[0]["cmds"][0],
                        "table_data": [
                            {"Database": "source_test_db1", "SCHEMA_NAME": "test_table", "TABLE_NAME": "test_table"}
                        ],
                        "rows_affected": 0,
                        "error_msg": "",
                    },
                ],
                "error_msg": "",
            },
            {
                "address": "5.5.5.4:20001",
                "cmd_results": [
                    {
                        "cmd": args[0]["cmds"][0],
                        "table_data": [
                            {"Database": "test_db1", "SCHEMA_NAME": "test_table", "TABLE_NAME": "test_table"}
                        ],
                        "rows_affected": 0,
                        "error_msg": "",
                    },
                ],
                "error_msg": "",
            },
        ]
        response_data = []

        for address in args[0]["addresses"]:
            for data in source_data:
                if address == data.get("address"):
                    if len(args[0]["cmds"]) > 1:
                        data["cmd_results"].append(
                            {
                                "cmd": args[0]["cmds"][1],
                                "table_data": [{"Database": "", "SCHEMA_NAME": "", "TABLE_NAME": ""}],
                                "rows_affected": 0,
                                "error_msg": "",
                            }
                        )
                    response_data.append(data)
        return response_data

    @classmethod
    def sqlserver_rpc(cls, *args, **kwargs):
        """
        SQLServer DRS 接口模拟
        根据不同的 SQL 命令返回不同的模拟数据
        """
        cmds = args[0].get("cmds", [])
        addresses = args[0].get("addresses", [])

        response_data = []
        for address in addresses:
            cmd_results = []
            for cmd in cmds:
                # 模拟获取数据库列表的查询
                if "select name from [master].[sys].[databases]" in cmd:
                    # 返回源集群和目标集群的数据库列表
                    if "2.2.2.1" in address or "2.2.2.2" in address:
                        # 源集群 (CLUSTER_ID=101) 的数据库
                        table_data = [
                            {"name": "test_database"},
                            {"name": "test_db2"},
                            {"name": "master"},
                            {"name": "model"},
                            {"name": "msdb"},
                            {"name": "tempdb"},
                        ]
                    elif "2.2.2.3" in address or "3.2.2" in address:
                        # 目标集群 (CLUSTER_ID=102) 的数据库
                        table_data = [
                            {"name": "existing_db"},
                            {"name": "master"},
                            {"name": "model"},
                            {"name": "msdb"},
                            {"name": "tempdb"},
                        ]
                    else:
                        table_data = [{"name": "test_database"}]
                # 模拟检查数据库是否存在的查询
                elif "select name from [master].[sys].[databases] where name in" in cmd:
                    # 返回已存在的数据库
                    table_data = [{"name": "existing_db"}]
                # 模拟获取集群主节点的查询
                elif "SELECT SERVERPROPERTY('MachineName')" in cmd:
                    table_data = [{"MachineName": address.split(":")[0]}]
                else:
                    table_data = []

                cmd_results.append(
                    {
                        "cmd": cmd,
                        "table_data": table_data,
                        "rows_affected": len(table_data),
                        "error_msg": "",
                    }
                )

            response_data.append(
                {
                    "address": address,
                    "cmd_results": cmd_results,
                    "error_msg": "",
                }
            )

        return response_data
