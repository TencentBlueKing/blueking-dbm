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

from celery.schedules import crontab

from backend import env
from backend.components import CCApi
from backend.db_meta.models import AppCache
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.dbm_init.constants import CC_APP_ABBR_ATTR

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/20"))
def update_app_cache():
    """缓存空闲机拓扑"""
    now = datetime.datetime.now()
    logger.warning("[db_meta] start update app cache start: %s", now)

    bizs = CCApi.search_business().get("info", [])

    updated_bizs, created_bizs = [], []
    for biz in bizs:
        try:
            logger.warning("[db_meta] sync app : %s", biz["bk_biz_id"])
            bk_app_abbr = biz.get(env.BK_APP_ABBR, "")
            db_app_abbr = biz.get(CC_APP_ABBR_ATTR, "").lower().replace(" ", "-").replace("_", "-")

            # 目标环境中存在bk_app_abbr，则同步过来
            if env.BK_APP_ABBR and env.BK_APP_ABBR != CC_APP_ABBR_ATTR:
                # db_app_abbr为空才同步
                if not db_app_abbr and db_app_abbr != bk_app_abbr:
                    CCApi.update_business(
                        {"bk_biz_id": biz["bk_biz_id"], "data": {"db_app_abbr": bk_app_abbr}}, use_admin=True
                    )
                    db_app_abbr = bk_app_abbr

            # update or create fields
            defaults = {
                "bk_biz_name": biz["bk_biz_name"],
                "language": biz["language"],
                "time_zone": biz["time_zone"],
                "bk_biz_maintainer": biz["bk_biz_maintainer"],
            }

            # 英文为空，则不更新进去，避免覆盖提单时刚写入的英文名
            if not db_app_abbr:
                defaults["db_app_abbr"] = db_app_abbr

            obj, created = AppCache.objects.update_or_create(
                defaults=defaults,
                bk_biz_id=biz["bk_biz_id"],
            )

            if created:
                created_bizs.append(obj.bk_biz_id)
            else:
                updated_bizs.append(obj.bk_biz_id)
        except Exception as e:  # pylint: disable=wildcard-import
            logger.error("[db_meta] cache app error: %s (%s)", biz, e)

    logger.warning(
        "[db_meta] finish update app cache end: %s, create_cnt: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        len(created_bizs),
        len(updated_bizs),
    )


@register_periodic_task(run_every=crontab(minute="*/20"))
def bulk_update_app_cache():
    """缓存空闲机拓扑"""

    def get_db_app_abbr(biz):
        """TODO（好绕的逻辑）: 获取db_app_abbr，为空则尝试从bk_app_abbr同步"""
        bk_app_abbr = biz.get(env.BK_APP_ABBR, "")
        db_app_abbr = biz.get(CC_APP_ABBR_ATTR, "").lower().replace(" ", "-").replace("_", "-")

        # 目标环境中存在bk_app_abbr，则同步过来
        if env.BK_APP_ABBR and env.BK_APP_ABBR != CC_APP_ABBR_ATTR:
            # db_app_abbr为空才同步
            if not db_app_abbr and db_app_abbr != bk_app_abbr:
                CCApi.update_business(
                    {"bk_biz_id": biz["bk_biz_id"], "data": {"db_app_abbr": bk_app_abbr}}, use_admin=True
                )
                db_app_abbr = bk_app_abbr

        return db_app_abbr

    LIMIT = 500
    total = CCApi.search_business({"page": {"start": 0, "limit": 1}}).get("count", 0)
    start = 0

    begin_at = datetime.datetime.now()
    logger.warning("bulk_update_app_cache: start update app cache start: total", total)

    # 批量创建和更新
    create_cnt, update_cnt = 0, 0
    update_fields = [CC_APP_ABBR_ATTR, "bk_biz_name", "time_zone", "bk_biz_maintainer"]
    while start < total:
        info = CCApi.search_business({"page": {"start": start, "limit": LIMIT}}).get("info", [])
        biz_map = {i["bk_biz_id"]: i for i in info}

        bk_biz_ids = list(biz_map.keys())
        exists = list(AppCache.objects.filter(bk_biz_id__in=bk_biz_ids).values_list("bk_biz_id", flat=True))
        not_exists = list(set(bk_biz_ids) - set(exists))

        # 整理需要批量创建的app
        new_apps = []
        for bk_biz_id in not_exists:
            cc_app = biz_map[bk_biz_id]
            db_app_abbr = get_db_app_abbr(cc_app)
            new_apps.append(
                AppCache(
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
                new_value = cc_app[field]
                old_value = getattr(app, field)
                if new_value != old_value:
                    logger.info("bulk_update_app_cache[%s]: %s:%s -> %s:%s", start, field, old_value, field, new_value)
                    setattr(cc_app, field, new_value)
                    need_update = True

                if need_update:
                    update_apps.append(AppCache)

        AppCache.objects.bulk_create(new_apps)
        AppCache.objects.bulk_update(update_apps, fields=update_fields)
        create_cnt += len(new_apps)
        update_cnt += len(update_apps)
        logger.info("bulk_update_app_cache[%s]: new: %s, update: %s", start, len(new_apps), len(update_apps))

        start += LIMIT

    logger.warning(
        "bulk_update_app_cache [%s] finish update app cache end: %s, create_cnt: %s, update_cnt: %s",
        datetime.datetime.now() - begin_at,
        create_cnt,
        update_cnt,
    )
