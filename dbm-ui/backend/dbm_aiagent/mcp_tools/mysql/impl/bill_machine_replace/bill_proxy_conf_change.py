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
from backend.db_meta.models import ProxyInstance, Spec
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.ticket.builders.mysql.mysql_proxy_conf_change import MysqlProxyConfChangeDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_proxy_conf_change(username: str, infos: List[dict]):
    """
    创建 TenDBHA proxy 升降配单据，支持多行，每行一个集群：
    - cluster_domain: 集群域名
    - target_spec_id: 目标规格 ID
    - labels: 资源标签 ID 列表（可选）
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    # 统一校验集群（确保同属一个业务）
    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 MySQL proxy 类型
    spec_ids = {info["target_spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.MySQL,
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
        target_spec_id = info["target_spec_id"]
        labels = info.get("labels") or []

        # 升降配是整集群操作：origin_proxies 必须是集群的全部 proxy
        # （flow 侧 MySQLProxySwitchForExtendValidator 会校验「是否传全集群全部机器」）
        proxy_objs = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).filter(cluster=cluster)
        if not proxy_objs.exists():
            raise DBMMcpBaseException(msg=_("集群无 proxy 实例: {}").format(cluster.immute_domain))

        # 校验目标规格与当前规格不同：当集群内所有 proxy 均为目标规格时，无需升降配
        current_spec_ids = set(proxy_objs.values_list("machine__spec_id", flat=True))
        if current_spec_ids == {target_spec_id}:
            raise DBMMcpBaseException(msg=_("目标规格与当前规格相同，无需升降配: {}").format(cluster.immute_domain))

        proxy_infos = []
        for pi in proxy_objs:
            proxy_infos.append(
                {
                    "bk_cloud_id": pi.machine.bk_cloud_id,
                    "ip": pi.machine.ip,
                    "bk_host_id": pi.machine.bk_host_id,
                    "bk_biz_id": bk_biz_id,
                    "port": 0,
                }
            )
        proxy_infos = list({pi["bk_host_id"]: pi for pi in proxy_infos}.values())

        # 升降配：目标规格由用户显式指定（区别于替换的「继承旧规格」）
        resource_spec = {"spec_id": target_spec_id, "count": len(proxy_infos), "labels": labels}

        built_infos.append(
            {
                "cluster_ids": [cluster.id],
                "origin_proxies": proxy_infos,
                "old_nodes": {
                    "proxy": proxy_infos,
                },
                "resource_spec": {"target_proxies": resource_spec},
            }
        )

    ticket_param = {
        "ticket_type": TicketType.MYSQL_PROXY_CONF_CHANGE,
        "remark": TicketType.MYSQL_PROXY_CONF_CHANGE,
        "creator": username,
        "helpers": [],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": built_infos,
            "disable_manual_confirm": False,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = MysqlProxyConfChangeDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_PROXY_CONF_CHANGE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]
