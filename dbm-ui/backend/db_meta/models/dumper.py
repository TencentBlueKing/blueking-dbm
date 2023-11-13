"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums.dumper import DumperReceiverType

logger = logging.getLogger("root")


class DumperSubscribeConfig(AuditedModel):
    """dumper的数据订阅配置表"""

    bk_biz_id = models.IntegerField(help_text=_("关联的业务id，对应cmdb"))
    name = models.CharField(max_length=128, help_text=_("订阅配置名"))
    receiver_type = models.CharField(max_length=32, choices=DumperReceiverType.get_choices(), help_text=_("数据接收端类型"))
    receiver = models.CharField(max_length=255, help_text=_("接收端域名(IP)"))
    subscribe = models.JSONField(help_text=_("订阅库表信息 eg: [{'db_name': 'xx', 'table_names': [....]}, ...]"))

    class Meta:
        verbose_name = _("dumper数据订阅配置")
        verbose_name_plural = _("dumper数据订阅配置")

        unique_together = (("bk_biz_id", "name"),)

    def get_subscribe_info(self):
        subscribe_info = []
        for info in self.subscribe:
            subscribe_info.extend([f"{info['db_name']}.{table_name}" for table_name in info["table_names"]])
        return subscribe_info
