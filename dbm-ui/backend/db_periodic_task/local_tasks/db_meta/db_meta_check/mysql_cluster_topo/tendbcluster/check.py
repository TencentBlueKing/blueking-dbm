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
from typing import List

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbcluster.access_relate import (
    _cluster_spider_access_remote,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbcluster.entry_bind import (
    _cluster_entry_on_spider,
    _cluster_entry_on_storage,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbcluster.status import (
    _cluster_master_remote_count,
    _cluster_master_spider_count,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.replicate import (
    cluster_master_as_ejector,
    cluster_replicate_out,
    cluster_slave_as_receiver,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.status import (
    cluster_instance_status,
    cluster_master_entry_count,
    cluster_master_status,
    cluster_standby_slave_status,
    cluster_status,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.unique_cluster import (
    cluster_instance_unique_cluster,
)


def health_check(cluster_id: int) -> List[CheckResponse]:
    """
    集群状态正常
    主入口数 >= 1
    主 spider >= 2
    master 状态正常
    master 实例数和分片数一致
    每个 master 实例唯一 standby slave
    standby slave 状态正常
    主/从入口 bind 的 spider 必须和正常 spider 数量一致
    master spider 只能访问 remote master
    slave spider 只能访问 remote slave
    mnt master spider 只能访问 remote master
    mnt slave spider 只能访问 remote slave
    master 只能作为 ejector
    slave 只能作为 receiver
    不允许有到集群外部的同步关系
    """
    qs = Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster).prefetch_related(
        "clusterentry_set__proxyinstance_set",
        "clusterentry_set__storageinstance_set",
        "proxyinstance_set__storageinstance",
        "storageinstance_set__as_receiver__ejector__cluster",
        "storageinstance_set__as_ejector__receiver__cluster",
        "storageinstance_set__cluster",
        "proxyinstance_set__cluster",
        "tendbclusterstorageset_set",
    )
    cluster_obj = qs.get(id=cluster_id)

    res = []
    # unique
    res.extend(cluster_instance_unique_cluster(cluster_obj))
    # status
    res.extend(cluster_status(cluster_obj))
    res.extend(cluster_instance_status(cluster_obj))
    res.extend(cluster_master_entry_count(cluster_obj))
    res.extend(_cluster_master_spider_count(cluster_obj))
    res.extend(cluster_master_status(cluster_obj))
    res.extend(_cluster_master_remote_count(cluster_obj))
    res.extend(cluster_standby_slave_status(cluster_obj))
    # bind
    res.extend(_cluster_entry_on_spider(cluster_obj))
    res.extend(_cluster_entry_on_storage(cluster_obj))
    # access relate
    res.extend(_cluster_spider_access_remote(cluster_obj))
    # replicate
    res.extend(cluster_master_as_ejector(cluster_obj))
    res.extend(cluster_slave_as_receiver(cluster_obj))
    res.extend(cluster_replicate_out(cluster_obj))
    return res
