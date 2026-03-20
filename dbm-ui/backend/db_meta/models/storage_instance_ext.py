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

from backend.db_meta.enums.instance_status import MongoDBStorageInstanceStatus
from backend.db_meta.models import StorageInstance

"""
    MongoDBStorageInstanceExt 表，用于存储 MongoDB 实例的扩展信息
    字段说明：
    instance: 关联 StorageInstance 表
    state: 实例状态 (用于前端显示)
    state_code: 实例状态码
    priority: 优先级
    hidden: 是否隐藏
    shard_name: shard名称 (可用于前端显示)
    update_at: 最后更新时间
    插入: 在 StorageInstance 表中插入实例时，同时插入 MongoDBStorageInstanceExt 表
    更新: 通过巡检任务，更新 MongoDBStorageInstanceExt 表
    删除: 通过 StorageInstance 表删除实例时，同时删除 MongoDBStorageInstanceExt 表
"""


class MongoDBStorageInstanceExt(models.Model):
    instance = models.OneToOneField(StorageInstance, on_delete=models.PROTECT)
    state = models.CharField(max_length=64, help_text=_("实例状态"), default=MongoDBStorageInstanceStatus.UNKNOWN.name)
    state_code = models.IntegerField(help_text=_("实例状态码"), default=-1)
    priority = models.IntegerField(help_text=_("优先级"), default=-1)
    hidden = models.IntegerField(help_text=_("是否隐藏"), default=0)
    # shard_name. 副本集的rs_name. 权威值在NosqlStorageSetDtl
    shard_name = models.CharField(max_length=256, help_text=_("shard名称"), default="", blank=True, null=True)
    update_at = models.DateTimeField(help_text=_("最后更新时间"), default=None, blank=True, null=True, db_index=True)
