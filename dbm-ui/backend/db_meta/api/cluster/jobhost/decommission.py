# -*- coding: utf-8 -*-
"""下线 JobHost 元数据并可选回收主机。"""

import logging

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Machine
from backend.db_meta.models.job_host import JobHost, JobHostStatus
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


@transaction.atomic
def decommission(job_host_id: int, recycle_hosts: bool = True, updater: str = ""):
    job_host = JobHost.objects.get(id=job_host_id)
    ip = (job_host.ip or "").strip()
    if ip:
        machine_obj = Machine.objects.filter(
            ip=ip,
            bk_cloud_id=job_host.bk_cloud_id,
            machine_type=MachineType.JOB_HOST.value,
        ).first()
        if machine_obj:
            if recycle_hosts and machine_obj.bk_host_id:
                CcManage(job_host.bk_biz_id, ClusterType.JobHost.value).recycle_host([machine_obj.bk_host_id])
            machine_obj.delete(keep_parents=True)
        else:
            logger.warning(
                _("skip recycle Machine for JobHost id={} ip={}: no JOB_HOST machine row").format(job_host_id, ip)
            )

    job_host.status = JobHostStatus.DESTROYED.value
    job_host.updater = updater
    job_host.save(update_fields=["status", "updater", "update_at"])
    if recycle_hosts and ip:
        logger.info(_("JobHost recycled to resource pool: {}").format(ip))
    logger.info(_("JobHost decommissioned: id={}").format(job_host_id))
