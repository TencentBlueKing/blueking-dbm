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

from backend.db_meta.api.cluster.base.graph import Graphic, LineLabel
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstance


def scan_cluster(cluster: Cluster) -> Graphic:
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))
    storage_inst = StorageInstance.objects.get(cluster=cluster, cluster_type=ClusterType.SqlserverSingle)

    _, cluster_entry_group = graph.add_node(storage_inst.bind_entry.first())
    _, storage_node_group = graph.add_node(storage_inst)

    graph.add_line(source=cluster_entry_group, target=storage_node_group, label=LineLabel.Bind)

    return graph
