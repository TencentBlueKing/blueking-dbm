"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_report.enums import ReportStateType
from backend.db_report.report_basemodel import BaseReportABS


class BaseSqlserverReportABS(BaseReportABS):
    cluster = models.CharField(max_length=255, default="", verbose_name=_("集群名称"))
    cluster_type = models.CharField(
        max_length=64, choices=ClusterType.get_choices(), default="", verbose_name=_("集群类型")
    )
    instance_host = models.CharField(max_length=255, default="", verbose_name=_("实例IP"))
    instance_port = models.IntegerField(default=48322, verbose_name=_("实例端口"))

    class Meta:
        abstract = True

    def calc_failed_days(self):
        """
        计算记录持续出现异常的天数
        计算逻辑：找出上一次（默认前一天），是否出现异常记录，如果有则，累计failed_days计时器，反正，failed_days 重置为1
        """
        current_date = self.create_at.date()
        yesterday_date = current_date - timezone.timedelta(days=1)
        start_of_day = timezone.make_aware(timezone.datetime.combine(yesterday_date, timezone.datetime.min.time()))
        end_of_day = timezone.make_aware(timezone.datetime.combine(yesterday_date, timezone.datetime.max.time()))

        records = self.__class__.objects.filter(
            create_at__gte=start_of_day,
            create_at__lte=end_of_day,
            cluster=self.cluster,
            instance_host=self.instance_host,
            instance_port=self.instance_port,
            state__in=[ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value],
        ).order_by("-create_at")
        # 理论一个检查项，一个集群只会产生一条记录，如果当天集群产生多条异常记录，则随机获取一条为准
        if not records:
            # 证明前一次没有产生异常记录, 重置failed_days为1
            self.failed_days = 1
            self.save()
            return

        self.failed_days = records[0].failed_days + 1
        self.save()
        return


class BaseBackupReportABS(BaseReportABS):
    """
    备份巡检的抽象基类
    """

    cluster = models.CharField(max_length=255, default="", verbose_name=_("集群名称"))
    cluster_type = models.CharField(
        max_length=64, choices=ClusterType.get_choices(), default="", verbose_name=_("集群类型")
    )

    class Meta:
        abstract = True

    def calc_failed_days(self):
        """
        计算记录持续出现异常的天数
        计算逻辑：找出上一次（默认前一天），是否出现异常记录，如果有则，累计failed_days计时器，反正，failed_days 重置为1
        """
        current_date = self.create_at.date()
        yesterday_date = current_date - timezone.timedelta(days=1)
        start_of_day = timezone.make_aware(timezone.datetime.combine(yesterday_date, timezone.datetime.min.time()))
        end_of_day = timezone.make_aware(timezone.datetime.combine(yesterday_date, timezone.datetime.max.time()))

        records = self.__class__.objects.filter(
            create_at__gte=start_of_day,
            create_at__lte=end_of_day,
            cluster=self.cluster,
            state__in=[ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value],
        )
        # 理论一个检查项，一个集群只会产生一条记录，如果当天集群产生多条异常记录，则随机获取一条为准
        if not records:
            # 证明前一次没有产生异常记录, 重置failed_days为1
            self.failed_days = 1
            self.save()
            return

        self.failed_days = records[0].failed_days + 1
        self.save()
        return


class SqlserverCheckAppSettingReport(BaseSqlserverReportABS):
    """
    检测实例的app_setting表信息是否正常
    """

    is_inconsistent = models.BooleanField(default=False, verbose_name=_("元信息是否不一致"))
    is_fix = models.BooleanField(default=False, verbose_name=_("元数据是否自动修复成功"))


class SqlserverCheckSysJobStatuReport(BaseSqlserverReportABS):
    """
    检测主从集群的系统作业的启动情况
    """

    is_job_disable = models.BooleanField(default=False, verbose_name=_("是否存在disable状态的系统job"))


class SqlserverCheckUserSyncReport(BaseSqlserverReportABS):
    """
    检测主从集群的账号同步状态
    """

    is_user_inconsistent = models.BooleanField(default=False, verbose_name=_("业务账号是否不一致"))


class SqlserverCheckJobSyncReport(BaseSqlserverReportABS):
    """
    检测主从集群的业务作业的JOB同步状态
    """

    is_job_inconsistent = models.BooleanField(default=False, verbose_name=_("业务Job数量是否不一致"))


class SqlserverCheckLinkServerReport(BaseSqlserverReportABS):
    """
    检测主从集群的linkserver配置的同步状态
    """

    is_link_server_inconsistent = models.BooleanField(default=False, verbose_name=_("业务LinkServer数量是否不一致"))


class SqlserverFullBackupInfoReport(BaseBackupReportABS):
    """
    全量备份文件巡检表
    """

    pass


class SqlserverLogBackupInfoReport(BaseBackupReportABS):
    """
    增量备份文件巡检表
    """

    pass
