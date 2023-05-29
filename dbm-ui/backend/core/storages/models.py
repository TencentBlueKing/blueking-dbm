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

from backend.utils.cache import class_member_cache


class BKJobFileCredential(models.Model):
    bk_biz_id = models.IntegerField(_("业务ID"), db_index=True)
    storage_type = models.CharField(_("文件源存储类型"), max_length=128, db_index=True)

    name = models.CharField(_("凭证名称"), max_length=128)
    type = models.CharField(_("凭证类型"), max_length=64)
    description = models.TextField(_("凭证描述"), default="")
    credential_id = models.CharField(_("凭证ID"), max_length=128)

    update_time = models.DateTimeField(_("更新时间"), auto_now=True, db_index=True)
    create_time = models.DateTimeField(_("创建时间"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("作业平台文件凭证")
        verbose_name_plural = _("作业平台文件凭证")
        # 唯一性校验，一个业务暂不支持配置同存储类型的多凭证
        unique_together = (("bk_biz_id", "storage_type"),)


class BKJobFileSource(models.Model):
    credential_id = models.CharField(_("凭证ID"), max_length=128, primary_key=True)
    file_source_id = models.IntegerField(_("文件源ID"), db_index=True)

    code = models.CharField(_("文件源标识"), max_length=128)
    alias = models.CharField(_("文件源别名"), max_length=128)
    access_params = models.JSONField(_("文件源接入参数"), default=dict)
    file_prefix = models.CharField(_("文件源标识"), max_length=128, default="")

    update_time = models.DateTimeField(_("更新时间"), auto_now=True, db_index=True)
    create_time = models.DateTimeField(_("创建时间"), auto_now_add=True, db_index=True)

    @property
    @class_member_cache()
    def credential(self):
        return BKJobFileCredential.objects.get(credential_id=self.credential_id)

    @credential.setter
    def credential(self, value):
        if self.credential_id != value.id:
            self.credential_id = value.id
            self.save()
        self._credential = value

    class Meta:
        verbose_name = _("作业平台文件源")
        verbose_name_plural = _("作业平台文件源")
