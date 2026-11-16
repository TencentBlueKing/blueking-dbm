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
from typing import Dict

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType


class Distribution(AuditedModel):
    """
    安装包的来源, 比如
    txsql, 社区版等等
    同时, 由于要兼容 Tokudb 和 Rocksdb, 这2个也当做独立发行版

    example:
    {
        name: Tokudb,
        engine: Tokudb,
        db_type: MySQL,
        pkg_type: MySQL
    }
    {
        name: DBM,
        engine: "",
        db_type: MySQL,
        pkg_type: dbactuator
    }
    """

    name = models.CharField(max_length=256, default="", help_text=_("发行版"))
    engine = models.CharField(max_length=64, default="", help_text=_("引擎"))  # mysql 特有

    db_type = models.CharField(max_length=128, choices=DBType.get_choices())
    pkg_type = models.CharField(max_length=128)

    class Meta:
        app_label = "db_meta"

    def snapshot(self) -> Dict:
        return {
            "id": self.pk,
            "name": self.name,
            "engine": self.engine,
            "db_type": self.db_type,
            "pkg_type": self.pkg_type,
        }

    @classmethod
    def init_distribution(cls):
        """
        初始化发行版，只在一个环境初始化的时候发起
        以 INIT_DB_PKG_SETTINGS 为准, 发行版/引擎取值参考 medium.lock，缺省为 ("DBM", "")
        """
        from backend.db_package.constants import INIT_DB_PKG_SETTINGS

        distribution_list = [
            cls(name=name, engine=engine, db_type=db_type, pkg_type=str(pkg["value"]))
            for db_type, pkgs in INIT_DB_PKG_SETTINGS.items()
            for pkg in pkgs
            for name, engine in pkg.get("distributions", [("DBM", "")])
        ]
        cls.objects.bulk_create(distribution_list)
