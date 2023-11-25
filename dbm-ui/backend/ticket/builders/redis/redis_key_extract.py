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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import (
    KEY_FILE_PREFIX,
    BaseRedisTicketFlowBuilder,
    RedisKeyBaseDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisKeyExtractDetailSerializer(RedisKeyBaseDetailSerializer):
    pass


class RedisKeyExtractFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_keys_extract

    def format_ticket_data(self):
        """
        {
            "rules": [
                {
                    "cluster_id": 11,
                    "path": "/redis/keyfiles/{ticket_id}.{domain}/",
                    "domain": "cache.moyelocaltest.redistest.db",
                    "white_regex": "test*",
                    "black_regex": ""
                },
                {
                    "cluster_id": 22,
                    "path": "/redis/keyfiles/{ticket_id}.{domain}/",
                    "domain": "cache.abc.redistest.db",
                    "white_regex": "",
                    "black_regex": "test*"
                }
            ],
            "uid": 340,
            "ticket_type": "REDIS_KEYS_EXTRACT",
            "created_by": "admin",
            "bk_biz_id": 1111,
            "fileserver": {
                "url": "制品库地址",
                "bucket": "目标bucket",
                "password": "制品库token"
                "username": "制品库username"
                "project": "制品库project"
            }
        }
        """

        # 填充文件保存路径，不包括project和bucket部分
        for rule in self.ticket_data["rules"]:
            # key文件名格式要求：{project}/{bucket}/{rule['path']}/biz.ip.keys.x
            biz_domain_name = f'{self.ticket.id}.{rule["domain"]}'
            rule["path"] = f"{KEY_FILE_PREFIX}/{biz_domain_name}"

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


@builders.BuilderFactory.register(TicketType.REDIS_KEYS_EXTRACT)
class RedisKeyExtractFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisKeyExtractDetailSerializer
    inner_flow_builder = RedisKeyExtractFlowParamBuilder
    inner_flow_name = _("提取Key")
    default_need_itsm = False
