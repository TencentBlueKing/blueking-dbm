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
import traceback

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts
from backend.db_meta.enums import ClusterType, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Machine
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import mongo_create_ticket
from backend.db_services.redis.util import is_support_redis_auotfix
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

from .enums import AutofixStatus
from .models import RedisAutofixCore

logger = logging.getLogger("root")


def generate_autofix_ticket(fault_clusters: QuerySet):
    """自愈创建单据"""
    for cluster in fault_clusters:
        # 目前仅支持这三种架构
        if not is_support_redis_auotfix(cluster.cluster_type):
            logger.info(
                "cluster_autofix_ignore {}, not supported cluster_type {} ".format(
                    cluster.immute_domain, cluster.cluster_type
                )
            )
            cluster.status_version = get_random_string(12)
            cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
            cluster.deal_status = AutofixStatus.AF_IGNORE.value
            cluster.save(update_fields=["status_version", "deal_status", "update_at"])
            continue

        fault_machines = json.loads(cluster.fault_machines)
        mongos_list, mongod_list, redis_proxies, redis_slaves, cluster_ids = [], [], [], [], [cluster.cluster_id]
        for fault_machine in fault_machines:
            fault_ip = fault_machine["ip"]
            fault_obj = Machine.objects.filter(ip=fault_ip, bk_biz_id=cluster.bk_biz_id).get()
            fault_info = {
                "ip": fault_ip,
                "spec_id": fault_obj.spec_id,
                "bk_sub_zone": fault_obj.bk_sub_zone,
                "bk_sub_zone_id": fault_obj.bk_sub_zone_id,
                "city": fault_obj.bk_city.logical_city.name,
                "instance_type": fault_machine["instance_type"],
                "spec_config": fault_obj.spec_config,
                "cluster_type": cluster.cluster_type,
            }
            if fault_machine["instance_type"] in [MachineType.TWEMPROXY.value, MachineType.PREDIXY.value]:
                redis_proxies.append(fault_info)
            elif fault_machine["instance_type"] == MachineType.MONGOS.value:
                mongos_list.append(fault_info)
            elif fault_machine["instance_type"] in MachineTypeInstanceRoleMap[MachineType.MONGODB]:
                mongod_list.append(fault_info)
                if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
                    clusters = query_cluster_by_hosts(hosts=[fault_ip])
                    cluster_ids = [cls_obj["cluster_id"] for cls_obj in clusters]
            else:
                if fault_obj.cluster_type == ClusterType.TendisRedisInstance.value:
                    clusters = query_cluster_by_hosts(hosts=[fault_ip])
                    cluster_ids = [cls_obj["cluster_id"] for cls_obj in clusters]
                    cluster.immute_domain = ";".join([cls_obj["cluster"] for cls_obj in clusters])
                redis_slaves.append(fault_info)

        logger.info(
            "cluster_summary_fault {}; proxies:{}, storages:{}".format(
                cluster.immute_domain, redis_proxies, redis_slaves
            )
        )
        if mongos_list or mongod_list:
            mongo_create_ticket(cluster, cluster_ids, mongos_list, mongod_list)
            return
        create_ticket(cluster, cluster_ids, redis_proxies, redis_slaves)


def create_ticket(cluster: RedisAutofixCore, cluster_ids: list, redis_proxies: list, redis_slaves: list):
    """redis自愈创建单据"""
    details = {
        "ip_source": IpSource.RESOURCE_POOL.value,
        "infos": [
            {
                "cluster_ids": cluster_ids,
                "immute_domain": cluster.immute_domain,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "proxy": redis_proxies,
                "redis_slave": redis_slaves,
            }
        ],
    }
    logger.info("create ticket for cluster {} , details : {}".format(cluster.immute_domain, details))

    try:
        redisDBA = DBAdministrator.objects.get(bk_biz_id=cluster.bk_biz_id, db_type=DBType.Redis.value)
    except DBAdministrator.DoesNotExist:
        # 如果不存在，则取默认值
        redisDBA = DBAdministrator.objects.get(bk_biz_id=0, db_type=DBType.Redis.value)

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

    cluster.ticket_id = ticket.id
    cluster.status_version = get_random_string(12)
    cluster.deal_status = AutofixStatus.AF_WFLOW.value

    # 初始化builder类
    try:
        builder = BuilderFactory.create_builder(ticket)
        builder.patch_ticket_detail()
        builder.init_ticket_flows()
        TicketFlowManager(ticket=ticket).run_next_flow()
    except Exception as e:
        cluster.deal_status = AutofixStatus.AF_FAIL.value
        cluster.status_version = str(e)
        logger.error(
            "create ticket for cluster {} failed, details : {}::{}".format(
                cluster.immute_domain, details, traceback.format_exc()
            )
        )

    logger.info("create ticket for cluster {} failed, details : {}".format(cluster.immute_domain, details))
    cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
    cluster.save(update_fields=["ticket_id", "status_version", "deal_status", "update_at"])
