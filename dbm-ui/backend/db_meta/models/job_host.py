# -*- coding: utf-8 -*-
"""跨 DB 临时作业机元数据（无 Cluster / 域名）。"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class JobHostStatus(StrStructuredEnum):
    DEPLOYING = EnumField("deploying", _("deploying"))
    RUNNING = EnumField("running", _("running"))
    DESTROYING = EnumField("destroying", _("destroying"))
    DESTROYED = EnumField("destroyed", _("destroyed"))


class JobHost(AuditedModel):
    """临时作业机业务表：申请 → 跑 Job → 回收。"""

    name = models.CharField(_("名称"), max_length=LEN_NORMAL)
    bk_biz_id = models.IntegerField(_("业务ID"), default=0)
    bk_cloud_id = models.IntegerField(_("云区域ID"), default=0)
    status = models.CharField(
        _("状态"),
        max_length=LEN_SHORT,
        choices=JobHostStatus.get_choices(),
        default=JobHostStatus.DEPLOYING.value,
    )
    ip = models.CharField(_("IP"), max_length=LEN_NORMAL, default="")
    deploy_path = models.CharField(_("部署路径"), max_length=LEN_LONG, default="")
    version = models.CharField(_("版本"), max_length=LEN_NORMAL, default="")
    db_type = models.CharField(_("数据库类型"), max_length=LEN_NORMAL, default="")
    purpose = models.CharField(_("用途"), max_length=LEN_NORMAL, default="")
    tags = models.JSONField(_("标签"), default=dict)

    class Meta:
        verbose_name = verbose_name_plural = _("作业机表")
