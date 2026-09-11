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
import time
from datetime import datetime
from typing import List, Optional, Tuple

from django.utils import timezone
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import DRSApi, JobApi
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import StorageInstance
from backend.db_services.mongodb.autofix.enums import MongoAutofixLogEvent, MongoAutofixStatus
from backend.db_services.mongodb.autofix.log import write_autofix_log
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    build_mongod_list_from_core,
    create_mongod_fix_status_ticket,
    create_mongod_reload_ticket,
    mongo_create_ticket,
)
from backend.db_services.mongodb.autofix.triage import (
    ACTION_FIX_STATUS,
    ACTION_IGNORE,
    ACTION_RELOAD,
    ACTION_REPLACE,
    decide_autofix_action,
    is_drs_auth_error,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.mongodb_script_template import mongodb_fast_execute_script_common_kwargs
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")

JOB_POLL_INTERVAL = 2
JOB_POLL_MAX_RETRIES = 15
GSE_SCRIPT_TIMEOUT = 30


def _probe_gse_alive(ip: str, bk_cloud_id: int) -> bool:
    """GSE/Job bash: echo + hostname. Fail/timeout => unreachable."""
    script = "echo autofix_pre_alive; hostname"
    body = {
        **mongodb_fast_execute_script_common_kwargs,
        "timeout": GSE_SCRIPT_TIMEOUT,
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": f"mongo_autofix_pre_gse_{ip}",
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"ip": ip, "bk_cloud_id": bk_cloud_id}]},
    }
    try:
        resp = JobApi.fast_execute_script(body, raw=True, use_admin=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mongo autofix pre gse issue fail ip=%s err=%s", ip, exc)
        return False

    if not resp.get("result") or not resp.get("data"):
        logger.warning("mongo autofix pre gse issue bad resp ip=%s resp=%s", ip, resp)
        return False

    job_instance_id = resp["data"]["job_instance_id"]
    bk_biz_id = resp["data"].get("bk_biz_id") or env.JOB_BLUEKING_BIZ_ID
    for _i in range(JOB_POLL_MAX_RETRIES):
        try:
            status_resp = JobApi.get_job_instance_status(
                {
                    "bk_scope_type": "biz_set",
                    "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                    "bk_biz_id": bk_biz_id,
                    "job_instance_id": job_instance_id,
                    "return_ip_result": True,
                },
                raw=True,
                use_admin=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mongo autofix pre gse poll fail ip=%s err=%s", ip, exc)
            return False

        data = (status_resp or {}).get("data") or {}
        if data.get("finished"):
            # job status: 3 success, others fail
            job_status = (data.get("job_instance") or {}).get("status")
            return job_status == 3
        time.sleep(JOB_POLL_INTERVAL)

    logger.warning("mongo autofix pre gse timeout ip=%s job=%s", ip, job_instance_id)
    return False


def _probe_datadir_writable(ip: str, bk_cloud_id: int) -> Optional[bool]:
    """
    Optional: try write under common mongo data mounts.
    Returns False if write fails while GSE is up; None if probe inconclusive/skipped.
    """
    script = r"""
set -e
ok=0
for d in /data1/mongodb /data/mongodb /data1 /data; do
  if [ -d "$d" ] && [ -w "$d" ]; then
    f="$d/.autofix_pre_write_$$"
    if echo ok > "$f" 2>/dev/null; then
      rm -f "$f" 2>/dev/null || true
      ok=1
      break
    fi
  fi
done
if [ "$ok" = "1" ]; then
  echo DATADIR_WRITABLE_OK
  exit 0
fi
echo DATADIR_WRITABLE_FAIL
exit 2
"""
    body = {
        **mongodb_fast_execute_script_common_kwargs,
        "timeout": GSE_SCRIPT_TIMEOUT,
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": f"mongo_autofix_pre_datadir_{ip}",
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"ip": ip, "bk_cloud_id": bk_cloud_id}]},
    }
    try:
        resp = JobApi.fast_execute_script(body, raw=True, use_admin=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mongo autofix pre datadir probe issue fail ip=%s err=%s", ip, exc)
        return None

    if not resp.get("result") or not resp.get("data"):
        return None

    job_instance_id = resp["data"]["job_instance_id"]
    bk_biz_id = resp["data"].get("bk_biz_id") or env.JOB_BLUEKING_BIZ_ID
    for _i in range(JOB_POLL_MAX_RETRIES):
        try:
            status_resp = JobApi.get_job_instance_status(
                {
                    "bk_scope_type": "biz_set",
                    "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                    "bk_biz_id": bk_biz_id,
                    "job_instance_id": job_instance_id,
                    "return_ip_result": True,
                },
                raw=True,
                use_admin=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mongo autofix pre datadir poll fail ip=%s err=%s", ip, exc)
            return None

        data = (status_resp or {}).get("data") or {}
        if data.get("finished"):
            job_status = (data.get("job_instance") or {}).get("status")
            if job_status == 3:
                return True
            # exit 2 / fail => not writable
            return False
        time.sleep(JOB_POLL_INTERVAL)
    return None


def _probe_drs_login(cluster_id: int, ip: str, ports: List[int]) -> Tuple[bool, bool]:
    """
    DRS direct login on fault ip:port.
    Returns (drs_ok, drs_auth_error). Any non-auth failure => drs_ok=False.
    """
    if not ports:
        return False, False

    auth_error = False
    all_ok = True
    session = f"autofix_pre:{datetime.now(timezone.utc).replace(microsecond=0)}"
    for port in ports:
        addr = f"{ip}:{port}"
        try:
            param = MongoUtil.get_mongodb_DRS_args_direct(
                cluster_id=cluster_id, addr=addr, session=session, command="ping", timeout=15
            )
            DRSApi.mongodb_rpc(param)
        except Exception as exc:  # noqa: BLE001
            msg = str(getattr(exc, "message", "") or exc)
            logger.warning("mongo autofix pre drs fail addr=%s err=%s", addr, msg)
            if is_drs_auth_error(msg):
                auth_error = True
            all_ok = False
    if auth_error:
        return False, True
    return all_ok, False


def _mark_instances_unavailable(ip: str, ports: List[int], bk_host_id: int = 0) -> None:
    qs = StorageInstance.objects.filter(machine__ip=ip)
    if ports:
        qs = qs.filter(port__in=ports)
    if bk_host_id:
        qs = qs.filter(machine__bk_host_id=bk_host_id)
    updated = qs.update(status=InstanceStatus.UNAVAILABLE.value)
    logger.info("mongo autofix pre mark UNAVAILABLE ip=%s ports=%s count=%s", ip, ports, updated)


def _link_pre_related_ticket(pre_ticket_id, followup_ticket: Optional[Ticket], log_fn=None) -> None:
    """
    将后续替换/重启/状态修复单挂到 PRE 确认单上（Delivery Flow + related_ticket）。
    done=True：PRE 即将结束，避免插入 PENDING Flow 干扰 current_flow。
    """
    if not pre_ticket_id or not followup_ticket:
        return
    try:
        pre_ticket = Ticket.objects.get(id=pre_ticket_id)
        pre_ticket.add_related_ticket(followup_ticket, done=True)
        msg = f"mongo autofix pre linked related_ticket={followup_ticket.id} to pre={pre_ticket_id}"
        logger.info(msg)
        if log_fn:
            log_fn(msg)
    except Ticket.DoesNotExist:
        logger.warning("mongo autofix pre ticket missing id=%s, skip relate", pre_ticket_id)
    except Exception as exc:  # noqa: BLE001 — 关联失败不影响主流程
        logger.warning("mongo autofix pre relate fail pre=%s follow=%s err=%s", pre_ticket_id, followup_ticket.id, exc)


def _unlock_pre_for_followup(pre_ticket_id, cluster_ids: List[int], log_fn=None) -> None:
    """
    PRE Inner 仍在 RUNNING 时出后续单会撞集群互斥；先对 PRE 的操作记录解锁 RELOAD/FIX_STATUS/AUTOFIX。
    """
    if not pre_ticket_id:
        return
    unlock_types = [
        TicketType.MONGODB_INSTANCE_RELOAD.value,
        TicketType.MONGODB_INSTANCE_FIX_STATUS.value,
        TicketType.MONGODB_AUTOFIX.value,
        TicketType.MONGODB_DEFERRED_DEINSTALL.value,
    ]
    qs = ClusterOperateRecord.objects.filter(ticket_id=pre_ticket_id)
    if cluster_ids:
        qs = qs.filter(cluster_id__in=cluster_ids)
    for record in qs:
        record.unlock_ticket_type_operations(unlock_types)
        msg = f"mongo autofix pre unlock cluster={record.cluster_id} " f"for {unlock_types} on ticket={pre_ticket_id}"
        logger.info(msg)
        if log_fn:
            log_fn(msg)


class MongoAutofixPreTriageService(BaseService):
    """PRE triage: disk/GSE/DRS → follow-up ticket."""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        global_data = data.get_one_of_inputs("global_data") or {}
        infos = kwargs.get("infos") or global_data.get("infos") or []
        if not infos:
            self.log_error("mongo autofix pre: empty infos")
            return False

        for info in infos:
            if not self._handle_one(info, global_data):
                return False
        return True

    def _handle_one(self, info: dict, global_data: dict) -> bool:
        core_id = info.get("autofix_core_id")
        try:
            core = MongoAutofixCore.objects.get(id=core_id)
        except MongoAutofixCore.DoesNotExist:
            self.log_error(f"MongoAutofixCore id={core_id} not found")
            return False

        ip = info.get("ip") or core.ip
        bk_cloud_id = info.get("bk_cloud_id", core.bk_cloud_id)
        bk_host_id = info.get("bk_host_id") or core.bk_host_id
        ports = info.get("ports") or core.ports or []
        cluster_ids = info.get("cluster_ids") or core.cluster_ids or [core.cluster_id]
        cluster_id = info.get("cluster_id") or core.cluster_id or (cluster_ids[0] if cluster_ids else 0)

        disk_rw_ok = info.get("disk_rw_ok", core.disk_rw_ok)
        if disk_rw_ok is None:
            disk_rw_ok = -1

        gse_alive = _probe_gse_alive(ip, bk_cloud_id)
        datadir_writable = None
        if gse_alive:
            datadir_writable = _probe_datadir_writable(ip, bk_cloud_id)

        drs_ok, drs_auth_error = False, False
        # skip DRS when already decided replace by disk/gse to save time
        if disk_rw_ok != 0 and gse_alive and datadir_writable is not False:
            drs_ok, drs_auth_error = _probe_drs_login(cluster_id, ip, ports)

        action, confirm_result = decide_autofix_action(
            disk_rw_ok=disk_rw_ok,
            gse_alive=gse_alive,
            datadir_writable=datadir_writable,
            drs_ok=drs_ok,
            drs_auth_error=drs_auth_error,
        )
        self.log_info(
            f"autofix pre triage ip={ip} action={action} confirm={confirm_result} "
            f"disk_rw_ok={disk_rw_ok} gse={gse_alive} datadir={datadir_writable} "
            f"drs_ok={drs_ok} auth_err={drs_auth_error}"
        )
        write_autofix_log(
            MongoAutofixLogEvent.TRIAGE,
            f"action={action} confirm={confirm_result}",
            core=core,
            context={
                "action": action,
                "confirm_result": confirm_result,
                "disk_rw_ok": disk_rw_ok,
                "gse_alive": gse_alive,
                "datadir_writable": datadir_writable,
                "drs_ok": drs_ok,
                "drs_auth_error": drs_auth_error,
            },
            confirm_result=confirm_result,
        )

        core.confirm_result = confirm_result
        if action == ACTION_IGNORE:
            core.deal_status = MongoAutofixStatus.IGNORE.value
            core.save(update_fields=["confirm_result", "deal_status", "update_at"])
            write_autofix_log(MongoAutofixLogEvent.IGNORE, f"ignored: {confirm_result}", core=core)
            return True

        # protocol: mark UNAVAILABLE before creating follow-up
        _mark_instances_unavailable(ip=ip, ports=ports, bk_host_id=bk_host_id)

        creator = global_data.get("created_by") or "admin"
        pre_ticket_id = global_data.get("uid") or core.pre_ticket_id
        followup_ticket = None
        # PRE 仍持有集群互斥锁时，先放行后续替换/重启
        _unlock_pre_for_followup(pre_ticket_id, cluster_ids, log_fn=self.log_info)
        try:
            if action == ACTION_REPLACE:
                mongod_list = build_mongod_list_from_core(core)
                followup_ticket = mongo_create_ticket(core, cluster_ids, mongos_list=[], mongod_list=mongod_list)
                core.refresh_from_db()
                core.confirm_result = confirm_result
                if not followup_ticket:
                    core.deal_status = MongoAutofixStatus.FAIL.value
                    core.status_version = "empty_resource_spec_or_create_fail"
                core.save(update_fields=["confirm_result", "deal_status", "status_version", "update_at"])
            elif action == ACTION_RELOAD:
                followup_ticket = create_mongod_reload_ticket(core, creator=creator)
                if followup_ticket:
                    core.ticket_id = followup_ticket.id
                    core.deal_status = MongoAutofixStatus.TICKETED.value
                else:
                    core.deal_status = MongoAutofixStatus.FAIL.value
                core.confirm_result = confirm_result
                core.save(update_fields=["confirm_result", "ticket_id", "deal_status", "update_at"])
            elif action == ACTION_FIX_STATUS:
                followup_ticket = create_mongod_fix_status_ticket(core, creator=creator)
                if followup_ticket:
                    core.ticket_id = followup_ticket.id
                    core.deal_status = MongoAutofixStatus.TICKETED.value
                else:
                    core.deal_status = MongoAutofixStatus.FAIL.value
                core.confirm_result = confirm_result
                core.save(update_fields=["confirm_result", "ticket_id", "deal_status", "update_at"])
            else:
                core.deal_status = MongoAutofixStatus.FAIL.value
                core.confirm_result = confirm_result
                core.save(update_fields=["confirm_result", "deal_status", "update_at"])
                self.log_error(f"unknown action={action}")
                write_autofix_log(MongoAutofixLogEvent.ERROR, f"unknown action={action}", core=core)
                return False
        except Exception as exc:  # noqa: BLE001
            self.log_error(f"create follow-up ticket fail: {exc}")
            core.confirm_result = confirm_result
            core.deal_status = MongoAutofixStatus.FAIL.value
            core.status_version = str(exc)[:64]
            core.save(update_fields=["confirm_result", "deal_status", "status_version", "update_at"])
            write_autofix_log(MongoAutofixLogEvent.ERROR, f"create follow-up fail: {exc}", core=core)
            return False

        if followup_ticket:
            write_autofix_log(
                MongoAutofixLogEvent.FOLLOWUP_TICKET,
                f"created follow-up ticket={followup_ticket.id} action={action}",
                core=core,
                context={"action": action, "ticket_id": followup_ticket.id},
            )
        elif core.deal_status == MongoAutofixStatus.FAIL.value:
            write_autofix_log(MongoAutofixLogEvent.ERROR, "follow-up ticket create failed", core=core)

        _link_pre_related_ticket(pre_ticket_id, followup_ticket, log_fn=self.log_info)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoAutofixPreTriageComponent(Component):
    name = __name__
    code = "mongo_autofix_pre_triage"
    bound_service = MongoAutofixPreTriageService
