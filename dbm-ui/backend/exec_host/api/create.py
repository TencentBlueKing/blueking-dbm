# -*- coding: utf-8 -*-
"""注册执行机 元数据：仅业务表 + Machine，不建 Cluster / Entry。"""

import logging

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import machine
from backend.db_meta.enums import MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Machine
from backend.exec_host.models import ExecHost, ExecHostStatus

logger = logging.getLogger("root")

_ACTIVE_STATUSES = (
    ExecHostStatus.DEPLOYING.value,
    ExecHostStatus.RUNNING.value,
    ExecHostStatus.DESTROYING.value,
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
) -> ExecHost:
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    bk_cloud_id = request_validator.validated_integer(bk_cloud_id)
    name = (name or "").strip()
    ip = (ip or "").strip()
    if not name:
        raise DBMetaException(message=_("执行机名称为空"))
    if not ip:
        raise DBMetaException(message=_("执行机 IP 为空"))

    _assert_name_available(bk_biz_id=bk_biz_id, name=name)
    _assert_ip_available_for_exec_host(bk_cloud_id=bk_cloud_id, ip=ip)
    machine.get_or_create(
        bk_cloud_id=bk_cloud_id,
        machines=[
            {
                "ip": ip,
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": MachineType.EXEC_HOST.value,
            }
        ],
        creator=creator,
    )

    exec_host = ExecHost.objects.create(
        name=name,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        status=ExecHostStatus.RUNNING.value,
        ip=ip,
        deploy_path=deploy_path or "",
        version=version or "",
        db_type=db_type or "",
        purpose=purpose or "",
        tags=tags or {},
        creator=creator,
        updater=creator,
    )
    logger.info(_("ExecHost registered: name={} id={} ip={}").format(name, exec_host.id, ip))
    return exec_host


def _assert_name_available(bk_biz_id: int, name: str):
    exists = ExecHost.objects.filter(
        bk_biz_id=bk_biz_id,
        name=name,
        status__in=_ACTIVE_STATUSES,
    ).exists()
    if exists:
        raise DBMetaException(message=_("业务 {} 下执行机名称 {} 已存在或正在回收").format(bk_biz_id, name))


def _assert_ip_available_for_exec_host(bk_cloud_id: int, ip: str):
    existing = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if existing and existing.machine_type != MachineType.EXEC_HOST.value:
        raise DBMetaException(message=_("IP {} 已存在且机型为 {}，禁止注册为执行机").format(ip, existing.machine_type))
    active = ExecHost.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id, status__in=_ACTIVE_STATUSES).first()
    if active:
        raise DBMetaException(
            message=_("IP {} 已有活跃执行机(id={}, name={})，请改用执行机 ID 复用，禁止重复注册").format(ip, active.id, active.name)
        )
