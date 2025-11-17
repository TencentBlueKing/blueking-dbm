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
from backend.utils.tenant import TenantHandler


class BaseReportManager(models.Manager):
    def create(self, **kwargs):
        # 获取租户id
        bk_biz_id = kwargs.get("bk_biz_id")
        kwargs["tenant_id"] = TenantHandler.get_tenant_id_by_biz(bk_biz_id)
        return super().create(**kwargs)

    def bulk_create(self, objs, **kwargs):
        for obj in objs:
            if not obj.tenant_id:
                obj.tenant_id = TenantHandler.get_tenant_id_by_biz(obj.bk_biz_id)
        return super().bulk_create(objs, **kwargs)


class BaseReportABS(AuditedModel):
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务的 cmdb id"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 id"))
    # TODO: status考虑废弃。替换成state，丰富字段表达
    status = models.BooleanField(default=True, help_text=_("巡检结果状态, 默认正常"))  # True = 正常, False = 异常
    state = models.CharField(default="", max_length=64, help_text=_("巡检结果状态"))
    failed_days = models.IntegerField(default=0, help_text=_("失败持续天数"))
    msg = models.TextField(default="", help_text=_("备注信息"))
    tenant_id = models.CharField(help_text=_("租户ID"), max_length=128, default="default")

    objects = BaseReportManager()

    class Meta:
        abstract = True
