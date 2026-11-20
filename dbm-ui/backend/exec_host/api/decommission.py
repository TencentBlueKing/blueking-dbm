# -*- coding: utf-8 -*-
"""下线 ExecHost 元数据并可选回收主机。"""

import logging

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Machine
from backend.exec_host.models import ExecHost, ExecHostStatus
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


@transaction.atomic
def decommission(exec_host_id: int, recycle_hosts: bool = True, updater: str = ""):
    exec_host = ExecHost.objects.select_for_update().get(id=exec_host_id)
    if exec_host.status == ExecHostStatus.DESTROYED.value:
        logger.info(_("ExecHost already decommissioned: id={}").format(exec_host_id))
        return
    ip = (exec_host.ip or "").strip()
    if ip:
        machine_obj = Machine.objects.filter(
            ip=ip,
            bk_cloud_id=exec_host.bk_cloud_id,
            machine_type=MachineType.EXEC_HOST.value,
        ).first()
        if machine_obj:
            if recycle_hosts and machine_obj.bk_host_id:
                CcManage(exec_host.bk_biz_id, ClusterType.ExecHost.value).recycle_host([machine_obj.bk_host_id])
            machine_obj.delete(keep_parents=True)
        else:
            logger.warning(
                _("skip recycle Machine for 执行机 id={} ip={}: no EXEC_HOST machine row").format(exec_host_id, ip)
            )

    exec_host.status = ExecHostStatus.DESTROYED.value
    exec_host.updater = updater
    exec_host.save(update_fields=["status", "updater", "update_at"])
    if recycle_hosts and ip:
        logger.info(_("ExecHost recycled to resource pool: {}").format(ip))
    logger.info(_("ExecHost decommissioned: id={}").format(exec_host_id))
