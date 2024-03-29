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
from typing import List, Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.api.cluster.nosqlcomm.decommission import decommission_cluster
from backend.db_meta.api.cluster.nosqlcomm.detail_cluster import scan_cluster
from backend.db_meta.api.cluster.nosqlcomm.scale_tendis import make_sync_mms
from backend.db_meta.enums import ClusterType

from .single import pkg_create_single, redo_slave, switch_2_pair, switch_2_slave


class TendisSingleHandler(ClusterHandler):

    # Tendis 内存版-单实例
    cluster_type = ClusterType.TendisRedisInstance

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        name: str,
        immute_domain: str,
        slave_domain: str,
        db_module_id: int,
        alias: str = "",
        major_version: str = "",
        storages: Optional[List] = None,
        creator: str = "",
        bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
        region: str = "",
        disaster_tolerance_level: str = "",
    ):
        """「必须」创建集群"""
        pkg_create_single(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            slave_domain=slave_domain,
            db_module_id=db_module_id,
            alias=alias,
            major_version=major_version,
            storages=storages,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            disaster_tolerance_level=disaster_tolerance_level,
        )

    @transaction.atomic
    def decommission(self):
        return decommission_cluster(self.cluster)

    def topo_graph(self):
        return scan_cluster(self.cluster).to_dict()

    def redo_slave(self, tendiss):
        return redo_slave(self.cluster, tendiss)

    def make_sync(self, tendiss):
        return make_sync_mms(self.cluster, tendiss)

    def switch_2_slave(self, tendis):
        """切换到slave 节点 m->s {"ejector":{},"receiver":{}}"""
        return switch_2_slave(self.cluster, tendis)

    def switch_2_pair(self, tendis):
        """成对切换 m->s 切换到 m->s {"ejector":{},"receiver":{}}"""
        return switch_2_pair(self.cluster, tendis)
