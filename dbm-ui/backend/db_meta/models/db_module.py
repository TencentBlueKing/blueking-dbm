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
import logging

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import AppCache

logger = logging.getLogger("root")


class DBModule(AuditedModel):
    """
    一个 meta_cluster_type 的 db_module 在 cc 上会有 count(meta_type) 个 bk module
    """

    bk_biz_id = models.IntegerField(default=0)
    db_module_name = models.CharField(default="", max_length=200)
    db_module_id = models.BigAutoField(primary_key=True)
    cluster_type = models.CharField(max_length=64, choices=ClusterEntryType.get_choices(), default="")

    class Meta:
        verbose_name = verbose_name_plural = _("DB模块(DBModule)")
        unique_together = [
            ("db_module_id", "bk_biz_id", "cluster_type"),
            ("db_module_name", "bk_biz_id", "cluster_type"),
        ]

    @classmethod
    def db_module_map(cls):
        return dict(cls.objects.values_list("db_module_id", "db_module_name"))

    @classmethod
    def get_choices(cls):
        try:
            db_module_choices = [
                (module.db_module_id, f"[{module.db_module_id}]{module.cluster_type}-{module.db_module_name}")
                for module in cls.objects.all()
            ]
        except Exception:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            db_module_choices = []
        return db_module_choices

    @classmethod
    def get_choices_with_filter(cls, cluster_type=None):
        try:
            q = Q()
            if cluster_type:
                q = Q(cluster_type=cluster_type)

            # logger.info("get db module choices with filter: {}".format(q))

            db_module_choices = []

            for dm in cls.objects.filter(q).all():

                try:
                    app = AppCache.objects.get(bk_biz_id=dm.bk_biz_id)
                    db_module_choices.append(
                        (
                            dm.db_module_id,
                            f"[{dm.db_module_id}]-[{dm.cluster_type}]-[app:{app.db_app_abbr}]-{dm.db_module_name}",
                        )
                    )
                except AppCache.DoesNotExist:
                    continue

            # db_module_choices = [
            #     (module.db_module_id, f"[{module.db_module_id}]{module.cluster_type}-{module.db_module_name}")
            #     for module in cls.objects.filter(q)
            # ]
        except Exception:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            db_module_choices = []
        return db_module_choices
