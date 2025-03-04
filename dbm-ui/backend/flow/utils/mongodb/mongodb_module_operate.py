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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, AccessLayer
from backend.db_meta.models import StorageInstance, ProxyInstance, Cluster
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from typing import Union


class MongoDBCCTopoOperator(CCTopoOperator):
    db_type = DBType.MongoDB.value

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance], cluster: Cluster) -> dict:
        """
        生成 MongoDB 集群分片标签
        MongoReplicaSet 的值为cluster.name
        MongoShardedCluster 的值为 primary的nosqlstoragesetdtl_set.seg_range
        """
        try:
            if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
                return {"shard": cluster.name}
            elif (
                cluster.cluster_type == ClusterType.MongoShardedCluster.value
                and ins.instance_role != AccessLayer.PROXY.value
            ):
                return {"shard": self.get_mongo_shard(cluster, ins)}
            return {}
        except Exception as e:
            raise e

    @staticmethod
    def get_mongo_shard(cluster: Cluster, ins: StorageInstance) -> str:
        """
        获取 ins的分片信息
        """

        for m in cluster.nosqlstoragesetdtl_set.all():
            if m.instance == ins:
                return m.seg_range
            for e in m.instance.as_ejector.all():
                if e.receiver == ins:
                    return m.seg_range
        return "unknown"
