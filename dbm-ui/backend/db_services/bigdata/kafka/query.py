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

from backend.db_meta.api.cluster.kafka.detail import scan_cluster
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.bigdata.resources.query import BigDataBaseListRetrieveResource
from backend.db_services.dbbase.resources.register import register_resource_decorator


@register_resource_decorator()
class KafkaListRetrieveResource(BigDataBaseListRetrieveResource):

    cluster_types = [ClusterType.Kafka]
    instance_roles = [InstanceRole.BROKER, InstanceRole.ZOOKEEPER]
    fields = [
        *BigDataBaseListRetrieveResource.fields,
        {"name": _("broker节点"), "key": "broker"},
        {"name": _("zookeeper节点"), "key": "zookeeper"},
    ]

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
