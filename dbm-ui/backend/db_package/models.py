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
from typing import Optional

import django.utils.timezone as timezone
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.db_package.constants import PackageMode, PackageType
from backend.db_package.exceptions import PackageNotExistException
from backend.flow.consts import MediumEnum


class Package(AuditedModel):
    name = models.CharField(_("文件名"), max_length=LEN_LONG)
    version = models.CharField(_("版本号"), max_length=LEN_NORMAL)
    pkg_type = models.CharField(_("安装包类型"), choices=PackageType.get_choices(), max_length=LEN_SHORT)
    db_type = models.CharField(
        _("存储类型"), choices=DBType.get_choices(), max_length=LEN_SHORT, default=DBType.MySQL.value
    )
    path = models.CharField(_("包路径"), max_length=LEN_LONG)
    size = models.IntegerField(_("包大小"))
    md5 = models.CharField(_("md5值"), max_length=LEN_SHORT)
    # allow_biz_ids 主要用于灰度场景，部分业务先用，不配置/为空 代表全业务可用
    allow_biz_ids = models.JSONField(_("允许的业务列表"), null=True)
    mode = models.CharField(_("安装包模式"), choices=PackageMode.get_choices(), max_length=LEN_SHORT, default="system")
    # package独立出时间字段
    create_at = models.DateTimeField(_("创建时间"), default=timezone.now)
    update_at = models.DateTimeField(_("更新时间"), default=timezone.now)

    class Meta:
        verbose_name = _("介质包（Package）")
        ordering = ("-create_at",)

    @classmethod
    def get_latest_package(
        cls,
        version: str,
        pkg_type: str,
        bk_biz_id: Optional[int] = None,
        db_type: Optional[str] = DBType.MySQL,
        name: Optional[str] = None,
    ) -> "Package":
        """
        根据版本和包类型获取最新的介质包
        """
        if version == MediumEnum.Latest:
            # 引进制品版本管理后，默认最新版就是最近上传的介质
            packages = cls.objects.filter(pkg_type=pkg_type, db_type=db_type)
        else:
            packages = cls.objects.filter(version=version, pkg_type=pkg_type, db_type=db_type)
        if bk_biz_id:
            # 过滤出灰度的业务以及无指定业务的包
            packages = packages.filter(Q(allow_biz_ids__contains=bk_biz_id) | Q(allow_biz_ids__isnull=True))

        if not packages:
            raise PackageNotExistException(version=version, pkg_type=pkg_type, db_type=db_type)

        # 取最新的版本
        package = packages.order_by("-update_at").first()
        return package
