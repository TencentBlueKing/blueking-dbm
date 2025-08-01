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
import datetime
import logging
import re

from celery.schedules import crontab
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import CCApi
from backend.components.bknodeman.client import BKNodeManApi
from backend.db_meta.models import AppCache
from backend.db_meta.models.app import TenantCache
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.dbm_init.constants import CC_APP_ABBR_ATTR
from backend.utils.tenant import TenantHandler

logger = logging.getLogger("celery")


def bulk_update_app_cache(tenant_id):
    """缓存空闲机拓扑"""
    REGEX_APP_ABBR = re.compile("^[A-Za-z0-9_-]+$")

    def format_app_abbr(app_abbr):
        if app_abbr is None:
            app_abbr = ""
        return app_abbr.lower().replace(" ", "-").replace("_", "-")

    def get_app_abbr(biz):
        """
        获取 db_app_abbr，为空则尝试从业务模型的 bk_app_abbr 同步，并会写至自定义业务属性字段: db_app_abbr
        """

        bk_app_abbr = biz.get(env.BK_APP_ABBR, "")
        db_app_abbr = biz.get(CC_APP_ABBR_ATTR, "")

        # 简单清理 bk_app_abbr 中的非法字符
        bk_app_abbr = format_app_abbr(bk_app_abbr)
        db_app_abbr = format_app_abbr(db_app_abbr)

        # 目标环境中存在 bk_app_abbr，则同步过来
        if env.BK_APP_ABBR and env.BK_APP_ABBR != CC_APP_ABBR_ATTR:
            # db_app_abbr 为空才同步，bk_app_abbr 只在create时插入，更新后，不能随便同步回来
            if not db_app_abbr and db_app_abbr != bk_app_abbr and REGEX_APP_ABBR.match(bk_app_abbr):
                logger.warning("bulk_update_app_cache: set [%s]'s bk_app_abbr to [%s]", biz["bk_biz_id"], bk_app_abbr)
                CCApi.update_business(
                    {"bk_biz_id": biz["bk_biz_id"], "db_app_abbr": bk_app_abbr, "tenant_id": tenant_id}
                )
                db_app_abbr = bk_app_abbr

        return db_app_abbr

    # 批量同步准备
    LIMIT = 1000
    start = 0
    total = CCApi.search_business({"page": {"start": 0, "limit": 1}, "tenant_id": tenant_id}).get("count", 0)

    begin_at = datetime.datetime.now(timezone.utc)
    logger.warning("bulk_update_app_cache: start update app cache total: %s", total)

    # 批量创建和更新
    create_cnt, update_cnt = 0, 0
    update_fields = [CC_APP_ABBR_ATTR, "bk_biz_name", "time_zone", "bk_biz_maintainer", "tenant_id"]
    while start < total:
        info = CCApi.search_business({"page": {"start": start, "limit": LIMIT}, "tenant_id": tenant_id}).get(
            "info", []
        )
        biz_map = {i["bk_biz_id"]: {**i, "tenant_id": tenant_id} for i in info}

        bk_biz_ids = list(biz_map.keys())
        exists = list(AppCache.objects.filter(bk_biz_id__in=bk_biz_ids).values_list("bk_biz_id", flat=True))
        not_exists = list(set(bk_biz_ids) - set(exists))

        # 整理需要批量创建的app
        new_apps = []
        for bk_biz_id in not_exists:
            cc_app = biz_map[bk_biz_id]
            db_app_abbr = get_app_abbr(cc_app)
            new_apps.append(
                AppCache(
                    tenant_id=tenant_id,
                    bk_biz_id=bk_biz_id,
                    bk_biz_name=cc_app["bk_biz_name"],
                    time_zone=cc_app["time_zone"],
                    bk_biz_maintainer=cc_app["bk_biz_maintainer"],
                    db_app_abbr=db_app_abbr,
                )
            )

        # 整理需要批量更新的app
        update_apps = []
        for app in AppCache.objects.filter(bk_biz_id__in=exists):
            need_update = False
            for field in update_fields:
                cc_app = biz_map[app.bk_biz_id]
                old_value = getattr(app, field)
                new_value = cc_app.get(field, "")

                # 英文名需要清洗后使用
                if field == CC_APP_ABBR_ATTR:
                    new_value = format_app_abbr(new_value)
                    # 清理无效则不同步
                    new_value = new_value if REGEX_APP_ABBR.match(new_value) else ""

                # 不为空且不一致才更新
                if new_value and new_value != old_value:
                    logger.info(
                        "bulk_update_app_cache[%s]: field=%s: %s -> %s", app.bk_biz_id, field, old_value, new_value
                    )
                    setattr(app, field, new_value)
                    need_update = True

                if need_update:
                    update_apps.append(app)

        AppCache.objects.bulk_create(new_apps)
        AppCache.objects.bulk_update(update_apps, fields=update_fields)
        create_cnt += len(new_apps)
        update_cnt += len(update_apps)
        logger.info("bulk_update_app_cache[%s]: new: %s, update: %s", start, len(new_apps), len(update_apps))

        start += LIMIT

    logger.warning(
        "bulk_update_app_cache [%s] finish update app cache end, create_cnt: %s, update_cnt: %s",
        (datetime.datetime.now(timezone.utc) - begin_at),
        create_cnt,
        update_cnt,
    )


@register_periodic_task(run_every=crontab(hour="*/1", minute=0))
def bulk_update_tenant_cache():
    """缓存租户信息"""
    # --- 更新租户信息 ---

    TenantHandler.update_tenant_data()

    # --- 更新租户的云区域信息 ---
    tenant_list = TenantCache.objects.all()
    update_tenants = []
    for tenant in tenant_list:
        logger.info("bulk_update_tenant_cache[%s]: update clouds", tenant.tenant_id)
        cloud_ids = [c["bk_cloud_id"] for c in BKNodeManApi.list_cloud(params={"tenant_id": tenant.tenant_id})]
        if cloud_ids != tenant.clouds:
            tenant.clouds = cloud_ids
            update_tenants.append(tenant)
    # 批量更新
    TenantCache.objects.bulk_update(update_tenants, fields=["clouds"])
    # --- 更新租户的业务信息 ---
    for tenant in tenant_list:
        logger.info("bulk_update_tenant_cache[%s]: update apps", tenant.tenant_id)
        try:
            TenantHandler.init_tenant_config(tenant.tenant_id)
        except Exception as e:
            logger.error(_("租户: {tenant_id} 更新业务信息失败: {error}").format(tenant_id=tenant.tenant_id, error=e))
            tenant.status = "disable"
            tenant.save()
