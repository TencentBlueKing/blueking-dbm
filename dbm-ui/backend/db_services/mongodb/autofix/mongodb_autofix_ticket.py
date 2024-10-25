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
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.redis.autofix.enums import AutofixStatus
from backend.db_services.redis.autofix.models import RedisAutofixCore
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


def get_resource_spec(mongos_list: list, mongod_list: list) -> dict:
    """获取申请机器规格信息，采用故障机与新机器园区相对应"""

    resource_spec = {}
    for mongos in mongos_list:
        resource_spec.update(
            {
                mongos["ip"]: {
                    "spec_id": mongos["spec_id"],
                    "count": 1,
                    "spec_config": mongos["spec_config"],
                    "Location_spec": {"city": mongos["city"], "sub_zone_ids": [mongos["bk_sub_zone_id"]]},
                }
            }
        )
    # mongod自愈
    for mongod in mongod_list:
        resource_spec.update(
            {
                mongod["ip"]: {
                    "spec_id": mongod["spec_id"],
                    "count": 1,
                    "spec_config": mongod["spec_config"],
                    "Location_spec": {"city": mongod["city"], "sub_zone_ids": [mongod["bk_sub_zone_id"]]},
                }
            }
        )
    return resource_spec


def mongo_create_ticket(cluster: RedisAutofixCore, cluster_ids: list, mongos_list: list, mongod_list: list):
    """mongodb自愈创建单据"""

    # 获取dba
    mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.MongoDB.value)

    # 申请机器规格信息
    resource_spec = get_resource_spec(mongos_list, mongod_list)
    if not resource_spec:
        return
    # 集群类型
    if mongos_list:
        cluster_type = mongos_list[0]["cluster_type"]
    if mongod_list:
        cluster_type = mongod_list[0]["cluster_type"]
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
    cluster.ticket_id = ticket.id
    cluster.status_version = get_random_string(12)
    cluster.deal_status = AutofixStatus.AF_WFLOW.value
    cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
    cluster.save(update_fields=["ticket_id", "status_version", "deal_status", "update_at"])
