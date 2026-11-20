# -*- coding: utf-8 -*-
"""注册 JobHost 元数据：仅业务表 + Machine，不建 Cluster / Entry。"""

import logging

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import machine
from backend.db_meta.enums import MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Machine
from backend.db_meta.models.job_host import JobHost, JobHostStatus

logger = logging.getLogger("root")

_ACTIVE_STATUSES = (
    JobHostStatus.DEPLOYING.value,
    JobHostStatus.RUNNING.value,
    JobHostStatus.DESTROYING.value,
)


@transaction.atomic
def create(
    bk_biz_id: int,
    bk_cloud_id: int,
    name: str,
    ip: str,
    deploy_path: str = "",
    version: str = "",
    db_type: str = "",
    purpose: str = "",
    tags: dict = None,
    creator: str = "",
) -> JobHost:
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    bk_cloud_id = request_validator.validated_integer(bk_cloud_id)
    name = (name or "").strip()
    ip = (ip or "").strip()
    if not name:
        raise DBMetaException(message=_("JobHost name is empty"))
    if not ip:
        raise DBMetaException(message=_("JobHost ip is empty"))

    _assert_name_available(bk_biz_id=bk_biz_id, name=name)
    _assert_ip_available_for_job_host(bk_cloud_id=bk_cloud_id, ip=ip)
    machine.get_or_create(
        bk_cloud_id=bk_cloud_id,
        machines=[
            {
                "ip": ip,
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": MachineType.JOB_HOST.value,
            }
        ],
        creator=creator,
    )

    job_host = JobHost.objects.create(
        name=name,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        status=JobHostStatus.RUNNING.value,
        ip=ip,
        deploy_path=deploy_path or "",
        version=version or "",
        db_type=db_type or "",
        purpose=purpose or "",
        tags=tags or {},
        creator=creator,
        updater=creator,
    )
    logger.info(_("JobHost registered: name={} id={} ip={}").format(name, job_host.id, ip))
    return job_host


def _assert_name_available(bk_biz_id: int, name: str):
    exists = JobHost.objects.filter(
        bk_biz_id=bk_biz_id,
        name=name,
        status__in=_ACTIVE_STATUSES,
    ).exists()
    if exists:
        raise DBMetaException(message=_("业务 {} 下 JobHost 名称 {} 已存在或正在回收").format(bk_biz_id, name))


def _assert_ip_available_for_job_host(bk_cloud_id: int, ip: str):
    existing = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if existing and existing.machine_type != MachineType.JOB_HOST.value:
        raise DBMetaException(message=_("IP {} 已存在且机型为 {}，禁止注册为 JobHost").format(ip, existing.machine_type))
    active = JobHost.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id, status__in=_ACTIVE_STATUSES).first()
    if active:
        raise DBMetaException(
            message=_("IP {} 已有活跃 JobHost(id={}, name={})，请改用 job_host_id 复用，禁止重复注册").format(
                ip, active.id, active.name
            )
        )
