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
from typing import Dict, List, Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.api.cluster.nosqlcomm.decommission import decommission_cluster
from backend.db_meta.api.cluster.nosqlcomm.scale_proxy import add_proxies, delete_proxies
from backend.db_meta.enums import ClusterType

from .create import pkg_create_mongo_cluster
from .detail import scan_cluster


class MongoClusterHandler(ClusterHandler):
    """
    MongoDB 分片集群（Sharded Cluster）架构在副本集的基础上，通过多组复制集群的组合，实现数据的横向扩展。
    每一个分片集群实例由 mongos 节点、config server、shard 节点等组件组成。
    1. mongos 节点：负责接收所有客户端应用程序的连接查询请求，并将请求路由到集群内部对应的分片上，同时会把接收到的响应拼装起来返回到客户端。
    2. config server 节点：负责存储集群和 Shard 节点的元数据信息，如集群的节点信息、分片数据的路由信息等。
    3. shard 节点：负责将数据分片存储在多个服务器上。 通过多个 Shard 节点来横向扩展实例的数据存储和读写并发能力。
    """

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        name: str,
        immute_domain: str,
        db_module_id: int,
        alias: str = "",
        major_version: str = "",
        proxies: Optional[List] = None,
        storages: Optional[List] = None,
        creator: str = "",
        bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
        region: str = "",
    ):
        """「必须」创建集群"""
        pkg_create_mongo_cluster(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            db_module_id=db_module_id,
            alias=alias,
            major_version=major_version,
            proxies=proxies,
            storages=storages,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            cluster_type=ClusterType.MongoShardedCluster.value,
        )

    @transaction.atomic
    def decommission(self):
        return decommission_cluster(self.cluster)

    def topo_graph(self):
        return scan_cluster(self.cluster).to_dict()

    def add_proxies(self, proxies: List[Dict]):
        return add_proxies(self.cluster, proxies)

    def delete_proxies(self, proxies: List[Dict]):
        return delete_proxies(self.cluster, proxies)

    def replace_node(self, storages: List[Dict]):
        """替换节点 支持 替换 任意角色

        TODO
        """
        pass
