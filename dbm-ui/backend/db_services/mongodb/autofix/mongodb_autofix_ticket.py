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
import logging

from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core import notify
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.redis.autofix.enums import AutofixStatus
from backend.db_services.redis.autofix.models import RedisAutofixCore
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


def mongos_get_resource_spec(cluster_id: int, mongos_list: list) -> dict:
    """获取申请机器规格信息，mongos申请机器，判断如果一半机器在同一园区，则排除该园区，否则任意园区"""

    include_or_exclue = True
    sub_zone_ids = []
    # 获取mongos的机器
    all_mongos = Cluster.objects.get(id=cluster_id).proxyinstance_set.all()
    # 获取健康mongos机器在园区的比重 {sub_zone_id: number}
    health_mongos_number = len(all_mongos) - len(mongos_list)  # 所有健康mongos的数量
    health_mongos_sub_zone = {}  # 健康mongos在每个园区的数量
    for mongos in all_mongos:
        if mongos.machine.ip in [host("ip") for host in mongos_list]:
            continue
        if health_mongos_sub_zone.get(str(mongos.machine.bk_sub_zone_id)):
            health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] = 0
        health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] += 1
    #  健康mongos在每个园区的机器数量占所有健康mongos的数量的百分比
    mongos_sub_zone_percent = {
        sub_zone: num / health_mongos_number for sub_zone, num in health_mongos_sub_zone.items()
    }
    for sub_zone, sub_zone_percent in mongos_sub_zone_percent.items():
        if sub_zone_percent >= 0.5:
            include_or_exclue = False
            sub_zone_ids.append(int(sub_zone))
            break

    resource_spec = {}
    for host in mongos_list:
        resource_spec.update(
            {
                host["ip"]: {
                    "spec_id": host["spec_id"],
                    "count": 1,
                    "spec_config": host["spec_config"],
                    "location_spec": {
                        "city": host["city"],
                        "sub_zone_ids": sub_zone_ids,
                        "include_or_exclue": include_or_exclue,
                    },
                }
            }
        )
    return resource_spec


def mongo_create_ticket(cluster: RedisAutofixCore, cluster_ids: list, mongos_list: list, mongod_list: list):
    """mongodb自愈创建单据 以cluster为维度"""

    # 获取dba
    mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.MongoDB.value)

    # 申请机器规格信息
    resource_spec = {}

    # 集群类型
    if mongos_list:
        cluster_type = mongos_list[0]["cluster_type"]
        # mongos的资源规格
        mongos_resource_spec = mongos_get_resource_spec(cluster_ids[0], mongos_list)
        resource_spec.update(mongos_resource_spec)
    if mongod_list:
        cluster_type = mongod_list[0]["cluster_type"]
        # mongodb的资源规格 TODO
        # mongod_resource_spec = mongod_get_resource_spec(cluster_ids[0], mongod_list)
        # mongod_resource_spec.update(mongod_resource_spec)

    if not resource_spec:
        return

    # 单据信息
    details = {
        "ip_source": IpSource.RESOURCE_POOL.value,
        "infos": [
            {
                "cluster_ids": cluster_ids,
                "immute_domain": cluster.immute_domain,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "resource_spec": resource_spec,
                "cluster_type": cluster_type,
                "mongos_list": mongos_list,
                "mongod_list": mongod_list,
            }
        ],
    }

    # 创建单据
    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_AUTOFIX.value,
        creator=mongodb_dba[0],
        bk_biz_id=cluster.bk_biz_id,
        remark=_("自动发起-自愈任务-{}".format(cluster.immute_domain)),
        details=details,
    )

    # 发送自愈消息提醒
    ip_list = []
    for host in mongos_list + mongod_list:
        ip_list.append(host["ip"])
    notify.send_msg.apply_async(args=(ticket.id,))

    # 回写tb_tendis_autofix_core表
    cluster.ticket_id = ticket.id
    cluster.status_version = get_random_string(12)
    cluster.deal_status = AutofixStatus.AF_WFLOW.value
    cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
    cluster.save(update_fields=["ticket_id", "status_version", "deal_status", "update_at"])
