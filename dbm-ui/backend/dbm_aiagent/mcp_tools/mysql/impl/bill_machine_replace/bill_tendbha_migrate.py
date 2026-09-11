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
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Spec
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.mysql_migrate_cluster import MysqlMigrateClusterDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_tendbha_migrate(
    username: str,
    infos: List[dict],
    opera_object: str,
    backup_source: str = MySQLBackupSource.REMOTE,
    need_checksum: bool = True,
    is_safe: bool = True,
):
    """
    创建 TenDBHA 主从迁移单据，支持多行，每行一个集群：
    - cluster_domain: 集群域名
    - spec_id: 目标规格 ID
    - count: 机器组数（1组=1主+1从）
    - labels: 资源标签 ID 列表（可选）
    opera_object / backup_source / need_checksum / is_safe 为整单共用参数。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 MySQL backend 存储类型
    spec_ids = {info["spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.MySQL,
        spec_machine_type=SpecMachineType.BACKEND,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("count 必须为正整数: {}").format(count))

        # 主从迁移成对迁移：resource_spec.backend_group（1组 = 1 master + 1 slave）
        resource_spec = {"backend_group": {"count": count, "spec_id": spec_id, "labels": labels}}

        built_infos.append(
            {
                "cluster_ids": [cluster.id],
                "resource_spec": resource_spec,
            }
        )

    ticket_param = {
        "ticket_type": TicketType.MYSQL_MIGRATE_CLUSTER,
        "remark": TicketType.MYSQL_MIGRATE_CLUSTER,
        "creator": username,
        "helpers": [],
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "backup_source": backup_source,
            "is_safe": is_safe,
            "need_checksum": need_checksum,
            "opera_object": opera_object,
            "infos": built_infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = MysqlMigrateClusterDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_MIGRATE_CLUSTER
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]
