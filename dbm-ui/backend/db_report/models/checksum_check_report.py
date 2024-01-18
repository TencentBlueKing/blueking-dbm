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
import django.db.models.deletion
from django.db import models
from django.utils.translation import ugettext as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.db_report.report_basemodel import BaseReportABS


class ChecksumCheckReport(BaseReportABS):
    cluster = models.CharField(max_length=255, default="", verbose_name=_("集群名称"))
    cluster_type = models.CharField(
        max_length=64, choices=ClusterType.get_choices(), default="", verbose_name=_("集群类型")
    )
    fail_slaves = models.IntegerField(default=0, verbose_name=_("失败的slave实例数量"))


class ChecksumInstance(AuditedModel):
    ip = models.CharField(max_length=64, verbose_name=_("slave部署机器ip"))
    port = models.CharField(max_length=64, verbose_name=_("slave部署机器port"))
    master_ip = models.CharField(max_length=64, verbose_name=_("master部署机器ip"))
    master_port = models.CharField(max_length=64, verbose_name=_("master部署机器port"))
    details = models.JSONField(default=dict, verbose_name=_("不一致库表详情"))
    report = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ChecksumCheckReport")
