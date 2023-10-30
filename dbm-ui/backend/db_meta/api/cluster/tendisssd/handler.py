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
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import create_twemproxy_cluster
from backend.db_meta.api.cluster.nosqlcomm.decommission import (
    decommission_backends,
    decommission_cluster,
    decommission_proxies,
)
from backend.db_meta.api.cluster.nosqlcomm.detail_cluster import scan_cluster
from backend.db_meta.api.cluster.nosqlcomm.scale_proxy import add_proxies, delete_proxies
from backend.db_meta.api.cluster.nosqlcomm.scale_tendis import make_sync_mms, redo_slaves, switch_tendis
from backend.db_meta.enums import ClusterType


class TendisSSDClusterHandler(ClusterHandler):
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
        create_twemproxy_cluster(
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
            cluster_type=ClusterType.TwemproxyTendisSSDInstance.value,
        )

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        return decommission_cluster(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        return scan_cluster(self.cluster).to_dict()

    def decommission_proxies(self, proxies: List[Dict]):
        return decommission_proxies(self.cluster, proxies, False)

    def decommission_tendis(self, tendiss: List[Dict]):
        return decommission_backends(self.cluster, tendiss, False)

    def add_proxies(self, proxies: List[Dict]):
        return add_proxies(self.cluster, proxies)

    def delete_proxies(self, proxies: List[Dict]):
        return delete_proxies(self.cluster, proxies)

    def redo_slaves(self, tendiss):
        return redo_slaves(self.cluster, tendiss)

    def make_sync(self, tendiss):
        return make_sync_mms(self.cluster, tendiss)

    def switch_tendis(self, tendiss):
        return switch_tendis(self.cluster, tendiss)
