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
from typing import Dict

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.models import AuditedModel
from backend.components import CCApi
from backend.dbm_init.constants import CC_APP_ABBR_ATTR

logger = logging.getLogger("root")


class TenantCache(AuditedModel):
    """租户信息缓存表"""

    tenant_id = models.CharField(primary_key=True, max_length=128, help_text=_("租户ID"))
    tenant_name = models.CharField(_("租户名称"), max_length=128, default="")
    status = models.CharField(_("状态"), max_length=64, default="enabled")
    admin = models.CharField(_("管理员"), max_length=128, default="admin")
    clouds = models.JSONField(_("云区域列表"), default=[])
    dba_app_id = models.IntegerField(help_text=_("当前租户默认业务ID"), default=0)
    dba_job_id = models.IntegerField(help_text=_("当前租户默认JOB执行业务集ID"), default=0)

    class Meta:
        verbose_name = verbose_name_plural = _("租户信息缓存表(TenantCache)")

    @classmethod
    def get_tenant_cache(cls) -> Dict[str, Dict]:
        """获取租户缓存信息"""
        if not cache.get("tenant_cache"):
            tenant_cache = {tenant.tenant_id: tenant.to_dict() for tenant in cls.objects.all()}
            cache.set("tenant_cache", tenant_cache, 60 * 60)
        return cache.get("tenant_cache")

    @classmethod
    def get_cloud_tenant_cache(cls) -> Dict[int, str]:
        """获取租户和云区域的缓存信息"""
        if not cache.get("cloud_tenant_cache"):
            cloud_tenant_map = {cloud: tenant.tenant_id for tenant in cls.objects.all() for cloud in tenant.clouds}
            cache.set("cloud_tenant_cache", cloud_tenant_map, 60 * 60)
        return cache.get("cloud_tenant_cache")

    @classmethod
    def get_tenant_attr(cls, tenant_id, attr_name, default=None):
        """获取租户属性"""
        tenant_cache = cls.get_tenant_cache()
        return tenant_cache.get(tenant_id, {}).get(attr_name, default)

    @classmethod
    def get_tenant_with_cloud(cls, bk_cloud_id):
        """根据云区域ID获取租户ID TODO: 这个方法并不准确，直连区域的租户共享"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return settings.DEFAULT_TENANT_ID
        return cls.get_cloud_tenant_cache().get(bk_cloud_id, "")

    @classmethod
    def get_tenant_with_app(cls, bk_biz_id=str):
        """根据业务ID获取租户ID"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return settings.DEFAULT_TENANT_ID
        tenant_id = AppCache.get_appcache(key="appcache_dict").get(str(bk_biz_id), {}).get("tenant_id", "")
        return tenant_id

    @classmethod
    def get_tenant_dba_app(cls, tenant_id):
        """获取租户的dba_app_id"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return env.DBA_APP_BK_BIZ_ID
        return cls.get_tenant_attr(tenant_id, "dba_app_id", env.DBA_APP_BK_BIZ_ID)

    @classmethod
    def get_tenant_dba_job(cls, tenant_id):
        """获取租户的dba_job_id"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return env.JOB_BLUEKING_BIZ_ID
        return cls.get_tenant_attr(tenant_id, "dba_job_id", env.JOB_BLUEKING_BIZ_ID)

    def to_dict(self):
        """对象转换为字典格式"""
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "status": self.status,
            "admin": self.admin,
            "clouds": self.clouds,
            "dba_app_id": self.dba_app_id,
            "dba_job_id": self.dba_job_id,
        }


class AppCache(AuditedModel):
    """CMDB业务信息缓存表"""

    bk_biz_id = models.IntegerField(primary_key=True, help_text=_("业务ID"))
    db_app_abbr = models.CharField(_("业务英文名"), max_length=128, default="")
    bk_biz_name = models.CharField(_("业务中文名"), max_length=128, default="")
    language = models.CharField(_("语言"), max_length=64, default="")
    time_zone = models.CharField(_("时区"), max_length=64, default="")
    bk_biz_maintainer = models.CharField(_("运维人员"), max_length=512, default="")
    tenant_id = models.CharField(help_text=_("租户ID"), max_length=128, default="default")

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
        bk_biz_ids = list(set(bk_biz_ids))
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
    def get_appcache(cls, key):
        if key not in ["appcache_list", "appcache_dict"]:
            raise ValueError(_("缓存key不存在，请检查key是否为appcache_dict/appcache_list"))
        if not cache.get(key):
            from backend.db_meta.utils import cache_appcache_data

            cache_appcache_data(cls)

        return cache.get(key)

    @classmethod
    def get_choices(cls):
        try:
            appcache_data = cls.get_appcache("appcache_list")
            biz_choices = [(app["bk_biz_id"], f"[{app['bk_biz_id']}]{app['bk_biz_name']}") for app in appcache_data]
        except Exception:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            biz_choices = []
        return biz_choices

    @classmethod
    def get_tenant_biz_ids(cls, tenant_id):
        """获取租户下的业务ID列表，使用缓存"""
        cache_key = f"tenant_biz_ids_{tenant_id}"
        if not cache.get(cache_key):
            biz_ids = list(cls.objects.filter(tenant_id=tenant_id).values_list("bk_biz_id", flat=True))
            cache.set(cache_key, biz_ids, 60 * 60 * 24)  # 缓存1小时
        return cache.get(cache_key)
