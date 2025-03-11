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
from typing import Any, Dict, List

from django.db.models import Q, Value
from django.db.models.query import QuerySet

from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler as BaseClusterServiceHandler
from backend.db_services.dbbase.dataclass import DBInstance


class ClusterServiceHandler(BaseClusterServiceHandler):
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def get_remote_pairs(self, cluster_ids: List[int]):
        """
        根据tendbcluster集群查询remote db/remote dr
        @param cluster_ids: 集群的ID列表
        """
        # 获取集群和对应的remote db实例
        clusters: QuerySet[Cluster] = Cluster.objects.prefetch_related("storageinstance_set").filter(
            id__in=cluster_ids
        )
        master_insts = StorageInstance.objects.prefetch_related("as_ejector").filter(
            cluster__in=clusters, instance_role=InstanceRole.REMOTE_MASTER
        )

        # 根据remote db实例查询remote dr实例
        cluster_id__remote_pairs: Dict[int, List[Dict]] = defaultdict(list)
        for master in master_insts:
            cluster_id = master.cluster.first().id
            slave: StorageInstance = master.as_ejector.first().receiver
            cluster_id__remote_pairs[cluster_id].append(
                {"remote_db": master.simple_desc, "remote_dr": slave.simple_desc}
            )

        remote_pair_infos: List[Dict[str, Any]] = [
            {"cluster_id": cluster_id, "remote_pairs": cluster_id__remote_pairs[cluster_id]}
            for cluster_id in cluster_id__remote_pairs.keys()
        ]
        return remote_pair_infos

    def find_related_clusters_by_instances(self, instances: List[DBInstance]) -> List[Dict[str, Any]]:
        return super().find_related_clusters_by_instances(instances, same_role=True)

    def _get_instance_objs(self, instances: List[DBInstance]):
        """
        根据instance(属DBInstance类)查询数据库实例，注意这里要考虑混布的情况
        eg: Tendbcluster的中控节点和spider master节点就是混布
        """
        bk_host_ids = [instance.bk_host_id for instance in instances]

        # 获得基本的instance_objs
        instance_objs = super()._get_instance_objs(instances)
        cluster_type = instance_objs[0].cluster.first().cluster_type

        # 如果是Tendbcluster，则中控节点混布，需补充
        if cluster_type == ClusterType.TenDBCluster:
            controller_instances = list(
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(
                    Q(machine__bk_host_id__in=bk_host_ids)
                    & Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
                )
                .annotate(role=Value("spider_ctl"))
            )
            # 覆写port为admin port
            for instance in controller_instances:
                instance.port = instance.admin_port
            instance_objs.extend(controller_instances)

        return instance_objs
