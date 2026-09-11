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
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Spec, StorageInstance
from backend.db_meta.models.storage_set_dtl import TenDBClusterStorageSet
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.tendbcluster.tendb_node_reblance import TendbNodeRebalanceDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_tendbcluster_node_rebalance(
    username: str,
    infos: List[dict],
    backup_source: str = MySQLBackupSource.REMOTE,
    need_checksum: bool = True,
):
    """
    创建 TenDBCluster 集群容量变更单据，支持多行，每行一个集群：
    - cluster_domain: 集群域名
    - spec_id: 目标规格 ID
    - count: 目标机器组数
    - labels: 资源标签 ID 列表（可选）
    backup_source / need_checksum 为整单共用参数。

    集群总分片数（cluster_shard_num）由工具从 db_meta 自动查询，固定不变；
    单机分片数（remote_shard_num）= 总分片数 / 机器组数。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBCluster)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 remote（backend）类型
    spec_ids = {info["spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.TenDBCluster,
        spec_machine_type=SpecMachineType.BACKEND,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    # 目标规格对象映射：用于详情展示的目标规格名与目标容量
    spec_map = {spec.spec_id: spec for spec in spec_objs}

    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        # 集群总分片数（固定）
        cluster_shard_num = TenDBClusterStorageSet.objects.using(MYSQL_MCP_DB_READ).filter(cluster=cluster).count()
        if cluster_shard_num <= 0:
            raise DBMMcpBaseException(msg=_("集群 {} 无分片信息").format(cluster.immute_domain))

        # 单机分片数 = 总分片数 / 机器组数，必须整除
        if count <= 0 or cluster_shard_num % count != 0:
            raise DBMMcpBaseException(
                msg=_("集群 {} 总分片数 {} 无法被机器组数 {} 整除").format(cluster.immute_domain, cluster_shard_num, count)
            )
        remote_shard_num = cluster_shard_num // count

        # 当前 remote 实例，用于获取当前规格与机器组数（仅用于详情展示）
        remote_insts = StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(
            cluster=cluster, machine_type=MachineType.REMOTE.value
        )
        if not remote_insts.exists():
            raise DBMMcpBaseException(msg=_("集群 {} 无 remote 存储实例").format(cluster.immute_domain))

        current_machine_cnt = remote_insts.values_list("machine__bk_host_id", flat=True).distinct().count()
        current_machine_pair = current_machine_cnt // 2
        current_spec_id = remote_insts.first().machine.spec_id

        # 当前规格名（仅用于详情展示）
        prev_cluster_spec_name = ""
        current_spec = Spec.objects.filter(spec_id=current_spec_id).first()
        if current_spec:
            prev_cluster_spec_name = current_spec.spec_name

        target_spec = spec_map[spec_id]
        resource_spec = {
            "backend_group": {
                "count": count,
                "spec_id": spec_id,
                "labels": labels,
                # 目标规格名 / 目标容量：详情页「目标容量」列展示用
                "specName": target_spec.spec_name,
                "futureCapacity": target_spec.capacity,
            }
        }

        built_infos.append(
            {
                "cluster_id": cluster.id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "cluster_shard_num": cluster_shard_num,
                "remote_shard_num": remote_shard_num,
                "resource_spec": resource_spec,
                "prev_cluster_spec_name": prev_cluster_spec_name,
                "prev_machine_pair": current_machine_pair,
                "spec_id": current_spec_id,
            }
        )

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_NODE_REBALANCE,
        "remark": TicketType.TENDBCLUSTER_NODE_REBALANCE,
        "creator": username,
        "helpers": [],
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "backup_source": backup_source,
            "need_checksum": need_checksum,
            "infos": built_infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = TendbNodeRebalanceDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_NODE_REBALANCE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]
