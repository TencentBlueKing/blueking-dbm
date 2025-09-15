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

import logging

from backend.db_services.redis.capacity_evaluate_service.repositories.cluster_topo_repo import (
    ClusterCapacityInfo,
    ClusterTopoInfo,
)

logger = logging.getLogger("root")


class CapacityCalculateService:
    """容量评估服务"""

    def __init__(self):
        """初始化容量评估服务"""

    @classmethod
    def get_cluster_info(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群信息"""
        topo_info = ClusterTopoInfo(cluster_id, bk_biz_id)
        topo_info.fetch_data()
        topo_info.generate_spec_info()
        return {
            "cluster_info": topo_info.__dict__(),
            "proxy_list": topo_info.proxy_list,
            "shard_list": topo_info.shard_list,
            "host_infos": topo_info.host_infos,
        }

    @classmethod
    def calculate(cls, bk_biz_id: int, cluster_id: int):
        """先获得集群结构，再计算集群容量"""
        try:
            topo_info = ClusterTopoInfo(cluster_id, bk_biz_id)
            topo_info.fetch_data()
            topo_info.generate_spec_info()
        except Exception as e:
            raise e

        capacity_info = ClusterCapacityInfo(topo_info)
        query_errors = capacity_info.generate_used_capacity_info(bk_biz_id)
        if len(query_errors) > 0:
            raise Exception(f"generate_used_capacity_info errors: {query_errors}")

        return capacity_info
