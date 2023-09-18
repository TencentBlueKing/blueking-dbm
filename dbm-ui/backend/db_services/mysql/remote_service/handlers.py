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
from collections import defaultdict
from itertools import chain
from typing import Dict, List, Union

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.flow.consts import SYSTEM_DBS


class RemoteServiceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def show_databases(self, cluster_ids: List[int]) -> List[Dict[str, Union[int, List[str]]]]:
        """批量查询集群的数据库列表"""

        # 如果集群列表为空，则提前返回
        if not cluster_ids:
            return []

        cloud_addresses = defaultdict(list)
        cluster_databases = []
        address_cluster_id_map = defaultdict(dict)
        cluster_ids = list(set(cluster_ids))

        # 查询各个集群可执行的实例地址
        for cluster_id in cluster_ids:
            cluster_handler = ClusterHandler.get_exact_handler(bk_biz_id=self.bk_biz_id, cluster_id=cluster_id)
            inst = cluster_handler.get_exec_inst()
            bk_cloud_id = cluster_handler.cluster.bk_cloud_id
            address = f"{inst.machine.ip}{IP_PORT_DIVIDER}{inst.port}"
            cloud_addresses[bk_cloud_id].append(f"{inst.machine.ip}{IP_PORT_DIVIDER}{inst.port}")
            address_cluster_id_map[bk_cloud_id][address] = cluster_id

        # 批量查询实例地址对应的数据库列表
        for bk_cloud_id in cloud_addresses.keys():
            rpc_results = DRSApi.rpc(
                {"bk_cloud_id": bk_cloud_id, "addresses": cloud_addresses[bk_cloud_id], "cmds": ["show databases"]}
            )
            for rpc_result in rpc_results:
                cmd_results = rpc_result["cmd_results"] or [{}]
                cluster_databases.append(
                    {
                        "cluster_id": address_cluster_id_map[bk_cloud_id][rpc_result["address"]],
                        "databases": [
                            data["Database"]
                            for data in cmd_results[0].get("table_data", [])
                            if data["Database"] not in SYSTEM_DBS
                        ],
                        "system_databases": SYSTEM_DBS,
                    }
                )
        return cluster_databases

    def check_cluster_database(self, cluster_ids: List[int], db_names: List[str]) -> Dict[str, Dict]:
        """
        批量校验集群下的DB是否存在
        [
            {
                "address": "127.0.0.1",
                "cmd_results": [
                    {
                        "cmd": "select schema_name as db_name from information_schema.schemata
                        where schema_name in ('test','sys','bk-dbm-test')",
                        "table_data": [{"db_name": "sys"},{"db_name": "test"}],
                        "rows_affected": 0,
                        "error_msg": ""
                    }
                ],
                "error_msg": ""
            }
        ]
        """

        master_inst__cluster_map: Dict[str, int] = {}
        for cluster_id in cluster_ids:
            cluster_handler = ClusterHandler.get_exact_handler(bk_biz_id=self.bk_biz_id, cluster_id=cluster_id)
            master_inst__cluster_map[cluster_handler.get_exec_inst().ip_port] = cluster_id

        raw_db_names = [f"'{db_name}'" for db_name in db_names]
        rpc_results = DRSApi.rpc(
            {
                "addresses": list(master_inst__cluster_map.keys()),
                "cmds": [
                    f"select schema_name as db_name "
                    f"from information_schema.schemata where schema_name in ({','.join(raw_db_names)});"
                ],
            }
        )

        # 获取每个集群包含的校验DB列表
        cluster_check_info: Dict[int, List[str]] = {}
        for result in rpc_results:
            cluster_check_info[master_inst__cluster_map[result["address"]]] = [
                db["db_name"] for db in result["cmd_results"][0]["table_data"]
            ]

        # 校验DB是否在集群中出现。
        # 这里的判断逻辑是只要DB在校验集群的其中一个出现，就判定为合法
        db_exist_list = set(chain(*list(cluster_check_info.values())))
        db_check_info = {db_name: (db_name in db_exist_list and db_name not in SYSTEM_DBS) for db_name in db_names}

        return {"cluster_check_info": cluster_check_info, "db_check_info": db_check_info}
