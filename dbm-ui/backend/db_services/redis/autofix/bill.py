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
import datetime
import json
import logging

from django.db.models import QuerySet
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.db_meta.enums import InstanceInnerRole, MachineType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

from .enums import AutofixStatus
from .models import RedisAutofixCore

logger = logging.getLogger("root")


def generate_autofix_ticket(fault_clusters: QuerySet):
    for cluster in fault_clusters:
        cluster_zones = load_cluster_arch_zone(cluster)
        fault_machines = json.loads(cluster.fault_machines)
        # {"instance_type": swiched_host.instance_type, "ip": swiched_host.ip}
        proxy_distrubt, redis_proxies, redis_slaves = cluster_zones["proxy_distrubt"], [], []
        for fault_machine in fault_machines:
            fault_ip = fault_machine["ip"]
            if fault_machine["instance_type"] in [MachineType.TWEMPROXY.value, MachineType.PREDIXY.value]:
                proxy_zone = cluster_zones["proxy_zones"][fault_ip]
                proxy_distrubt[proxy_zone["bk_sub_zone_id"]] -= 1
                redis_proxies.append({"ip": fault_ip, "spec_id": proxy_zone["spec_id"]})
            else:
                zone_info = cluster_zones["storage_zones"][fault_ip]
                redis_slaves.append({"ip": fault_ip, "spec_id": zone_info["spec_id"]})

        logger.info(
            "cluster summary fault {} proxies:{},curr available zone distrubt:{},storages:{}".format(
                cluster.immute_domain, len(redis_proxies), proxy_distrubt, len(redis_slaves)
            )
        )
        create_ticket(cluster, redis_proxies, redis_slaves)


def create_ticket(cluster: RedisAutofixCore, redis_proxies: list, redis_slaves: list):
    details = {
        "ip_source": IpSource.RESOURCE_POOL.value,
        "infos": [
            {
                "cluster_id": cluster.cluster_id,
                "immute_domain": cluster.immute_domain,
                "bk_cloud_id": cluster.bk_cloud_id,
                "proxy": redis_proxies,
                "redis_slave": redis_slaves,
            }
        ],
    }
    logger.info("create ticket for cluster {} , details : {}".format(cluster.immute_domain, details))
    redisDBA = DBAdministrator.objects.get(bk_biz_id=cluster.bk_biz_id, db_type=DBType.Redis.value)
    ticket = Ticket.objects.create(
        creator=redisDBA.users[0],
        bk_biz_id=cluster.bk_biz_id,
        ticket_type=TicketType.REDIS_CLUSTER_AUTOFIX.value,
        group=DBType.Redis.value,
        status=TicketStatus.PENDING.value,
        remark=_("自动发起-自愈任务-{cluster.immute_domain}"),
        details=details,
        is_reviewed=True,
    )

    # 初始化builder类
    builder = BuilderFactory.create_builder(ticket)
    builder.patch_ticket_detail()
    builder.init_ticket_flows()

    cluster.ticket_id = ticket.id
    cluster.status_version = get_random_string(12)
    cluster.update_at = datetime2str(datetime.datetime.now())
    cluster.deal_status = AutofixStatus.AF_WFLOW.value
    cluster.save(update_fields=["ticket_id", "status_version", "deal_status", "update_at"])

    TicketFlowManager(ticket=ticket).run_next_flow()


def load_cluster_arch_zone(cluster: RedisAutofixCore):
    cluster_obj = Cluster.objects.get(bk_biz_id=cluster.bk_biz_id, id=cluster.cluster_id)
    # 构造园区分布     bk_sub_zone: bk_sub_zone_id:
    proxy_zones, proxy_distrubt = {}, {}
    for proxy in cluster_obj.proxyinstance_set.all():
        proxy_zones[proxy.machine.ip] = {
            "spec_id": proxy.machine.spec_id,
            "proxy_ip": proxy.machine.ip,
            "bk_sub_zone": proxy.machine.bk_sub_zone,
            "bk_sub_zone_id": proxy.machine.bk_sub_zone_id,
        }
        if not proxy_distrubt.get(proxy.machine.bk_sub_zone_id):
            proxy_distrubt[proxy.machine.bk_sub_zone_id] = 0
        proxy_distrubt[proxy.machine.bk_sub_zone_id] += 1

    storage_zones = {}
    for master in cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value):
        slave_obj = master.as_ejector.get().receiver
        slave_ip = slave_obj.machine.ip
        storage_zones[slave_ip] = {
            "slave_ip": slave_ip,
            "bk_sub_zone": slave_obj.machine.bk_sub_zone,
            "bk_sub_zone_id": slave_obj.machine.bk_sub_zone_id,
            "spec_id": slave_obj.machine.spec_id,
            "master_ip": master.machine.ip,
            "master_zone": master.machine.bk_sub_zone,
            "master_zone_id": master.machine.bk_sub_zone_id,
        }

    return {
        "storage_zones": storage_zones,
        "proxy_zones": proxy_zones,
        "region": cluster_obj.region,
        "proxy_distrubt": proxy_distrubt,
    }
