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

from backend.db_meta.api.cluster.es.detail import scan_cluster
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Machine
from backend.db_meta.models.cluster import Cluster
from backend.db_services.bigdata.resources.query import BigDataBaseListRetrieveResource
from backend.db_services.dbbase.resources.query import CommonQueryResourceMixin
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper


@register_resource_decorator()
class ESListRetrieveResource(BigDataBaseListRetrieveResource):
    cluster_types = [ClusterType.Es]
    instance_roles = [
        InstanceRole.ES_MASTER.value,
        InstanceRole.ES_DATANODE_HOT.value,
        InstanceRole.ES_DATANODE_COLD.value,
        InstanceRole.ES_CLIENT.value,
    ]
    fields = [
        *BigDataBaseListRetrieveResource.fields,
        {"name": _("Master节点"), "key": "es_master_nodes"},
        {"name": _("热节点"), "key": "es_hot_nodes"},
        {"name": _("冷节点"), "key": "es_cold_nodes"},
        {"name": _("代理节点"), "key": "es_client"},
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

    @classmethod
    def update_headers(cls, headers, **kwargs):
        # 补充实例为空未展示的字段
        extra_headers = [
            {"id": "clb", "name": _("clb")},
            {"id": "polaris", "name": _("北极星")},
            {"id": "es_master", "name": _("Master 节点")},
            {"id": "es_client", "name": _("Client 节点")},
            {"id": "es_datanode_hot", "name": _("热节点")},
            {"id": "es_datanode_cold", "name": _("冷节点")},
        ]

        return super().update_headers(headers, extra_headers=extra_headers)

    @classmethod
    def update_cluster_info(cls, cluster, cluster_info, **kwargs):
        """
        补充额外的集群列表数据
        """

        # 补充clb/北极星
        clb_entry, polaris_entry = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)
        cluster_info.update(
            {
                "clb": clb_entry,
                "polaris": polaris_entry,
            }
        )
        return cluster_info
