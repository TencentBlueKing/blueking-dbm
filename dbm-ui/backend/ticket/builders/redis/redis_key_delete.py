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
import os

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.core.storages.storage import get_storage
from backend.db_services.redis.constants import KeyDeleteType
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import (
    KEY_FILE_PREFIX,
    BaseRedisTicketFlowBuilder,
    RedisBasePauseParamBuilder,
    RedisKeyBaseDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisKeyDeleteDetailSerializer(RedisKeyBaseDetailSerializer):
    delete_type = serializers.ChoiceField(help_text=_("删除方式"), choices=KeyDeleteType.get_choices())


class RedisKeyDeleteFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_keys_delete

    def format_ticket_data(self):
        """
        {
            "rules": [
                {
                    "cluster_id": 11,
                    "path": "",
                    "domain": "cache.moyelocaltest.redistest.db",
                    "white_regex": "test*",
                    "black_regex": ""
                },
                {
                    "cluster_id": 22,
                    "path": "",
                    "domain": "cache.abc.redistest.db",
                    "white_regex": "",
                    "black_regex": "test*"
                }
            ],
            "uid": 340,
            "ticket_type": "REDIS_KEYS_DELETE",
            "created_by": "admin",
            "bk_biz_id": 1111,
            "delete_type": "regex/files",
            "fileserver": {
                "url": "制品库地址",
                "bucket": "目标bucket",
                "password": "制品库token",
                "username": "制品库username",
                "project": "制品库project"
            }
        }
        """

        storage = get_storage()
        delete_type = self.ticket_data["delete_type"]

        # 填充文件保存路径，不包括project和bucket部分
        for rule in self.ticket_data["rules"]:

            # 补充total_size，用于筛选临时
            if delete_type == KeyDeleteType.BY_FILES:
                rule["path"] = os.path.join(KEY_FILE_PREFIX, rule["path"])
                _, files = storage.listdir(rule["path"])
                rule["total_size"] = sum(f["size"] for f in files)
            else:
                biz_domain_name = f'{self.ticket.id}.{rule["domain"]}'
                rule["path"] = os.path.join(KEY_FILE_PREFIX, biz_domain_name)

        self.ticket_data.update(
            {
                "fileserver": {
                    "url": settings.BKREPO_ENDPOINT_URL,
                    "bucket": settings.BKREPO_BUCKET,
                    "password": settings.BKREPO_PASSWORD,
                    "username": settings.BKREPO_USERNAME,
                    "project": settings.BKREPO_PROJECT,
                }
            }
        )


@builders.BuilderFactory.register(TicketType.REDIS_KEYS_DELETE)
class RedisKeyDeleteFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisKeyDeleteDetailSerializer
    inner_flow_builder = RedisKeyDeleteFlowParamBuilder
    inner_flow_name = _("删除Key")
    pause_node_builder = RedisBasePauseParamBuilder

    @property
    def need_manual_confirm(self):
        return True
