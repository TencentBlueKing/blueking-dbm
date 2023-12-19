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
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
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
        fault_machines = json.loads(cluster.fault_machines)
        redis_proxies, redis_slaves = [], []
        for fault_machine in fault_machines:
            fault_ip = fault_machine["ip"]
            fault_obj = Machine.objects.filter(ip=fault_ip, bk_biz_id=cluster.bk_biz_id).get()
            fault_info = {"ip": fault_ip, "spec_id": fault_obj.spec_id, "bk_sub_zone": fault_obj.bk_sub_zone}
            if fault_machine["instance_type"] in [MachineType.TWEMPROXY.value, MachineType.PREDIXY.value]:
                redis_proxies.append(fault_info)
            else:
                redis_slaves.append(fault_info)

        logger.info(
            "cluster_summary_fault {}; proxies:{}, storages:{}".format(
                cluster.immute_domain, redis_proxies, redis_slaves
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
        remark=_("自动发起-自愈任务-{}".format(cluster.immute_domain)),
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
