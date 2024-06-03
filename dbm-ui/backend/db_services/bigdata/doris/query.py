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

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.api.cluster.doris.detail import scan_cluster
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Machine
from backend.db_meta.models.cluster import Cluster
from backend.db_services.bigdata.resources.query import BigDataBaseListRetrieveResource
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper


@register_resource_decorator()
class DorisListRetrieveResource(BigDataBaseListRetrieveResource):
    cluster_types = [ClusterType.Doris]
    instance_roles = [
        InstanceRole.DORIS_FOLLOWER.value,
        InstanceRole.DORIS_OBSERVER.value,
        InstanceRole.DORIS_BACKEND_HOT.value,
        InstanceRole.DORIS_BACKEND_COLD.value,
    ]
    fields = [
        *BigDataBaseListRetrieveResource.fields,
        {"name": _("Follower节点"), "key": "doris_follower_nodes"},
        {"name": _("Observer节点"), "key": "doris_observer_nodes"},
        {"name": _("热节点"), "key": "doris_hot_nodes"},
        {"name": _("冷节点"), "key": "doris_cold_nodes"},
    ]

    @classmethod
    def get_nodes(cls, bk_biz_id: int, cluster_id: int, role: str, keyword: str = None) -> list:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        storage_instances = cluster.storageinstance_set.filter(instance_role=role)
        machines = Machine.objects.filter(bk_host_id__in=storage_instances.values_list("machine", flat=True))

        role_host_ids = list(machines.values_list("bk_host_id", flat=True))
        return ResourceQueryHelper.search_cc_hosts(role_host_ids, keyword)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
