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
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import ProxyInstance, Spec
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.ticket.builders.tendbcluster.tendb_spider_conf_up_down import SpiderConfUpDownDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

# 升降配仅支持接入层的 master / slave 两种角色（不含 spider_ctl / spider_mnt / spider_slave_mnt）
SUPPORT_SPIDER_ROLES = [
    TenDBClusterSpiderRole.SPIDER_MASTER.value,
    TenDBClusterSpiderRole.SPIDER_SLAVE.value,
]


def bill_spider_conf_change(username: str, infos: List[dict]):
    """
    创建 TenDBCluster 接入层（spider）升降配单据，支持多行，每行一个集群：
    - cluster_domain: 集群域名
    - spider_role: 接入层角色（spider_master / spider_slave）
    - target_spec_id: 目标规格 ID
    - labels: 资源标签 ID 列表（可选）

    注意：升降配是整集群操作，同一集群只能出现一行（锁定单一 spider 角色）。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBCluster)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 spider（proxy）类型
    spec_ids = {info["target_spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.TenDBCluster,
        spec_machine_type=SpecMachineType.PROXY,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        spider_role = info["spider_role"]
        target_spec_id = info["target_spec_id"]
        labels = info.get("labels") or []

        if spider_role not in SUPPORT_SPIDER_ROLES:
            raise DBMMcpBaseException(msg=_("不支持的 spider 角色: {}，仅支持 {}").format(spider_role, SUPPORT_SPIDER_ROLES))

        # 升降配是整集群操作：该角色的全部 spider 都要升降配
        this_role_spiders = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).filter(
            cluster=cluster, tendbclusterspiderext__spider_role=spider_role
        )
        if not this_role_spiders.exists():
            raise DBMMcpBaseException(msg=_("集群 {} 无 {} 角色实例").format(cluster.immute_domain, spider_role))

        # 校验目标规格与当前规格不同：当该角色全部 spider 均为目标规格时，无需升降配
        current_spec_ids = set(this_role_spiders.values_list("machine__spec_id", flat=True))
        if current_spec_ids == {target_spec_id}:
            raise DBMMcpBaseException(msg=_("目标规格与当前规格相同，无需升降配: {}").format(cluster.immute_domain))

        # 当前规格对象映射：spider 旧实例需携带 spec（含规格名），详情页「当前规格」列展示用
        current_spec_map = {spec.spec_id: spec for spec in Spec.objects.filter(spec_id__in=current_spec_ids)}

        spider_old_ip_list = []
        for si in this_role_spiders:
            spider_old_ip_list.append(
                {
                    "bk_cloud_id": si.machine.bk_cloud_id,
                    "ip": si.machine.ip,
                    "bk_host_id": si.machine.bk_host_id,
                    "bk_biz_id": bk_biz_id,
                    "port": si.port,
                    "spec": current_spec_map[si.machine.spec_id].get_spec_info(),
                }
            )

        built_infos.append(
            {
                "cluster_id": cluster.id,
                "resource_spec": {
                    spider_role: {
                        "spec_id": target_spec_id,
                        "count": len(spider_old_ip_list),
                        "labels": labels,
                    }
                },
                "spider_old_ip_list": spider_old_ip_list,
                "old_nodes": {spider_role: spider_old_ip_list},
                "switch_spider_role": spider_role,
            }
        )

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN,
        "remark": TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN,
        "creator": username,
        "helpers": [],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "disable_manual_confirm": False,
            "infos": built_infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = SpiderConfUpDownDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]
