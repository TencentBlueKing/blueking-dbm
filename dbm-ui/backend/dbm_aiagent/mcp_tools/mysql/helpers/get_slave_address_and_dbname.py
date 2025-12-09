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
from typing import Tuple

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstanceTuple


def get_cloud_slave_address_and_dbname(
    cluster_type: ClusterType, cluster_domain: str, dbname: str
) -> Tuple[int, str, str]:
    cluster_obj = Cluster.objects.get(immute_domain=cluster_domain, cluster_type=cluster_type)

    if cluster_type == ClusterType.TenDBSingle:
        address = cluster_obj.storageinstance_set.first().ip_port
    elif cluster_type == ClusterType.TenDBHA:
        address = cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE).first().ip_port
    else:
        one_remove_slave = cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE).first()
        address = one_remove_slave.ip_port

        one_storageinstance_tuple = StorageInstanceTuple.objects.get(receiver=one_remove_slave)
        shard_id = one_storageinstance_tuple.tendbclusterstorageset.shard_id
        dbname = f"{dbname}_{shard_id}"

    return cluster_obj.bk_cloud_id, address, dbname
