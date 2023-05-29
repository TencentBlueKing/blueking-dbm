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

from backend.bk_web.models import AuditedModel


class TicketResultRelation(AuditedModel):
    """
    某些单据执行后需要关联到第三方系统才能获得直接结果
    task_id 为了兼容性设计为字符串类型, 这样方便兼容各个系统的 id 设计
    这里只提供对应关系, 通过 ticket_id 拿到 task_id 后具体该怎么用, 需要和设计人员沟通
    """

    ticket_id = models.BigIntegerField(default=0, help_text=_("单据id"))
    task_id = models.CharField(max_length=255, default="", help_text=_("第三方系统id"))
    ticket_type = models.CharField(max_length=255, default="")

    class Meta:
        indexes = [models.Index(fields=["task_id"]), models.Index(fields=["ticket_id"])]
