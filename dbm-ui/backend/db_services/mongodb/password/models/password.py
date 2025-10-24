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

logger = logging.getLogger("root")


class MongoDBPassword(models.Model):
    username = models.CharField(max_length=255, default="", help_text=_("用户名"))
    password = models.TextField(blank=True, help_text=_("密码"))
    component = models.CharField(max_length=255, default="", help_text=_("组件"))
    ip = models.CharField(max_length=255, default="", help_text=_("IP"))
    port = models.IntegerField(default=0, help_text=_("端口"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域ID"))

    class Meta:
        managed = False  # 不创建数据库表，仅用于 Admin 展示外部数据
        verbose_name = verbose_name_plural = _("MongoDB用户密码")

    def __str__(self):
        return self.username + " " + self.password + " " + self.component + " " + self.ip + " " + str(self.port)
