from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType, MigrateStatus


class TbTendisSlotsMigrateRecord(AuditedModel):
    id = models.BigAutoField(primary_key=True)
    related_slots_migrate_bill_id = models.BigIntegerField(verbose_name=_("单据号，关联单据"))
    bk_biz_id = models.BigIntegerField(verbose_name=_("业务id"))
    app = models.CharField(max_length=64, default="", verbose_name=_("业务名"))
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域id"))

    cluster_type = models.CharField(
        max_length=64, default="", choices=ClusterType.get_choices(), verbose_name=_("集群类型")
    )
    cluster_id = models.BigIntegerField(verbose_name=_("集群id，cluster.id"))
    cluster_name = models.CharField(max_length=128, default="", verbose_name=_("集群名"))

    # 扩缩容
    old_instance_pair = models.JSONField(default=dict, verbose_name=_("扩缩容前实例主从对"))
    new_instance_pair = models.JSONField(default=dict, verbose_name=_("扩缩容后实例主从对"))
    # 记录扩容新增的实例
    add_new_master_slave_pair = models.JSONField(default=dict, verbose_name=_("扩容新增实例主从对"))
    # 记录缩容下架的实例
    shutdown_master_slave_pair = models.JSONField(default=dict, verbose_name=_("缩容下架实例主从对"))
    current_group_num = models.IntegerField(null=True, verbose_name=_("扩缩容前的主机数量"))
    target_group_num = models.IntegerField(null=True, verbose_name=_("扩缩容后的主机数量"))
    # 扩容时的新增主机信息
    new_ip_group = models.JSONField(default=dict, verbose_name=_("扩容时新增的主从主机"))

    # 迁移特定slots，解决热点key问题和数据均衡
    migrate_specified_slot = models.JSONField(default=dict, verbose_name=_("特定slots迁移信息"))

    # 任务执行状态,0:未开始 1:执行中 2:完成 -1:发生错误
    status = models.IntegerField(
        choices=MigrateStatus.get_choices(),
        default=MigrateStatus.NOT_STARTED,
        verbose_name=_("状态"),
    )
    specification = models.JSONField(default=dict, verbose_name=_("规格需求"))

    class Meta:
        db_table = "tb_tendis_slots_migrate_record"
        verbose_name = "Tendisplus slots migrate  record"

        indexes = [
            models.Index(fields=["update_at"], name="idx_update_at_slots"),
            models.Index(fields=["cluster_name"], name="idx_cluster_name_slots"),
        ]
