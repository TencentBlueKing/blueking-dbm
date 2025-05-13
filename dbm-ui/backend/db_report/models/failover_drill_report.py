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
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_report.report_basemodel import BaseReportABS
from backend.db_services.redis.autofix.enums import DBHASwitchResult


class FailoverDrillReport(BaseReportABS):
    main_task_id = models.CharField(max_length=64, help_text=_("主任务ID"), unique=True, default="")
    cluster_domain = models.CharField(max_length=255, help_text=_("集群域名"), default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices())
    city = models.CharField(max_length=128, help_text=_("城市"), default="")
    drill_info = models.TextField(default="", help_text=_("演练执行信息"))
    drill_start_time = models.DateTimeField(help_text=_("演练开始时间"), auto_now_add=True)
    drill_end_time = models.DateTimeField(help_text=_("演练结束始时间"), auto_now=True)
    task_info = models.TextField(help_text=_("演练任务执行信息"), default="")
    dhha_status = models.CharField(
        max_length=255, help_text=_("dbha切换状态"), choices=DBHASwitchResult.get_choices(), default=""
    )
    dbha_info = models.TextField(help_text=_("dbha切换信息"), default="")
