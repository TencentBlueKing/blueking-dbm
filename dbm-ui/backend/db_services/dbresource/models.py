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

from backend.bk_web.constants import LEN_NORMAL
from backend.ticket.constants import TICKET_FINISHED_STATUS_SET
from backend.ticket.models import Ticket


class ResourceReplenishRecord(models.Model):
    """资源补货记录"""

    creator = models.CharField(_("创建人"), max_length=LEN_NORMAL)
    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    details = models.JSONField(verbose_name=_("资源补给详情"))
    ticket_ids = models.JSONField(verbose_name=_("关联单据ID"))

    class Meta:
        verbose_name = _("资源补货记录")

    @classmethod
    def is_latest_running(cls):
        # 查询最近一条是否在运行
        record = cls.objects.last()
        ticket_status = list(Ticket.objects.filter(id__in=record.ticket_ids).values_list("status", flat=True))
        is_running = any(status not in TICKET_FINISHED_STATUS_SET for status in ticket_status)
        return record.id if is_running else None
