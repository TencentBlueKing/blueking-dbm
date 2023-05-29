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

from django.core.exceptions import ObjectDoesNotExist

from backend.db_meta.enums import AccessLayer, ClusterEntryRole, ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterEntryNotBindException, ClusterEntryNotExistException
from backend.db_meta.models import ClusterEntry


def cluster_instances(entry_name: str):
    """
    用任意访问入口查询 TenDBHA 集群信息
    bind_to 是访问入口绑定的 AccessLayer 名称
    当 bind_to == proxy 时为主入口, 授权需要在 proxy 开通白名单, 切在 storage.instance_inner_role == master 上授权
    当 bind_to == storage 时为从入口, 只需要在 storage.instance_inner_role == slave 上授权

    对比老版本, 返回增加了几个 field 更为方便
    1. entry_role, 直接指明访问入口是主入口还是从入口
    2. storage.instance_inner_role, 为枚举的 [master, slave], 写代码更方便
    3. 所有实例信息增加了 bk_instance_id
    4. immute_domain
    5. 新增了 master_storage_instance 和 slave_storage_instances 两个字段, 能更快的拿到需要的实例信息.
       原有的 storages 依然保留, 等调用方完成修改后可以删除
    """
    try:
        input_entry = ClusterEntry.objects.get(entry=entry_name, cluster__cluster_type=ClusterType.TenDBHA.value)
        if input_entry.proxyinstance_set.exists():
            bind_to_layer = AccessLayer.PROXY.value
        elif input_entry.storageinstance_set.exists():
            bind_to_layer = AccessLayer.STORAGE.value
        else:
            raise ClusterEntryNotBindException(entry=entry_name)

        cluster = input_entry.cluster

        master_storage_instance = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        return {
            "bind_to": bind_to_layer,
            "entry_role": input_entry.role,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "immute_domain": cluster.immute_domain,
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
            "master_storage_instance": {
                "ip": master_storage_instance.machine.ip,
                "port": master_storage_instance.port,
                "instance_inner_role": master_storage_instance.instance_inner_role,
                "instance_role": master_storage_instance.instance_role,
                "bk_cloud_id": master_storage_instance.machine.bk_cloud_id,
                "status": master_storage_instance.status,
                "bk_instance_id": master_storage_instance.bk_instance_id,
            },
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

    except ObjectDoesNotExist:
        raise ClusterEntryNotExistException(entry=entry_name)
