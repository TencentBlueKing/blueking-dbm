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

from django.core.management.base import BaseCommand

from backend import env
from backend.components import CCApi
from backend.exceptions import ApiResultError

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "实例标签app_id改为appid"

    def handle(self, *args, **options):
        bk_biz_id = env.DBA_APP_BK_BIZ_ID

        bad_instance_ids = set()
        bk_instance_ids = [
            i["id"]
            for i in CCApi.list_service_instance({"bk_biz_id": bk_biz_id, "page": {"start": 0, "limit": 500}})["info"]
        ]

        logger.info("try to update instance: %s, %s", bk_instance_ids, len(bk_instance_ids))

        try:
            CCApi.remove_label_from_service_instance(
                {
                    "bk_biz_id": bk_biz_id,
                    "instance_ids": bk_instance_ids,
                    "keys": ["app_id"],
                }
            )
            logger.info("remove_label_from_service_instance success")
        except ApiResultError as e:
            logger.error("remove_label_from_service_instance bk_instance_ids: %s, error: %s", bk_instance_ids, e)
            for bk_instance_id in bk_instance_ids:
                try:
                    CCApi.remove_label_from_service_instance(
                        {
                            "bk_biz_id": bk_biz_id,
                            "instance_ids": [bk_instance_id],
                            "keys": ["app_id"],
                        }
                    )
                except ApiResultError:
                    bad_instance_ids.add(bad_instance_ids)

        try:
            CCApi.add_label_for_service_instance(
                {
                    "bk_biz_id": bk_biz_id,
                    "instance_ids": bk_instance_ids,
                    "labels": {"appid": str(bk_biz_id)},
                }
            )
        except ApiResultError as e:
            logger.error("add_label_for_service_instance bk_instance_ids: %s, error: %s", bk_instance_ids, e)
            step_size = 99
            count = len(bk_instance_ids)
            for step in range(count // step_size + 1):
                instance_ids = bk_instance_ids[step * step_size : (step + 1) * step_size]
                logger.info("add_label_for_service_instance: %s" % instance_ids)
                try:
                    CCApi.add_label_for_service_instance(
                        {
                            "bk_biz_id": bk_biz_id,
                            "instance_ids": instance_ids,
                            "labels": {"appid": str(bk_biz_id)},
                        }
                    )
                except ApiResultError:
                    bad_instance_ids.update(instance_ids)

        total_stats = f"bad instances: {bad_instance_ids}, good instances: {set(bk_instance_ids) - bad_instance_ids}"
        logger.info(total_stats)
