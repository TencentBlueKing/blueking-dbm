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
from abc import ABC

from django.db import transaction

from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster


class ClusterHandler(ABC):
    # 「必须」 集群类型
    cluster_type = None

    def __init__(self, bk_biz_id: int, cluster_id: int):
        self.bk_biz_id = bk_biz_id
        self.cluster_id = cluster_id
        try:
            self.cluster: Cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id)

    @classmethod
    def get_exact_handler(cls, bk_biz_id: int, cluster_id: int):
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_type="", cluster_id=cluster_id)
        for subclass in cls.__subclasses__():
            if subclass.cluster_type == cluster.cluster_type:
                return subclass(bk_biz_id=bk_biz_id, cluster_id=cluster_id)

    @classmethod
    @transaction.atomic
    def create(cls, *args, **kwargs):
        """「必须」创建集群"""
        raise NotImplementedError

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        raise NotImplementedError

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        raise NotImplementedError
