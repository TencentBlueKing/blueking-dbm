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

from backend.db_meta.models import StorageInstance
from django.utils.translation import gettext_lazy as _


class MongoDBStorageInstanceExt(models.Model):
    instance = models.OneToOneField(StorageInstance, on_delete=models.PROTECT)
    state = models.CharField(max_length=64, help_text=_("实例状态"), default=_("未检测"))
    state_code = models.IntegerField(help_text=_("实例状态码"), default=-1)
    priority = models.IntegerField(help_text=_("优先级"), default=-1)
    hidden = models.IntegerField(help_text=_("是否隐藏"), default=0)
    update_at = models.DateTimeField(
        help_text=_("最后更新时间"), default="0000-00-00 00:00:00", blank=True, null=True, db_index=True
    )
