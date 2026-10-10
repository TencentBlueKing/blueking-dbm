from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel


class TbTendisRollbackPlan(AuditedModel):
    """The rollback plan approved at ticket submission; flow nodes read it by id."""

    id = models.BigAutoField(primary_key=True)
    bk_biz_id = models.BigIntegerField(verbose_name=_("业务id"))
    cluster_id = models.BigIntegerField(verbose_name=_("集群id"), db_index=True)
    # Plans are saved while the ticket serializer validates, before the ticket exists.
    ticket_id = models.BigIntegerField(verbose_name=_("单据id"), null=True, blank=True, db_index=True)
    plan = models.JSONField(default=dict, verbose_name=_("回档计划"))

    class Meta:
        db_table = "tb_tendis_rollback_plan"
        verbose_name = "Tendis rollback plan"
