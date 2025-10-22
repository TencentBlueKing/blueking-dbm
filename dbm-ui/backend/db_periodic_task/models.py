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

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask
from django_celery_beat.schedulers import ModelEntry

from backend.bk_web import constants
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.constants import PeriodicTaskType
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
    # 资源归还成功
    RESOURCE_RETURN_SUCCESS = "resource_return_success"


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
    # 关联单据id
    recover_start_time = models.DateTimeField(_("备份恢复开始时间"), default=timezone.now)
    recover_end_time = models.DateTimeField(_("备份恢复结束时间"), default=timezone.now)
    task_id = models.CharField(_("关联的任务ID"), max_length=constants.LEN_LONG, default="")
    task_status = models.CharField(_("任务状态"), max_length=constants.LEN_SHORT, default="")
    task_info = models.TextField(_("任务信息"), default="")
    # 定义任务的运行阶段
    phase = models.CharField(_("阶段"), max_length=constants.LEN_SHORT, default="")
    status = models.BooleanField(default=False, help_text=_("巡检结果状态, 默认正常"))  # True = 正常, False = 异常

    class Meta:
        indexes = [
            models.Index(fields=["bk_biz_id", "task_status"], name="idx_biz_task_status"),
            models.Index(fields=["cluster_id", "task_status"], name="idx_cluster_task_status"),
            models.Index(fields=["backup_id", "task_status"], name="idx_backup_task_status"),
        ]

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
    def get_recent_24h_task_cluster_ids(cls):
        """
        获取最近24小时内发起任务集群ID列表
        """
        try:
            recent_time = timezone.now() - timedelta(hours=24)
            return list(
                MySQLBackupRecoverTask.objects.filter(
                    create_at__gte=recent_time,
                    # 排除所有状态的任务，不仅仅是创建时间
                )
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取最近24小时任务集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_running_task_cluster_ids(cls):
        """
        获取正在执行中的任务集群ID列表，避免并发执行
        """
        try:
            # 过滤正在执行中的任务
            return list(
                MySQLBackupRecoverTask.objects.filter(phase=TaskPhase.RUNNING)
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取正在执行任务集群ID列表时发生数据库连接错误: {}").format(str(e)))
            return []

    @classmethod
    def get_recent_2h_exercise_cluster_type_stats(cls):
        """
        获取最近2小时内演练的集群类型统计

        Returns:
            dict: {
                'tendbcluster_count': int,  # TenDBCluster演练次数
                'tendbha_count': int,       # TenDBHA演练次数
                'total_count': int          # 总演练次数
            }
        """
        recent_time = timezone.now() - timedelta(hours=2)
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
    def get_recent_3days_failed_cluster_ids(cls):
        """
        获取最近3天内失败的演练集群ID列表
        失败指的是task_status为RECOVER_FAILED状态的任务
        """
        try:
            recent_time = timezone.now() - timedelta(days=3)
            return list(
                MySQLBackupRecoverTask.objects.filter(
                    create_at__gte=recent_time, task_status=TaskStatus.RECOVER_FAILED
                )
                .values_list("cluster_id", flat=True)
                .distinct()
            )
        except Exception as e:
            logger.warning(gettext("获取最近3天失败演练集群ID列表时发生数据库连接错误: {}").format(str(e)))
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
