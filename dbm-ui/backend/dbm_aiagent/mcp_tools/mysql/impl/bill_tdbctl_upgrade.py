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
from typing import List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.mysql.toolbox.serializers import TdbctlUpgradeSerializer
from backend.db_services.mysql.toolbox.tdbctl_upgrade_handler import TdbctlUpgradeHandler
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_tdbctl_upgrade(
    bk_biz_id: int,
    username: str,
    cluster_domains: Optional[List[str]] = None,
    cluster_ids: Optional[List[int]] = None,
    version: Optional[str] = None,
) -> Ticket:
    """
    创建 TenDBCluster 中控（tdbctl）升级单据

    参数：
        bk_biz_id: 业务ID
        username: 创建人用户名
        cluster_domains: 集群域名列表（可选，与 cluster_ids 二选一）
        cluster_ids: 集群ID列表（可选，与 cluster_domains 二选一）
        version: 升级版本号（可选）
    """
    # 1. 查询升级包（只查询 id 和 name 字段）
    if version:
        # 用户指定版本，使用 name like '%tdbctl-{version}%' 查询
        # 例如：传入 version='2.4.10'，查询 name 包含 'tdbctl-2.4.10' 的包
        package = (
            Package.objects.using(MYSQL_MCP_DB_READ)
            .filter(pkg_type="tdbctl", name__icontains=f"tdbctl-{version}")
            .only("id", "name")
            .order_by("-create_at")
            .first()
        )

        if not package:
            raise Exception(_("未找到版本 {} 的 tdbctl 升级包").format(version))
    else:
        # 不传版本号，查询最新创建的 tdbctl 包
        # SQL: SELECT id, name FROM db_package_package WHERE pkg_type='tdbctl' ORDER BY create_at DESC LIMIT 1
        package = (
            Package.objects.using(MYSQL_MCP_DB_READ)
            .filter(pkg_type="tdbctl")
            .only("id", "name")
            .order_by("-create_at")
            .first()
        )

        if not package:
            raise Exception(_("未找到 tdbctl 升级包"))

    # 2. 查询集群并构建单据参数
    # 空列表视为未传；去重避免重复升级
    cluster_domains = list(dict.fromkeys(cluster_domains)) if cluster_domains else None
    cluster_ids = list(dict.fromkeys(cluster_ids)) if cluster_ids else None
    has_domains = cluster_domains and len(cluster_domains) > 0
    has_ids = cluster_ids and len(cluster_ids) > 0
    if has_domains and has_ids:
        raise Exception(_("cluster_domains 与 cluster_ids 只能二选一，不能同时传入"))

    if has_domains or has_ids:
        # 升级指定集群（支持多个）
        clusters = []
        if has_domains:
            for domain in cluster_domains:
                try:
                    cluster = Cluster.objects.using(MYSQL_MCP_DB_READ).get(
                        bk_biz_id=bk_biz_id, immute_domain=domain, cluster_type=ClusterType.TenDBCluster
                    )
                    clusters.append(cluster)
                except Cluster.DoesNotExist:
                    raise Exception(_("集群 {} 不存在或不是 TenDBCluster 类型，请检查集群域名和业务ID").format(domain))
        else:
            for cid in cluster_ids:
                try:
                    cluster = Cluster.objects.using(MYSQL_MCP_DB_READ).get(
                        id=cid, bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBCluster
                    )
                    clusters.append(cluster)
                except Cluster.DoesNotExist:
                    raise Exception(_("集群ID {} 不存在或不属于业务 {}，请检查集群ID和业务ID").format(cid, bk_biz_id))
        cluster_ids = [c.id for c in clusters]
    else:
        # 升级业务下所有集群：查询所有 TenDBCluster 集群
        clusters = list(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBCluster)
        )

        if not clusters:
            raise Exception(_("业务 {} 下未找到任何 TenDBCluster 集群").format(bk_biz_id))

        cluster_ids = [cluster.id for cluster in clusters]

    details = {"bk_biz_id": bk_biz_id, "cluster_ids": cluster_ids, "pkg_id": package.id}

    # 3. 检查集群是否需要升级
    handler = TdbctlUpgradeHandler(bk_biz_id=bk_biz_id, pkg_id=package.id, operator=username)

    # 检查哪些集群需要升级，哪些已经是最新版本（如果目标集群已经是目标版本则跳过升级）
    filter_result = handler.filter_clusters_need_upgrade(clusters)
    upgraded_clusters = filter_result["upgraded_clusters"]
    skipped_clusters = filter_result["skipped_clusters"]

    # 如果所有集群都不需要升级，给出友好提示
    if not upgraded_clusters:
        # 构建详细的跳过信息
        skip_info_list = []
        for item in skipped_clusters[:5]:  # 最多显示5个
            skip_info_list.append(_("{}({})").format(item["cluster_domain"], item["reason"]))

        skip_info = ", ".join(skip_info_list)
        if len(skipped_clusters) > 5:
            skip_info += _("等 {} 个集群").format(len(skipped_clusters))

        raise Exception(_("所有集群版本已是最新或无法升级，无需升级。跳过的集群: {}").format(skip_info))

    # 更新 cluster_ids 为只包含需要升级的集群（跳过已经是目标版本的集群）
    cluster_ids = [cluster.id for cluster in upgraded_clusters]
    details["cluster_ids"] = cluster_ids

    # 4. 验证参数
    slz = TdbctlUpgradeSerializer(data=details)
    slz.is_valid(raise_exception=True)

    # 5. 创建单据（附带升级提示信息）
    # 构建单据备注，包含升级和跳过的集群信息
    remark_parts = [_("TdbCtl 升级到版本 {}").format(package.name)]
    if upgraded_clusters:
        remark_parts.append(_("需要升级的集群: {} 个").format(len(upgraded_clusters)))
    if skipped_clusters:
        remark_parts.append(_("跳过的集群: {} 个").format(len(skipped_clusters)))

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value,
        "remark": ", ".join(remark_parts),
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": details,
    }

    return Ticket.create_ticket(**ticket_param)
