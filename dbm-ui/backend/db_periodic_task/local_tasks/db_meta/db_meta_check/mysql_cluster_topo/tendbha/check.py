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
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.access_relate import (
    _cluster_proxy_access_master,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.entry_bind import (
    _cluster_entry_real_bind,
    _cluster_master_entry_on_proxy,
    _cluster_master_entry_on_storage,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.replicate import (
    _cluster_master_as_ejector,
    _cluster_replicate_out,
    _cluster_slave_as_receiver,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.status import (
    _cluster_instance_status,
    _cluster_master_entry_count,
    _cluster_master_status,
    _cluster_one_master,
    _cluster_one_standby_slave,
    _cluster_proxy_count,
    _cluster_standby_slave_status,
    _cluster_status,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.unique_cluster import (
    _cluster_instance_unique_cluster,
)


def health_check(cluster_id: int) -> List[CheckResponse]:
    """
    所有检查项应相互独立
    集群状态正常
    主入口数 >= 1
    proxy 数 >= 2
    唯一 master
    master 状态正常
    唯一 standby slave
    standby slave 状态正常
    主入口 bind 的 proxy 必须和集群正常 proxy 数量一致
    主入口不能 bind 到存储
    ToDo 检查域名真实的 bind 配置
    proxy 只能访问 master
    master 只能作为 ejector
    slave 只能作为 receiver
    不允许有到集群外部的同步关系
    """
    qs = Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).prefetch_related(
        "clusterentry_set__proxyinstance_set",
        "clusterentry_set__storageinstance_set",
        "proxyinstance_set__storageinstance",
        "storageinstance_set__as_receiver__ejector__cluster",
        "storageinstance_set__as_ejector__receiver__cluster",
        "storageinstance_set__cluster",
        "proxyinstance_set__cluster",
    )
    cluster_obj = qs.get(id=cluster_id)

    res = []
    # unique_cluster.py
    res.extend(_cluster_instance_unique_cluster(cluster_obj))
    # status.py
    res.extend(_cluster_status(cluster_obj))
    res.extend(_cluster_instance_status(cluster_obj))
    res.extend(_cluster_master_entry_count(cluster_obj))
    res.extend(_cluster_proxy_count(cluster_obj))
    res.extend(_cluster_one_master(cluster_obj))
    res.extend(_cluster_master_status(cluster_obj))
    res.extend(_cluster_one_standby_slave(cluster_obj))
    res.extend(_cluster_standby_slave_status(cluster_obj))
    # entry_bind.py
    res.extend(_cluster_master_entry_on_proxy(cluster_obj))
    res.extend(_cluster_master_entry_on_storage(cluster_obj))
    res.extend(_cluster_entry_real_bind(cluster_obj))
    res.extend(_cluster_proxy_access_master(cluster_obj))
    # replicate.py
    res.extend(_cluster_master_as_ejector(cluster_obj))
    res.extend(_cluster_slave_as_receiver(cluster_obj))
    res.extend(_cluster_replicate_out(cluster_obj))

    return res
