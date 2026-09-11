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
import logging
from typing import Optional

from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core import notify
from backend.db_services.mongodb.autofix.enums import MongoAutofixLogEvent, MongoAutofixStatus
from backend.db_services.mongodb.autofix.log import write_autofix_log
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import build_mongod_list_from_core
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongod_fix_status_ticket as _create_mongod_fix_status_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongod_reload_ticket as _create_mongod_reload_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import mongo_create_ticket
from backend.db_services.mongodb.autofix.remark import autofix_core_tag
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


def _mongodb_dba(bk_biz_id: int) -> str:
    admins = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.MongoDB.value)
    if not admins:
        raise ValueError(f"no mongodb dba for biz {bk_biz_id}")
    return admins[0]


def create_autofix_pre_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """从 MongoAutofixCore 创建 MONGODB_AUTOFIX_PRE 确认单."""
    details = {
        "infos": [
            {
                "autofix_core_id": core.id,
                "ip": core.ip,
                "bk_host_id": core.bk_host_id,
                "bk_cloud_id": core.bk_cloud_id,
                "bk_biz_id": core.bk_biz_id,
                "cluster_ids": core.cluster_ids or [core.cluster_id],
                "ports": core.ports or [],
                "cluster_type": core.cluster_type,
                "immute_domain": core.immute_domain,
            }
        ]
    }
    creator = _mongodb_dba(core.bk_biz_id)
    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_AUTOFIX_PRE.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=_("自动发起-自愈确认-{}{}".format(core.immute_domain, autofix_core_tag(core.id))),
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    # discover 路径也会写 PRE_TICKET；此处补一行覆盖手工/Shell 注入场景（可重复，便于审计）
    write_autofix_log(
        MongoAutofixLogEvent.PRE_TICKET,
        f"created PRE ticket={ticket.id}",
        core=core,
        pre_ticket_id=ticket.id,
    )
    return ticket


def create_mongod_autofix_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 确认后出替换单（MONGODB_AUTOFIX），复用 mongo_create_ticket + resource_spec."""
    try:
        mongod_list = build_mongod_list_from_core(core)
        cluster_ids = core.cluster_ids or [core.cluster_id]
        mongo_create_ticket(core, cluster_ids, mongos_list=[], mongod_list=mongod_list)
        core.refresh_from_db()
        if core.ticket_id and core.ticket_id > 0:
            ticket = Ticket.objects.filter(id=core.ticket_id).first()
            write_autofix_log(
                MongoAutofixLogEvent.FOLLOWUP_TICKET,
                f"created AUTOFIX ticket={core.ticket_id}",
                core=core,
            )
            return ticket
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_mongod_autofix_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create AUTOFIX fail: {exc}", core=core)
        return None


def create_mongod_reload_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 确认后出重启单；委托 mongodb_autofix_ticket 实现并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongod_reload_ticket(core, creator=creator)
        if ticket is None:
            return None
        core.ticket_id = ticket.id
        core.deal_status = MongoAutofixStatus.TICKETED.value
        core.status_version = get_random_string(12)
        core.save(update_fields=["ticket_id", "deal_status", "status_version", "update_at"])
        write_autofix_log(
            MongoAutofixLogEvent.FOLLOWUP_TICKET,
            f"created RELOAD ticket={ticket.id}",
            core=core,
        )
        return ticket
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_mongod_reload_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create RELOAD fail: {exc}", core=core)
        return None


def create_mongod_fix_status_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 探测成功后出状态修复单；委托 mongodb_autofix_ticket 实现并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongod_fix_status_ticket(core, creator=creator)
        if ticket is None:
            return None
        core.ticket_id = ticket.id
        core.deal_status = MongoAutofixStatus.TICKETED.value
        core.status_version = get_random_string(12)
        core.save(update_fields=["ticket_id", "deal_status", "status_version", "update_at"])
        write_autofix_log(
            MongoAutofixLogEvent.FOLLOWUP_TICKET,
            f"created FIX_STATUS ticket={ticket.id}",
            core=core,
        )
        return ticket
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_mongod_fix_status_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create FIX_STATUS fail: {exc}", core=core)
        return None
