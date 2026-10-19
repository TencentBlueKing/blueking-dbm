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
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster


def ticket_error(field: str, message: str) -> dict:
    """返回 ParamValidateSerializerMixin 可直接抛给提单接口的错误项。"""
    return {"field": field, "errors": message, "index": 0, "row_key": ""}


def get_hdfs_cluster(cluster_id):
    """集群不存在或不是 HDFS 时返回 (None, error)，否则返回 (cluster, None)。"""
    if not cluster_id:
        return None, ticket_error("cluster_id", _("cluster_id 不能为空"))
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return None, ticket_error("cluster_id", _("集群 {} 不存在").format(cluster_id))
    if cluster.cluster_type != ClusterType.Hdfs.value:
        return None, ticket_error("cluster_id", _("集群 {} 不是 HDFS 集群").format(cluster_id))
    return cluster, None


def cluster_datanode_ips(cluster: Cluster) -> set:
    return set(
        cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_DATA_NODE.value).values_list(
            "machine__ip", flat=True
        )
    )


def node_ips(nodes: list) -> list:
    return [node.get("ip") for node in nodes if node.get("ip")]


def check_datanode_ips_belong_to_cluster(cluster: Cluster, nodes: list, field: str) -> list:
    """单据里的 DataNode IP 必须都是该集群当前的 DataNode。"""
    errors = []
    missing_ip_count = sum(1 for node in nodes if not node.get("ip"))
    if missing_ip_count:
        errors.append(ticket_error(field, _("DataNode 节点缺少 IP")))
    dn_ips = cluster_datanode_ips(cluster)
    unknown_ips = [ip for ip in node_ips(nodes) if ip not in dn_ips]
    if unknown_ips:
        errors.append(ticket_error(field, _("IP {} 不属于该集群的 DataNode").format(",".join(unknown_ips))))
    return errors
