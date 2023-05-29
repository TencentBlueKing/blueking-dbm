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
from backend.db_meta.enums import ClusterType

from .create import pkg_create_mongoset
from .detail import scan_cluster


class MongoReplicaSetHandler(ClusterHandler):
    """
    副本集架构通过部署多个服务器存储数据副本来达到高可用的能力，每一个副本集实例由一个 Primary 节点和一个或多个 Secondary 节点组成。
    Primary 节点：负责处理客户端的读写请求。每个副本集架构实例中只能有一个 Primary 节点。
    Secondary 节点：通过定期轮询 Primary 节点的 oplog（操作日志）复制 Primary 节点的数据，保证数据与 Primary 节点一致。
    在 Primary 节点故障时，多个 Secondary 节点通过选举成为新的 Primary 节点，保障高可用。
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
        storages: Optional[List] = None,
        creator: str = "",
        bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
        region: str = "",
    ):
        """「必须」创建集群"""

        pkg_create_mongoset(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            db_module_id=db_module_id,
            alias=alias,
            major_version=major_version,
            storages=storages,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            cluster_type=ClusterType.MongoReplicaSet.value,
        )

    @transaction.atomic
    def decommission(self):
        return decommission_cluster(self.cluster)

    def topo_graph(self):
        return scan_cluster(self.cluster).to_dict()

    def replace_node(self, storages: List[Dict]):
        """替换节点 支持 替换 任意角色

        TODO
        """
        pass
