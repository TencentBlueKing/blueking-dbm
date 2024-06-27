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
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.components import CCApi
from backend.dbm_init.constants import CC_APP_ABBR_ATTR

logger = logging.getLogger("root")


class AppCache(AuditedModel):
    """CMDB业务信息缓存表"""

    bk_biz_id = models.IntegerField(primary_key=True, help_text=_("业务ID"))
    db_app_abbr = models.CharField(_("业务英文名"), max_length=128, default="")
    bk_biz_name = models.CharField(_("业务中文名"), max_length=128, default="")
    language = models.CharField(_("语言"), max_length=64, default="")
    time_zone = models.CharField(_("时区"), max_length=64, default="")
    bk_biz_maintainer = models.CharField(_("运维人员"), max_length=512, default="")

    class Meta:
        verbose_name = verbose_name_plural = _("CMDB业务信息缓存表(AppCache)")

    @classmethod
    def id_to_name(cls):
        return dict(cls.objects.values_list("bk_biz_id", "bk_biz_name"))

    @classmethod
    def get_biz_name(cls, bk_biz_id: int) -> str:
        try:
            app_cache = AppCache.objects.get(bk_biz_id=bk_biz_id)
        except AppCache.DoesNotExist:
            return str(bk_biz_id)
        return app_cache.bk_biz_name

    @classmethod
    def get_app_attr_from_cc(cls, bk_biz_id, attr_name, default=""):
        """实时从cc查询业务属性"""
        info = CCApi.search_business(
            params={
                "fields": ["bk_biz_id", CC_APP_ABBR_ATTR, attr_name],
                "biz_property_filter": {
                    "condition": "AND",
                    "rules": [{"field": "bk_biz_id", "operator": "equal", "value": int(bk_biz_id)}],
                },
            },
            use_admin=True,
        )["info"]
        return info[0].get(attr_name, "") if info else default

    @classmethod
    def get_app_attr(cls, bk_biz_id, attr_name="db_app_abbr", default=""):
        """查询缓存业务的属性"""
        try:
            app = cls.objects.get(bk_biz_id=bk_biz_id)
        except AppCache.DoesNotExist:
            logger.error("AppCache.get_app_attr: app not exist, bk_biz_id=%s", bk_biz_id)
            return cls.get_app_attr_from_cc(bk_biz_id, attr_name, default)

        return getattr(app, attr_name, default)

    @classmethod
    def batch_get_app_attr(cls, bk_biz_ids, attr_name="db_app_abbr"):
        apps = cls.objects.filter(bk_biz_id__in=bk_biz_ids)
        infos = apps.values("bk_biz_id", attr_name)
        if set(apps.values_list("bk_biz_id", flat=True)) != set(bk_biz_ids):
            infos = CCApi.search_business(
                params={
                    "fields": ["bk_biz_id", CC_APP_ABBR_ATTR, "bk_biz_name"],
                    "biz_property_filter": {
                        "condition": "AND",
                        "rules": [{"field": "bk_biz_id", "operator": "in", "value": bk_biz_ids}],
                    },
                },
                use_admin=True,
            )["info"]

        app_infos = {info["bk_biz_id"]: info[attr_name] for info in infos}
        return app_infos

    @classmethod
    def get_choices(cls):
        try:
            biz_choices = [(biz.bk_biz_id, f"[{biz.bk_biz_id}]{biz.bk_biz_name}") for biz in cls.objects.all()]
        except Exception:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            biz_choices = []
        return biz_choices
