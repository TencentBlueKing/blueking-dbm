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
from typing import Dict, List, Union

from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.consts import SQLSERVER_SYSTEM_DBS


class RemoteSqlserverServiceHandler(RemoteServiceHandler):
    def show_databases(
        self, cluster_ids: List[int], cluster_id__role_map: Dict[int, str] = None
    ) -> List[Dict[str, Union[int, List[str]]]]:
        """
        批量查询集群的数据库列表
        @param cluster_ids: 集群ID列表
        @param cluster_id__role_map: (可选)集群ID和对应查询库表角色的映射表
        """
        # 如果集群列表为空，则提前返回
        if not cluster_ids:
            return []

        cluster_id__role_map = cluster_id__role_map or {}
        cloud_addresses = defaultdict(list)
        cluster_databases = []
        address_cluster_id_map = defaultdict(dict)
        cluster_ids = list(set(cluster_ids))

        # 查询各个集群可执行的实例地址
        for cluster_id in cluster_ids:
            cluster_handler, address = self._get_cluster_address(cluster_id__role_map, cluster_id)
            bk_cloud_id = cluster_handler.cluster.bk_cloud_id
            cloud_addresses[bk_cloud_id].append(address)
            address_cluster_id_map[bk_cloud_id][address] = cluster_id

        # 批量查询实例地址对应的数据库列表
        for bk_cloud_id in cloud_addresses.keys():
            rpc_results = DRSApi.sqlserver_rpc(
                {
                    "bk_cloud_id": bk_cloud_id,
                    "addresses": cloud_addresses[bk_cloud_id],
                    "cmds": ["select name from master.sys.databases;"],
                }
            )

            if rpc_results[0]["error_msg"]:
                raise RemoteServiceBaseException(_("DRS调用失败，错误信息: {}").format(rpc_results[0]["error_msg"]))

            for rpc_result in rpc_results:
                cmd_results = rpc_result["cmd_results"] or [{}]
                cluster_databases.append(
                    {
                        "cluster_id": address_cluster_id_map[bk_cloud_id][rpc_result["address"]],
                        "databases": [
                            data["name"]
                            for data in cmd_results[0].get("table_data", [])
                            if data["name"] not in SQLSERVER_SYSTEM_DBS
                        ],
                        "system_databases": SQLSERVER_SYSTEM_DBS,
                    }
                )
        return cluster_databases
