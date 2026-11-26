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

import json
import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from django_celery_beat.schedulers import ModelEntry

from backend.bk_web import constants
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.constants import FailoverDrillVersion, PeriodicTaskType
from backend.db_report.report_basemodel import BaseReportABS

logger = logging.getLogger("root")


class PeriodicTaskManager(models.Manager):
    pass


class DBPeriodicTask(AuditedModel):
    name = models.CharField(_("周期任务名称"), max_length=constants.LEN_LONG, unique=True)
    task = models.ForeignKey(PeriodicTask, verbose_name=_("celery 周期任务实例"), on_delete=models.CASCADE)
    task_type = models.CharField(_("任务类型"), choices=PeriodicTaskType.get_choices(), max_length=constants.LEN_SHORT)
    is_frozen = models.BooleanField(_("是否冻结"), help_text=_("人工冻结此任务，将不受更新影响"), default=False)

    objects = PeriodicTaskManager()

    class Meta:
        verbose_name_plural = verbose_name = _("周期任务(PeriodicTask)")
        ordering = ["-id"]

    def __str__(self):
        return self.name

    @classmethod
    @transaction.atomic
    def delete_legacy_periodic_task(cls, tasks, task_type):
        # 本地周期任务，且不再注册，说明是历史废弃任务，需删除
        legacy_tasks = DBPeriodicTask.objects.filter(task_type=task_type).exclude(name__in=tasks)
        celery_task_ids = legacy_tasks.values_list("task_id", flat=True)
        PeriodicTask.objects.filter(id__in=celery_task_ids).delete()
        legacy_tasks.delete()

    @classmethod
    def create_or_update_periodic_task(cls, name, task, run_every, task_type, args=None, kwargs=None):
        """
        创建/更新任务
        """

        # 转换执行周期
        model_schedule, model_field = ModelEntry.to_model_schedule(run_every)
        # 转换执行参数
        _args = json.dumps(args or [])
        _kwargs = json.dumps(kwargs or {})

        try:
            db_task = DBPeriodicTask.objects.get(name=name)
        except DBPeriodicTask.DoesNotExist:
            # 新建周期任务
            celery_task = PeriodicTask.objects.create(
                name=name, task=task, args=_args, kwargs=_kwargs, **{model_field: model_schedule}
            )
            db_task = DBPeriodicTask.objects.create(name=name, task=celery_task, task_type=task_type)
        else:
            # 未冻结的情况，需要更新执行周期和执行参数
            if not db_task.is_frozen:
                celery_task = db_task.task
                setattr(celery_task, model_field, model_schedule)
                celery_task.args = _args
                celery_task.kwargs = _kwargs
                celery_task.save(update_fields=[model_field, "args", "kwargs"])

        return db_task


class DispatchQueueSettings(AuditedModel):
    """Persisted settings for one Redis dispatch queue namespace."""

    namespace = models.CharField(_("队列命名空间"), max_length=128, unique=True)
    config = models.JSONField(_("配置覆盖项"), default=dict, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("Dispatch队列设置")
        ordering = ["namespace"]

    def __str__(self):
        return self.namespace

    def clean(self):
        super().clean()
        from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
        from backend.db_periodic_task.dispatch.queue import DispatchQueue
        from backend.db_periodic_task.dispatch.routing import validate_namespace

        validate_namespace(self.namespace)
        queue_cls = DispatchQueue.queue_for_namespace(self.namespace)
        config_cls = queue_cls.config_cls if queue_cls else DispatchQueueConfig
        config_cls.validate_raw(self.config)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Invalidate after commit so concurrent loaders cannot refill the cache
        # from the pre-commit DB snapshot (e.g. Admin save + watch_queue).
        namespace = self.namespace
        transaction.on_commit(lambda: _invalidate_queue_config(namespace))

    def delete(self, *args, **kwargs):
        namespace = self.namespace
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: _invalidate_queue_config(namespace))
        return result


class DispatchTaskSettings(AuditedModel):
    """Persisted settings for one registered dispatch task."""

    queue = models.ForeignKey(
        DispatchQueueSettings,
        verbose_name=_("队列设置"),
        related_name="task_settings",
        on_delete=models.PROTECT,
    )
    task_key = models.CharField(_("任务唯一标识"), max_length=255, unique=True)
    config = models.JSONField(_("配置覆盖项"), default=dict, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("Dispatch任务设置")
        ordering = ["queue__namespace", "task_key"]
        indexes = [models.Index(fields=["queue", "task_key"], name="idx_dispatch_queue_task")]

    def __str__(self):
        return self.task_key

    def clean(self):
        super().clean()
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

        task_cls = DISPATCH_REGISTRY.get(self.task_key)
        if task_cls:
            if self.queue_id and self.queue.namespace != task_cls.namespace:
                raise ValidationError({"queue": f"task {self.task_key} belongs to namespace {task_cls.namespace}"})
            task_cls.config_cls.validate_raw(self.config)
        elif not isinstance(self.config, dict):
            raise ValidationError({"config": "must be a JSON object"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        task_key = self.task_key
        transaction.on_commit(lambda: _invalidate_task_config(task_key))

    def delete(self, *args, **kwargs):
        task_key = self.task_key
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: _invalidate_task_config(task_key))
        return result


class DispatchQueueRoute(AuditedModel):
    """Which Redis instance owns one dispatch namespace's keys.

    The route map must survive a Redis flush (unlike ``dispatch:registered``),
    so it lives in MySQL. It must NOT be folded into
    ``DispatchQueueSettings.config``: ``DispatchQueueConfig.save_to_db()``
    rewrites the whole config row and would silently reset ``redis_alias``.

    Editing either field through the admin is disabled on purpose —
    ``remap_namespace()`` is the only sanctioned mutation path because moving a
    live namespace also requires pausing, sweeping the old shard, and waiting
    out the route caches.
    """

    namespace = models.CharField(_("队列命名空间"), max_length=128, unique=True)
    redis_alias = models.CharField(_("Redis 实例别名"), max_length=64)

    class Meta:
        verbose_name = verbose_name_plural = _("Dispatch队列路由")
        ordering = ["namespace"]

    def __str__(self):
        return f"{self.namespace} -> {self.redis_alias}"

    def clean(self):
        super().clean()
        from django.conf import settings

        from backend.db_periodic_task.dispatch.routing import validate_namespace

        validate_namespace(self.namespace)
        aliases = getattr(settings, "DISPATCH_REDIS_ALIASES", None) or []
        if not aliases:
            raise ValidationError({"redis_alias": "no dispatch Redis aliases configured"})
        if self.redis_alias not in aliases:
            raise ValidationError(
                {"redis_alias": f"must be one of the configured dispatch aliases: {', '.join(aliases)}"}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        namespace = self.namespace
        transaction.on_commit(lambda: _invalidate_dispatch_route(namespace))

    def delete(self, *args, **kwargs):
        namespace = self.namespace
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: _invalidate_dispatch_route(namespace))
        return result


def _invalidate_queue_config(namespace: str) -> None:
    from backend.db_periodic_task.dispatch.config_cache import DispatchSettingsCache

    DispatchSettingsCache.invalidate_queue(namespace)


def _invalidate_task_config(task_key: str) -> None:
    from backend.db_periodic_task.dispatch.config_cache import DispatchSettingsCache

    DispatchSettingsCache.invalidate_task(task_key)


def _invalidate_dispatch_route(namespace: str) -> None:
    from backend.db_periodic_task.dispatch.routing import invalidate_route

    invalidate_route(namespace)


class TaskStatus:
    # 已生成任务
    GENERATED = "generated"
    # 已申请资源
    RESOURCE_APPLIED = "resource_applied"
    # 资源不足
    RESOURCE_INSUFFICIENT = "resource_insufficient"
    # 资源申请失败
    RESOURCE_APPLIED_FAILED = "resource_applied_failed"
    # 提交任务成功
    COMMIT_SUCCESS = "commit_success"
    # 提交任务失败
    COMMIT_FAILED = "commit_failed"
    # 部署mysql成功
    DEPLOY_SUCCESS = "deploy_success"
    # 演练恢复成功
    RECOVER_SUCCESS = "recover_success"
    # 演练恢复失败
    RECOVER_FAILED = "recover_failed"
    # binlog 查询或下载失败
    BINLOG_PREPARE_FAILED = "binlog_prepare_failed"
    # binlog apply 失败
    BINLOG_APPLY_FAILED = "binlog_apply_failed"
    # 资源归还成功
    RESOURCE_RETURN_SUCCESS = "resource_return_success"

    @classmethod
    def exercise_failed_statuses(cls):
        return [cls.RECOVER_FAILED, cls.BINLOG_PREPARE_FAILED, cls.BINLOG_APPLY_FAILED]


class TaskPhase:
    # 初始化
    DONE = "done"
    # 执行中
    RUNNING = "running"


class MySQLBackupRecoverTask(BaseReportABS):
    """
    MySQL备份定期回档演练
    """

    bk_biz_id = models.IntegerField(_("演练业务ID"), default=0)
    cluster_id = models.IntegerField(_("备份来源集群ID"), default=0)
    cluster_domain = models.CharField(_("备份来源域名"), max_length=constants.LEN_LONG, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    charset = models.CharField(_("字符集"), max_length=constants.LEN_SHORT, default="")
    mysql_version = models.CharField(_("MySQL版本"), max_length=constants.LEN_SHORT, default="")
    sql_mode = models.CharField(_("SQL模式"), max_length=constants.LEN_LONG, default="")
    backup_id = models.CharField(_("备份ID"), max_length=constants.LEN_LONG, default="")
    backup_begin_time = models.DateTimeField(_("备份开始时间"), default=None)
    backup_end_time = models.DateTimeField(_("备份结束时间"), default=None)
    backup_total_size = models.IntegerField(_("备份总大小G"), default=0)
    backup_host = models.CharField(_("备份主机"), max_length=constants.LEN_LONG, default="")
    backup_host_role = models.CharField(_("备份主机角色"), max_length=constants.LEN_SHORT, default="")
    backup_type = models.CharField(_("备份类型"), max_length=constants.LEN_SHORT, default="")
    backup_tool = models.CharField(_("备份工具"), max_length=constants.LEN_SHORT, default="")
    time_zone = models.CharField(_("时区"), max_length=constants.LEN_SHORT, default="")
    exercise_host_ip = models.CharField(
        _("演练机器IP"), max_length=constants.LEN_NORMAL, default="", help_text=_("用于演练的机器IP地址")
    )
    exercise_host_spec = models.JSONField(
        _("演练主机规格快照"), default=dict, blank=True, null=True, help_text=_("演练主机申请时的硬件规格快照")
    )
    backup_download_start_time = models.DateTimeField(
        _("下载全备开始时间"), null=True, blank=True, default=None, help_text=_("下载全备文件开始时间")
    )
    backup_download_duration = models.IntegerField(
        _("下载全备耗时(秒)"), null=True, blank=True, default=None, help_text=_("下载全备文件耗时，单位秒")
    )
    exercise_timing_nodes = models.JSONField(
        _("演练计时步骤"),
        default=dict,
        blank=True,
        help_text=_("全备下载、恢复数据步骤编号"),
    )
    # 关联单据id
    recover_start_time = models.DateTimeField(_("备份恢复开始时间"), default=timezone.now)
    recover_end_time = models.DateTimeField(_("备份恢复结束时间"), default=timezone.now)
    recover_duration = models.IntegerField(
        _("纯备份恢复耗时(秒)"),
        null=True,
        blank=True,
        default=None,
        help_text=_("纯备份恢复数据阶段耗时，不含下载与binlog前滚，单位秒"),
    )
    task_id = models.CharField(_("关联的任务ID"), max_length=constants.LEN_LONG, default="")
    task_status = models.CharField(_("任务状态"), max_length=constants.LEN_SHORT, default="")
    task_info = models.TextField(_("任务信息"), default="")
    # 定义任务的运行阶段
    phase = models.CharField(_("阶段"), max_length=constants.LEN_SHORT, default="")

    HOST_SPEC_SNAPSHOT_FIELDS = (
        "ip",
        "bk_host_id",
        "bk_cloud_id",
        "device_class",
        "svr_type_name",
        "cpu_num",
        "dram_cap",
        "total_storage_cap",
        "total_data_storage_cap",
        "storage_device",
        "os_type",
        "os_name",
        "city",
        "sub_zone",
        "idc_name",
        "rack_id",
    )

    class Meta:
        indexes = [
            models.Index(fields=["bk_biz_id", "task_status"], name="idx_biz_task_status"),
            models.Index(fields=["cluster_id", "task_status"], name="idx_cluster_task_status"),
            models.Index(fields=["backup_id", "task_status"], name="idx_backup_task_status"),
        ]

    @classmethod
    def build_host_spec_snapshot(cls, mch_info) -> dict:
        """从资源池主机信息中抽取演练主机硬件规格快照。"""
        if not isinstance(mch_info, dict):
            return {}
        snapshot = {}
        for field in cls.HOST_SPEC_SNAPSHOT_FIELDS:
            if field not in mch_info:
                continue
            val = mch_info.get(field)
            if val is None or val == "":
                continue
            if field == "storage_device" and isinstance(val, str):
                try:
                    val = json.loads(val)
                except (ValueError, TypeError):
                    pass
            snapshot[field] = val
        return snapshot

    @classmethod
    def get_all_practiced_biz_ids(cls):
        """
        获取已经回档过的所有业务ID
        """
        try:
            return list(
                MySQLBackupRecoverTask.objects.filter(
                    task_status__in=[TaskStatus.RECOVER_SUCCESS, TaskStatus.RESOURCE_RETURN_SUCCESS]
                )
                .values_list("bk_biz_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取已回档业务ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_all_practiced_cluster_ids(cls):
        """
        获取已经成功回档过的所有集群ID
        """
        try:
            return list(
                MySQLBackupRecoverTask.objects.filter(
                    task_status__in=[TaskStatus.RECOVER_SUCCESS, TaskStatus.RESOURCE_RETURN_SUCCESS]
                )
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取已回档集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_today_task_cluster_ids(cls):
        """
        获取项目时区自然日内已创建演练任务的集群 ID。

        当天任意状态的任务都占用该集群的当日名额。窗口是本地 00:00 到次日 00:00。
        """
        now_local = timezone.localtime()
        day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        return list(
            cls.objects.filter(create_at__gte=day_start, create_at__lt=day_end)
            .values_list("cluster_id", flat=True)
            .distinct()
        )

    @classmethod
    def get_running_task_cluster_ids(cls):
        """
        获取正在执行中的任务集群ID列表，避免并发执行
        """
        try:
            # 过滤正在执行中的任务
            return list(
                MySQLBackupRecoverTask.objects.filter(phase=TaskPhase.RUNNING)
                .exclude(task_status__in=[TaskStatus.RESOURCE_INSUFFICIENT, TaskStatus.RESOURCE_APPLIED_FAILED])
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取正在执行任务集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_recent_24h_exercise_cluster_type_stats(cls):
        """
        获取最近24小时内演练的集群类型统计

        Returns:
            dict: {
                'tendbcluster_count': int,  # TenDBCluster演练次数
                'tendbha_count': int,       # TenDBHA演练次数
                'total_count': int          # 总演练次数
            }
        """
        recent_time = timezone.now() - timedelta(hours=24)
        recent_tasks = MySQLBackupRecoverTask.objects.filter(
            create_at__gte=recent_time,
        ).values_list("cluster_type", flat=True)

        tendbcluster_count = sum(1 for ct in recent_tasks if ct == "tendbcluster")
        tendbha_count = sum(1 for ct in recent_tasks if ct == "tendbha")

        return {
            "tendbcluster_count": tendbcluster_count,
            "tendbha_count": tendbha_count,
            "total_count": tendbcluster_count + tendbha_count,
        }

    @classmethod
    def get_recent_2days_failed_cluster_ids(cls):
        """
        获取最近2天内失败的演练集群ID列表
        失败指的是task_status为RECOVER_FAILED、BINLOG_PREPARE_FAILED或BINLOG_APPLY_FAILED状态的任务
        """
        try:
            recent_time = timezone.now() - timedelta(days=2)
            return list(
                MySQLBackupRecoverTask.objects.filter(
                    create_at__gte=recent_time, task_status__in=TaskStatus.exercise_failed_statuses()
                )
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取最近2天失败演练集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []


class FailoverDrillConfig(AuditedModel):
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务的 cmdb id"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 id"))
    db_module_id = models.IntegerField(default=0, help_text=_("db模块 id"))
    labels = models.JSONField(help_text=_("资源标签"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    city_map = models.JSONField(help_text=_("城市缩写映射表"), default=dict)
    switch_flag = models.BooleanField(help_text=_("是否启用任务"), default=False)
    max_retry = models.IntegerField(default=6, help_text=_("最大重试次数"))
    interval = models.IntegerField(default=10, help_text=_("重试间隔 分钟"))
    version = models.CharField(
        max_length=16,
        choices=FailoverDrillVersion.get_choices(),
        default=FailoverDrillVersion.V1.value,
        help_text=_("DBHA版本"),
    )
    cluster_domain = models.CharField(max_length=255, default="", blank=True, help_text=_("演练集群域名"))


class MysqlFailoverDrillV1Config(AuditedModel):
    """一座城市、一种集群类型、一个 DBHA 版本一行。旧 FailoverDrillConfig 继续给原定时任务用。"""

    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    city = models.CharField(max_length=128, default="", help_text=_("逻辑城市名"))
    city_abbr = models.CharField(max_length=64, default="", blank=True, help_text=_("城市缩写，用于演练域名"))
    version = models.CharField(
        max_length=16,
        choices=((FailoverDrillVersion.V1.value, _("DBHA v1")), (FailoverDrillVersion.V2.value, _("DBHA v2"))),
        default=FailoverDrillVersion.V1.value,
        help_text=_("DBHA 版本。同一城市可以各有一行 v1 和 v2"),
    )
    enabled = models.BooleanField(default=False, help_text=_("是否演练这座城市的这个版本"))
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务的 cmdb id"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 id"))
    db_module_id = models.IntegerField(default=0, help_text=_("db模块 id"))
    labels = models.JSONField(default=list, help_text=_("资源申请和退回时使用的标签"))
    db_version = models.CharField(max_length=64, default="MySQL-5.7", help_text=_("演练集群版本"))
    spider_version = models.CharField(
        max_length=64,
        default="Spider-3",
        help_text=_("TenDBCluster 演练使用的 Spider 版本"),
    )
    charset = models.CharField(max_length=32, default="utf8mb4", help_text=_("演练集群字符集"))
    disaster_tolerance_level = models.CharField(max_length=64, default="CROS_SUBZONE", help_text=_("容灾要求，传给上架元数据"))
    start_mysql_port = models.IntegerField(default=20000, help_text=_("MySQL 起始端口"))
    start_proxy_port = models.IntegerField(default=10000, help_text=_("Proxy 起始端口"))
    remark = models.CharField(max_length=255, default="", blank=True, help_text=_("备注"))

    class Meta:
        verbose_name = verbose_name_plural = _("MySQL容灾演练v1独立配置")
        unique_together = (("cluster_type", "city", "version"),)

    @staticmethod
    def select_enabled(configs):
        """按传入顺序保留已启用、城市名非空的配置。"""
        chosen = []
        for conf in configs:
            if conf.enabled and (conf.city or "").strip():
                chosen.append(conf)
        return chosen


class MysqlFailoverDrillV1Run(AuditedModel):
    """一座城市一次独立演练的结果。阶段流水在 MysqlFailoverDrillV1Stage。"""

    root_id = models.CharField(max_length=64, default="", db_index=True, help_text=_("Bamboo 根流程"))
    main_task_id = models.CharField(max_length=64, unique=True, help_text=_("这座城市的演练号"))
    bk_biz_id = models.IntegerField(default=0)
    bk_cloud_id = models.IntegerField(default=0)
    city = models.CharField(max_length=128, default="")
    cluster_type = models.CharField(max_length=64, default="")
    version = models.CharField(
        max_length=16,
        default=FailoverDrillVersion.V1.value,
        db_index=True,
        help_text=_("这次演练的 DBHA 版本，用来区分 v1 和 v2 的结果"),
    )
    master_domain = models.CharField(max_length=255, default="")
    slave_domain = models.CharField(max_length=255, default="")
    labels = models.JSONField(default=list)
    hosts = models.JSONField(default=list)
    phase = models.CharField(max_length=32, default="resource_apply", help_text=_("当前阶段"))
    flow_result = models.CharField(max_length=32, default="running", help_text=_("流程结果"))
    dbha_result = models.CharField(
        max_length=32,
        default="unknown",
        help_text=_("DBHA 切换汇总。各实例类型都切换成功才是 switched，分类型结果在 MysqlFailoverDrillV1Dbha"),
    )
    resource_returned = models.BooleanField(default=False)
    labels_applied = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(default="", blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("MySQL容灾演练v1结果")


class MysqlFailoverDrillV1Stage(models.Model):
    """演练过程流水。同一节点从开始到结束各记一行。"""

    run = models.ForeignKey(MysqlFailoverDrillV1Run, on_delete=models.CASCADE, related_name="stages")
    stage = models.CharField(max_length=255, help_text=_("阶段或节点名"))
    target = models.CharField(max_length=255, default="", blank=True)
    status = models.CharField(max_length=32)
    node_id = models.CharField(max_length=64, default="", blank=True)
    phase = models.CharField(max_length=32, default="")
    error_message = models.TextField(default="", blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("MySQL容灾演练v1过程")
        indexes = [
            models.Index(fields=["run", "status"], name="drill_v1_stage_run_status"),
            models.Index(fields=["node_id"], name="drill_v1_stage_node_id"),
        ]


class MysqlFailoverDrillV1Dbha(models.Model):
    """一次演练里一个实例类型的 DBHA 切换结果。TenDBCluster 是 remote、spider，TenDBHA 是 backend、proxy。"""

    run = models.ForeignKey(MysqlFailoverDrillV1Run, on_delete=models.CASCADE, related_name="dbha_rows")
    version = models.CharField(
        max_length=16,
        default=FailoverDrillVersion.V1.value,
        help_text=_("这次触发用的 DBHA 版本，v1 或 v2"),
    )
    instance_type = models.CharField(max_length=64, help_text=_("实例类型"))
    ip = models.CharField(max_length=64, default="", blank=True, help_text=_("这次触发的 IP"))
    dbha_result = models.CharField(
        max_length=32,
        default="unknown",
        help_text=_("switched、timeout、query_error、unknown"),
    )
    dbha_status = models.CharField(max_length=64, default="", blank=True, help_text=_("HADB 返回的切换状态"))
    error_message = models.TextField(default="", blank=True)
    switch_start_time = models.DateTimeField(null=True, blank=True)
    switch_finished_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("MySQL容灾演练v1切换结果")
        constraints = [
            models.UniqueConstraint(fields=["run", "instance_type"], name="drill_v1_dbha_run_type"),
        ]
        indexes = [
            models.Index(fields=["version", "instance_type", "dbha_result"], name="drill_v1_dbha_ver_type"),
        ]


class ExerciseIgnoreType:
    """演练忽略类型枚举"""

    BIZ = "biz"  # 业务级别忽略
    CLUSTER = "cluster"  # 集群级别忽略

    @classmethod
    def get_choices(cls):
        return (
            (cls.BIZ, _("业务")),
            (cls.CLUSTER, _("集群")),
        )


class ExerciseIgnoreConfig(AuditedModel):
    """
    演练忽略配置表
    用于配置忽略哪些业务或集群的演练
    """

    ignore_type = models.CharField(
        _("忽略类型"),
        max_length=constants.LEN_SHORT,
        choices=ExerciseIgnoreType.get_choices(),
        help_text=_("忽略类型：biz-业务级别，cluster-集群级别"),
    )
    target_id = models.IntegerField(
        _("目标ID"), help_text=_("当ignore_type为biz时，存储bk_biz_id；当ignore_type为cluster时，存储cluster_id")
    )
    target_name = models.CharField(_("目标名称"), max_length=constants.LEN_LONG, default="", help_text=_("业务名称或集群域名，用于展示"))
    reason = models.TextField(_("忽略原因"), default="", help_text=_("说明为什么要忽略此业务或集群的演练"))
    is_active = models.BooleanField(_("是否生效"), default=True, help_text=_("是否启用此忽略配置"))
    expire_time = models.DateTimeField(_("过期时间"), null=True, blank=True, help_text=_("忽略配置的过期时间，为空表示永久生效"))

    class Meta:
        verbose_name_plural = verbose_name = _("演练忽略配置")
        ordering = ["-id"]
        unique_together = [["ignore_type", "target_id"]]  # 同一类型的同一目标只能有一条配置

    def __str__(self):
        return f"{self.get_ignore_type_display()}-{self.target_name}({self.target_id})"

    @classmethod
    def is_biz_ignored(cls, bk_biz_id):
        """
        检查指定业务是否被忽略

        Args:
            bk_biz_id (int): 业务ID

        Returns:
            bool: True表示被忽略，False表示不忽略
        """
        now = timezone.now()
        return (
            cls.objects.filter(ignore_type=ExerciseIgnoreType.BIZ, target_id=bk_biz_id, is_active=True)
            .filter(models.Q(expire_time__isnull=True) | models.Q(expire_time__gt=now))
            .exists()
        )

    @classmethod
    def is_cluster_ignored(cls, cluster_id):
        """
        检查指定集群是否被忽略

        Args:
            cluster_id (int): 集群ID

        Returns:
            bool: True表示被忽略，False表示不忽略
        """
        now = timezone.now()
        return (
            cls.objects.filter(ignore_type=ExerciseIgnoreType.CLUSTER, target_id=cluster_id, is_active=True)
            .filter(models.Q(expire_time__isnull=True) | models.Q(expire_time__gt=now))
            .exists()
        )

    @classmethod
    def get_ignored_biz_ids(cls):
        """
        获取所有被忽略的业务ID列表

        Returns:
            list: 被忽略的业务ID列表
        """
        try:
            now = timezone.now()
            return list(
                cls.objects.filter(ignore_type=ExerciseIgnoreType.BIZ, is_active=True)
                .filter(models.Q(expire_time__isnull=True) | models.Q(expire_time__gt=now))
                .values_list("target_id", flat=True)
            )
        except Exception as e:
            logger.warning(gettext("获取被忽略业务ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_ignored_cluster_ids(cls):
        """
        获取所有被忽略的集群ID列表

        Returns:
            list: 被忽略的集群ID列表
        """
        try:
            now = timezone.now()
            return list(
                cls.objects.filter(ignore_type=ExerciseIgnoreType.CLUSTER, is_active=True)
                .filter(models.Q(expire_time__isnull=True) | models.Q(expire_time__gt=now))
                .values_list("target_id", flat=True)
            )
        except Exception as e:
            logger.warning(gettext("获取被忽略集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    def save(self, *args, **kwargs):
        """
        重写save方法，确保同一类型的同一目标只能有一条生效配置
        """
        if self.is_active:
            # 如果当前配置要设为生效，则将同类型同目标的其他配置设为不生效
            ExerciseIgnoreConfig.objects.filter(
                ignore_type=self.ignore_type, target_id=self.target_id, is_active=True
            ).exclude(id=self.id).update(is_active=False)

        super().save(*args, **kwargs)
