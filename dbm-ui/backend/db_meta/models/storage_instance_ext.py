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
from backend.db_meta.models import StorageInstance


class MySQLStorageInstanceExt(AuditedModel):
    """
    TenDBHA 和 TenDBCluster 多 slave 用
    一个 master 实例正常情况下, 有且只有一个 is_stand_by = True 的 slave 同步实例
    用于 dbha, 迁移等场景的备选目标
    master 默认为 True
    """

    instance = models.OneToOneField(StorageInstance, on_delete=models.PROTECT)
    is_stand_by = models.BooleanField(default=True, help_text=_("多 slave 的备选标志"))
