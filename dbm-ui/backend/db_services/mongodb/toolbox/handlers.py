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
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler


class ToolboxHandler(ClusterServiceHandler):
    """mongodb工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        super().__init__(bk_biz_id)

    @classmethod
    def get_execute_cluster_hosts(cls, cluster):
        cluster_type = cluster.cluster_type
        host_ids = []
        # 有可能连后端Master/slave, 也有可能连接Proxy的
        if cluster_type in [ClusterType.MongoReplicaSet]:
            host_ids = list(cluster.storageinstance_set.values_list("machine__bk_host_id", flat=True))
            host_ids.extend(list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True)))
        # 只连接Proxy的
        elif cluster_type in [ClusterType.MongoShardedCluster]:
            host_ids = list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True))

        return host_ids
