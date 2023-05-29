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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster


def biz_clusters(bk_biz_id: int, immute_domains: Optional[List[str]]):
    """
    对比老版本, 添加了更多的信息
    1. 所有实例有了更多的信息, 特别的, 返回了 bk_instance_id
    2. 新增了 master_storage_instances, slave_storage_instances 两个实例列表, 能更快的拿到需要的实例信息.
       原有的 storages 依然保留, 等调用方完成修改后可以删除
    3. storage.instance_inner_role, 为枚举的 [master, slave], 写代码更方便
    """
    res = []

    qs = Cluster.objects.prefetch_related(
        "storageinstance_set", "proxyinstance_set", "storageinstance_set__machine", "proxyinstance_set__machine"
    ).filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.TenDBHA.value,
    )

    if immute_domains:
        qs = qs.filter(immute_domain__in=immute_domains)

    for cluster in qs:
        res.append(
            {
                "immute_domain": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "bk_biz_id": bk_biz_id,
                "db_module_id": cluster.db_module_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "proxies": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "admin_port": ele.admin_port,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                        "status": ele.status,
                        "bk_instance_id": ele.bk_instance_id,
                    }
                    for ele in cluster.proxyinstance_set.all()
                ],
                "master_storage_instances": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "instance_inner_role": ele.instance_inner_role,
                        "instance_role": ele.instance_role,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                        "status": ele.status,
                        "bk_instance_id": ele.bk_instance_id,
                    }
                    for ele in cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value)
                ],
                "slave_storage_instances": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "instance_inner_role": ele.instance_inner_role,
                        "instance_role": ele.instance_role,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                        "status": ele.status,
                        "bk_instance_id": ele.bk_instance_id,
                    }
                    for ele in cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE.value)
                ],
                "storages": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "instance_inner_role": ele.instance_inner_role,
                        "instance_role": ele.instance_role,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                        "status": ele.status,
                        "bk_instance_id": ele.bk_instance_id,
                    }
                    for ele in cluster.storageinstance_set.all()
                ],
            }
        )

    return res
