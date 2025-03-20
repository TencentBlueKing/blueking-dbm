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
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterStatus, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import ClusterEntry, ProxyInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


class FixProxyInplaceDBMetaService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        ip = kwargs.get("ip")
        port_list = kwargs.get("port_list")
        # cluster_id = kwargs.get("cluster_id")

        bk_cloud_id = kwargs.get("bk_cloud_id")

        # cluster_obj = Cluster.objects.get(pk=cluster_id)
        # cluster_obj.status = ClusterStatus.NORMAL

        for port in port_list:
            proxy_obj = ProxyInstance.objects.get(
                machine__ip=ip,
                port=port,
                machine__bk_cloud_id=bk_cloud_id,
            )
            proxy_obj.status = InstanceStatus.RUNNING

            cluster_obj = proxy_obj.cluster.first()
            cluster_obj.status = ClusterStatus.NORMAL

            # 实例关系
            proxy_obj.storageinstance.clear()
            proxy_obj.storageinstance.add(
                cluster_obj.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER)
            )

            # entry 表
            # 这里隐含了一个约束, 集群主入口必须绑定到所有 proxy
            entry = ClusterEntry.objects.filter(
                cluster=cluster_obj, role=ClusterEntryRole.MASTER_ENTRY, cluster_entry_type=ClusterEntryType.DNS
            ).all()

            proxy_obj.bind_entry.clear()
            proxy_obj.bind_entry.add(*entry)
            proxy_obj.save()
            cluster_obj.save()

        return True


class FixProxyInplaceDBMetaComponent(Component):
    name = __name__
    code = "fix_proxy_inplace_dbmeta"
    bound_service = FixProxyInplaceDBMetaService
