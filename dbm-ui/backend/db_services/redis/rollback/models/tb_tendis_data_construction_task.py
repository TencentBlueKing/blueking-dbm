from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel


class TbTendisRollbackTasks(AuditedModel):
    id = models.BigAutoField(primary_key=True)
    related_rollback_bill_id = models.BigIntegerField(verbose_name=_("单据号，关联单据"))
    bk_biz_id = models.BigIntegerField(verbose_name=_("业务id"))
    app = models.CharField(max_length=64, default="", verbose_name=_("业务名"))
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域id"))

    # 源集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    prod_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("构造源集群类型"))
    prod_cluster = models.CharField(max_length=128, default="", verbose_name=_("构造的源集群，线上环境cluster"))
    prod_instance_range = models.TextField(max_length=10000, verbose_name=_("源构造的实例范围"))

    # 目标集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    temp_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("临时集群类型"))
    temp_password = models.CharField(max_length=128, default="", verbose_name=_("临时集群proxy密码base64值"))
    temp_instance_range = models.TextField(max_length=10000, verbose_name=_("临时集群构造实例范围"))
    temp_cluster_proxy = models.CharField(max_length=100, verbose_name=_("构造产物访问入口ip:port"))

    prod_temp_instance_pairs = models.TextField(max_length=20000, default="", verbose_name=_("构造源实例和临时实例一一对应关系"))
    # 任务执行状态,0:未开始 1:执行中 2:完成 -1:发生错误
    status = models.IntegerField(default=0, verbose_name=_("任务状态"))
    # 构造记录是否已销毁,0:未销毁 1:已销毁
    is_destroyed = models.IntegerField(default=0, verbose_name=_("是否已销毁"))
    specification = models.CharField(max_length=100, verbose_name=_("规格需求"))
    host_count = models.IntegerField(verbose_name=_("构造的主机数量"))
    recovery_time_point = models.DateTimeField(verbose_name=_("构造到指定时间"))

    class Meta:
        db_table = "tb_tendis_rollback_tasks"
        verbose_name = "Tendis data construction task"

        indexes = [
            models.Index(fields=["update_at"], name="idx_update_at"),
            models.Index(fields=["prod_cluster"], name="idx_prod_cluster"),
        ]
