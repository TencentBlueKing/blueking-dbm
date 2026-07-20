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
from typing import Union

from django.utils.translation import gettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance


def get_dbconsole_read_instance(cluster: Cluster) -> Union[ProxyInstance, StorageInstance]:
    """
    获取 dbconsole dump / where 校验共用的只读实例。

    TenDBCluster: 优先 spider slave，不存在则用 spider master
    其他: orphan 或 backend slave
    """
    if cluster.cluster_type == ClusterType.TenDBCluster:
        backend_info = ProxyInstance.objects.filter(
            cluster=cluster,
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
        ).first()
        # 如果不存在 slave spider，则使用 master spider
        if backend_info is None:
            backend_info = ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
            ).first()
    else:
        backend_info = StorageInstance.objects.filter(
            cluster=cluster,
            instance_role__in=[
                InstanceRole.ORPHAN,
                InstanceRole.BACKEND_SLAVE,
            ],
        ).first()

    if backend_info is None:
        raise ValueError(_("查询不到可执行的只读实例"))
    return backend_info
