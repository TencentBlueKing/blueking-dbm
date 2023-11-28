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
