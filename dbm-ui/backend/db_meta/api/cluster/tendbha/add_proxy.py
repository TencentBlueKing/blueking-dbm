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

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.utils.mysql.bk_module_operate import transfer_host_in_cluster_module

logger = logging.getLogger("root")


@transaction.atomic
def add_proxy(cluster_ids: list, proxy_ip: str, bk_cloud_id: int):
    """
    集群添加proxy场景元数据注册方式
    默认情况下新的proxy的时区信息以集群的记录为准
    """

    for cluster_id in cluster_ids:
        cluster = Cluster.objects.get(id=cluster_id)
        cluster_proxy_port = ProxyInstance.objects.filter(cluster=cluster).all()[0].port
        proxy_objs = ProxyInstance.objects.filter(machine__ip=proxy_ip, port=cluster_proxy_port)
        master_storage_obj = StorageInstance.objects.get(cluster=cluster, instance_inner_role=InstanceInnerRole.MASTER)

        # 设置接入层后端
        master_storage_obj.proxyinstance_set.add(*proxy_objs)

        # 关联对应的域名信息
        template_proxy = ProxyInstance.objects.filter(cluster=cluster, status=InstanceStatus.RUNNING.value).all()[0]
        entry_list = template_proxy.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS).all()
        for bind_entry in entry_list:
            bind_entry.proxyinstance_set.add(*proxy_objs)

        # 关联cluster
        cluster.proxyinstance_set.add(*proxy_objs)

        # proxy实例的时区信息同步cluster的,这里其实list只有一个实例
        for proxy in proxy_objs:
            proxy.time_zone = cluster.time_zone
            proxy.save()

    # proxy主机转移模块、添加对应的服务实例
    transfer_host_in_cluster_module(
        cluster_ids=cluster_ids,
        ip_list=[proxy_ip],
        machine_type=MachineType.PROXY.value,
        bk_cloud_id=bk_cloud_id,
    )
