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
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_MIDDLE
from backend.bk_web.models import AuditedModel
from backend.ticket.models import Flow, Ticket


class DirtyMachine(AuditedModel):
    """
    污点机器记录：从资源池申请成功后，但是部署失败未处理的机器记录
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("业务ID"))
    bk_host_id = models.PositiveBigIntegerField(primary_key=True, default=0, help_text=_("主机ID"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("主机云区域"))
    ip = models.CharField(max_length=LEN_MIDDLE, help_text=_("主机IP"))
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, help_text=_("关联任务"))
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, help_text=_("关联单据"))
