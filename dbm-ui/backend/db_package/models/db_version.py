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
import math

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums.version_phase import VersionPhase

from .version_series import VersionSeries


class DBVersion(AuditedModel):
    """
    full version 是 a.b.c.d.e.f 这样的 6 段式
    major version 是 a.b
    base version 是 a.b.c
    sub version 是 d.e.f
    每一个 segment 必须在 (0, 999) 的范围内. 这样整个 6 段拼出来的数值版本号 < 2^63, 在 bigint 域内可以比较
    """

    full_version = models.CharField(max_length=128, default="", help_text=_("完整版本"))
    name = models.CharField(max_length=128, default="", help_text=_("版本名称"))
    distribution_snapshot = models.JSONField(null=True, help_text=_("发行版快照"), default=dict)
    distribution_id = models.IntegerField(help_text=_("发行版ID"))
    version_series = models.ForeignKey(VersionSeries, on_delete=models.PROTECT, null=True, blank=True)
    phase = models.CharField(max_length=128, choices=VersionPhase.get_choices(), help_text=_("版本阶段"))
    enable = models.BooleanField(default=True, help_text=_("版本启用"))
    description = models.TextField(default="", blank=True, help_text=_("版本描述"))
    recommend = models.BooleanField(default=False, help_text=_("版本推荐"))

    class Meta:
        app_label = "db_meta"
        unique_together = [("full_version", "distribution_id"), ("name", "distribution_id")]

    def save(self, *args, **kwargs):
        if self.full_version:
            split_fv = self.full_version.split(".")
            if len(split_fv) != 6:
                raise ValidationError(_("%(value)s must look like a.b.c.d.e.f"), params={"value": self.full_version})
        else:
            raise ValidationError(_("完整版本号不能为空"))

            # 先不检查版本号大小了, 不同 db 组件自己写吧
            # bad_seg = []
            # for seg in split_fv:
            #     seg_int = int(seg)
            #     if seg_int > 999 or seg_int < 0:
            #         bad_seg.append(seg)
            #
            # if bad_seg:
            #     raise ValidationError(_("%(seg)s must gt 0 and lt 999"), params={"seg": bad_seg})
        if not self.version_series_id:
            raise ValidationError(_("版本系列不能为空"))

        self.distribution_snapshot = self.version_series.distribution.snapshot()
        self.distribution_id = self.version_series.distribution_id
        super(DBVersion, self).save(*args, **kwargs)

    def __version_s(self, from_p: int, end_p: int) -> str:
        return ".".join(self.full_version.split(".")[from_p:end_p])

    @staticmethod
    def __version_n(vs: str) -> int:
        split_vs = vs.split(".")
        vn = 0
        for i, seg in enumerate(split_vs):
            vn += int(seg) * math.pow(10, (len(split_vs) - i - 1) * 3)

        return int(vn)

    @property
    def major_version(self) -> str:
        return self.__version_s(0, 2)

    @property
    def base_version(self) -> str:
        return self.__version_s(0, 3)

    @property
    def sub_version(self) -> str:
        return self.__version_s(3, 6)

    @property
    def full_version_n(self) -> int:
        return self.__version_n(self.full_version)

    @property
    def major_version_n(self) -> int:
        return self.__version_n(self.major_version)

    @property
    def base_version_n(self) -> int:
        return self.__version_n(self.base_version)

    @property
    def sub_version_n(self) -> int:
        return self.__version_n(self.sub_version)
