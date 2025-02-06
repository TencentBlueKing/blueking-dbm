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
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.replicate import (
    cluster_master_as_ejector,
    cluster_slave_as_receiver,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.status import (
    cluster_master_entry_count,
    cluster_master_status,
    cluster_one_master,
    cluster_one_standby_slave,
    cluster_standby_slave_status,
    cluster_status,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.tendbha.unique_cluster import (
    cluster_instance_unique_cluster,
)


def sqlserver_dbmeta_check(cluster_id: int) -> List[CheckResponse]:
    """
    SQLServer Ha集群检测项：
    1：集群状态正常
    2：实例有且只有属于一个集群
    3：主入口数 >= 1
    4：唯一 master
    5：master 状态正常
    6：唯一 standby slave
    7：standby slave 状态正常
    8：master 只能作为 ejector
    9：slave 只能作为 receiver
    """
    # 或者集群所有元信息
    clusters = Cluster.objects.filter(id=cluster_id).prefetch_related(
        "clusterentry_set__storageinstance_set",
        "storageinstance_set__as_receiver__ejector__cluster",
        "storageinstance_set__as_ejector__receiver__cluster",
        "storageinstance_set__cluster",
    )

    res = []
    for cluster_obj in clusters:
        # 检查集群状态
        res.extend(cluster_status(cluster_obj))
        # 实例有且只有属于一个集群
        res.extend(cluster_instance_unique_cluster(cluster_obj))
        # 主入口数 >= 1
        res.extend(cluster_master_entry_count(cluster_obj))

        # 如果是ha架构，则需要检测下面子项
        if cluster_obj.cluster_type == ClusterType.SqlserverHA:
            # 唯一 master
            res.extend(cluster_one_master(cluster_obj))
            # master 状态
            res.extend(cluster_master_status(cluster_obj))
            # 唯一 standby slave
            res.extend(cluster_one_standby_slave(cluster_obj))
            # standby slave 状态正常
            res.extend(cluster_standby_slave_status(cluster_obj))
            # master 只能作为 ejector
            res.extend(cluster_master_as_ejector(cluster_obj))
            # slave 只能作为 receiver
            res.extend(cluster_slave_as_receiver(cluster_obj))

    return res
