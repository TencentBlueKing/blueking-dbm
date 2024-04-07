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
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.report_basemodel import BaseReportABS


class MetaCheckReport(BaseReportABS):
    ip = models.GenericIPAddressField(default="")
    port = models.PositiveIntegerField(default=0)
    cluster = models.CharField(max_length=255, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
    subtype = models.CharField(
        max_length=64, choices=MetaCheckSubType.get_choices(), default="", help_text=_("元数据检查子项")
    )
