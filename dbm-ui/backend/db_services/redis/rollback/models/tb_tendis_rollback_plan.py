from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel


class TbTendisRollbackPlan(AuditedModel):
    """The rollback plan approved at ticket submission; flow nodes read it by id."""

    id = models.BigAutoField(primary_key=True)
    bk_biz_id = models.BigIntegerField(verbose_name=_("业务id"))
    cluster_id = models.BigIntegerField(verbose_name=_("集群id"))
    plan = models.JSONField(default=dict, verbose_name=_("回档计划"))

    class Meta:
        db_table = "tb_tendis_rollback_plan"
        verbose_name = "Tendis rollback plan"
