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

from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core import notify
from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance
from backend.db_services.mongodb.autofix import ctl as autofix_ctl
from backend.db_services.mongodb.autofix.enums import (
    MONGO_AUTOFIX_ACTIVE_STATUSES,
    MongoAutofixLogEvent,
    MongoAutofixStatus,
)
from backend.db_services.mongodb.autofix.log import write_autofix_log
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    build_mongod_list_from_core,
    build_mongos_list_from_core,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongo_ensure_start_ticket as _create_mongo_ensure_start_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongo_fix_status_ticket as _create_mongo_fix_status_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongo_manual_ticket as _create_mongo_manual_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    create_mongo_reload_ticket as _create_mongo_reload_ticket,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import is_mongos_core, mongo_create_ticket
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
    mongos = is_mongos_core(core)
    machine_type = MachineType.MONGOS.value if mongos else ""
    if not machine_type:
        for fm in core.fault_machines or []:
            if isinstance(fm, dict) and fm.get("machine_type"):
                machine_type = fm["machine_type"]
                break
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
                "machine_type": machine_type,
                "roles": core.roles or [],
                "wait_gse_forever": mongos,
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


def create_one_mongos_autofix_pre(
    *,
    ip: str,
    bk_host_id: int = 0,
    bk_biz_id: int,
    bk_cloud_id: int,
    cluster_id: int,
    cluster_type: str,
    immute_domain: str,
    city: str = "",
) -> Optional[Ticket]:
    """按 mongos 机器写 MongoAutofixCore 并出 PRE。已有进行中 Core 则跳过。"""
    qs = ProxyInstance.objects.select_related("machine").prefetch_related("cluster")
    if bk_host_id:
        proxies = list(qs.filter(machine__bk_host_id=bk_host_id))
    else:
        proxies = list(qs.filter(machine__ip=ip, machine__bk_biz_id=bk_biz_id))
    proxies = [
        p
        for p in proxies
        if p.machine_type == MachineType.MONGOS.value
        or getattr(p.machine, "machine_type", "") == MachineType.MONGOS.value
    ] or proxies
    if not proxies:
        logger.error("create mongos PRE skip, proxy missing ip=%s host_id=%s", ip, bk_host_id)
        return None
    if MongoAutofixCore.objects.filter(ip=ip, deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES).exists():
        logger.info("create mongos PRE skip, active core exists ip=%s", ip)
        return None
    primary = proxies[0]
    cluster_obj = primary.cluster.first()
    ports = sorted({p.port for p in proxies})
    cluster_ids = sorted({c.id for p in proxies for c in p.cluster.all()})
    if not cluster_ids:
        cluster_ids = [cluster_id]
    resolved_cluster_id = cluster_obj.id if cluster_obj else cluster_id
    resolved_domain = cluster_obj.immute_domain if cluster_obj else immute_domain
    fault_machines = [
        {
            "ip": ip,
            "bk_host_id": primary.machine.bk_host_id,
            "ports": ports,
            "roles": [MachineType.MONGOS.value],
            "machine_type": MachineType.MONGOS.value,
        }
    ]
    core = MongoAutofixCore.objects.create(
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        cluster_id=resolved_cluster_id,
        cluster_type=cluster_type,
        immute_domain=resolved_domain,
        fault_machines=fault_machines,
        ip=ip,
        bk_host_id=primary.machine.bk_host_id,
        cluster_ids=cluster_ids,
        ports=ports,
        roles=[MachineType.MONGOS.value],
        bk_city=city or "",
        bk_sub_zone_id=primary.machine.bk_sub_zone_id or 0,
        deal_status=MongoAutofixStatus.DETECTED.value,
        status_version=get_random_string(12),
        detected_at=timezone.now(),
    )
    write_autofix_log(
        MongoAutofixLogEvent.DETECTED,
        f"detected mongos fault ip={ip} ports={ports}",
        core=core,
        context={"ports": ports, "roles": [MachineType.MONGOS.value]},
    )
    if autofix_ctl.is_dry_run():
        write_autofix_log(MongoAutofixLogEvent.DETECTED, "dry_run: skip PRE ticket", core=core)
        return None
    try:
        ticket = create_autofix_pre_ticket(core)
    except Exception as exc:  # noqa: BLE001
        logger.exception("create mongos PRE fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create PRE failed: {exc}", core=core)
        return None
    if ticket is None:
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.save(update_fields=["deal_status", "update_at"])
        return None
    core.pre_ticket_id = ticket.id
    core.deal_status = MongoAutofixStatus.PRE_RUNNING.value
    core.save(update_fields=["pre_ticket_id", "deal_status", "update_at"])
    return ticket


def create_mongo_autofix_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 确认后出替换单（MONGODB_AUTOFIX），复用 mongo_create_ticket + resource_spec."""
    try:
        cluster_ids = core.cluster_ids or [core.cluster_id]
        if is_mongos_core(core):
            mongo_create_ticket(core, cluster_ids, mongos_list=build_mongos_list_from_core(core), mongod_list=[])
        else:
            mongod_list = build_mongod_list_from_core(core)
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
        logger.exception("create_mongo_autofix_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create AUTOFIX fail: {exc}", core=core)
        return None


def create_mongo_reload_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 确认后出重启单；委托 mongodb_autofix_ticket 实现并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongo_reload_ticket(core, creator=creator)
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
        logger.exception("create_mongo_reload_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create RELOAD fail: {exc}", core=core)
        return None


def create_mongo_ensure_start_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE process_bad 后出进程拉起单；委托 mongodb_autofix_ticket 实现并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongo_ensure_start_ticket(core, creator=creator)
        if ticket is None:
            return None
        core.ticket_id = ticket.id
        core.deal_status = MongoAutofixStatus.TICKETED.value
        core.status_version = get_random_string(12)
        core.save(update_fields=["ticket_id", "deal_status", "status_version", "update_at"])
        write_autofix_log(
            MongoAutofixLogEvent.FOLLOWUP_TICKET,
            f"created ENSURE_START ticket={ticket.id}",
            core=core,
        )
        return ticket
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_mongo_ensure_start_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create ENSURE_START fail: {exc}", core=core)
        return None


def create_mongo_fix_status_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE 探测成功后出状态修复单；委托 mongodb_autofix_ticket 实现并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongo_fix_status_ticket(core, creator=creator)
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
        logger.exception("create_mongo_fix_status_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create FIX_STATUS fail: {exc}", core=core)
        return None


def create_mongo_manual_ticket(core: MongoAutofixCore) -> Optional[Ticket]:
    """PRE auth_error / gse_inconclusive 后出人工处理单；委托 mongodb_autofix_ticket 并回写 Core."""
    try:
        creator = _mongodb_dba(core.bk_biz_id)
        ticket = _create_mongo_manual_ticket(core, creator=creator)
        if ticket is None:
            return None
        core.ticket_id = ticket.id
        core.deal_status = MongoAutofixStatus.TICKETED.value
        core.status_version = get_random_string(12)
        core.save(update_fields=["ticket_id", "deal_status", "status_version", "update_at"])
        write_autofix_log(
            MongoAutofixLogEvent.FOLLOWUP_TICKET,
            f"created MANUAL ticket={ticket.id}",
            core=core,
        )
        return ticket
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_mongo_manual_ticket fail core=%s err=%s", core.id, exc)
        core.deal_status = MongoAutofixStatus.FAIL.value
        core.status_version = str(exc)[:64]
        core.save(update_fields=["deal_status", "status_version", "update_at"])
        write_autofix_log(MongoAutofixLogEvent.ERROR, f"create MANUAL fail: {exc}", core=core)
        return None
