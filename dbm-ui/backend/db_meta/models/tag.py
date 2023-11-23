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
from backend.db_meta.enums.comm import TagType
from backend.db_meta.models import Cluster


class Tag(AuditedModel):
    bk_biz_id = models.IntegerField(default=0)
    name = models.CharField(max_length=64, default="", help_text=_("tag名称"))
    type = models.CharField(max_length=64, help_text=_("tag类型"), choices=TagType.get_choices())
    cluster = models.ManyToManyField(Cluster, blank=True, help_text=_("关联集群"))

    class Meta:
        unique_together = ["bk_biz_id", "name"]

    @property
    def tag_desc(self):
        """仅返回tag的信息"""
        return {"bk_biz_id": self.bk_biz_id, "name": self.name, "type": self.type}
