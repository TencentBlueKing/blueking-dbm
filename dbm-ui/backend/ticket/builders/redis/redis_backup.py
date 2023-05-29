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
    BaseRedisTicketFlowBuilder,
    RedisBasePauseParamBuilder,
    RedisOpsBaseDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisBackupDetailSerializer(RedisOpsBaseDetailSerializer):
    pass


class RedisBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_backup

    def format_ticket_data(self):
        """
        {
            "rules": [
                {
                    "cluster_id": 120,
                    "domain": "cache.twemproxyredisinstance.hs1.dba.db",
                    "target": "slave",
                    "backup_type": "normal_backup"
                },
                {
                    "cluster_id": 121,
                    "domain": "cache.twemproxyredisinstance.hs3.dba.db",
                    "target": "master",
                    "backup_type": "normal_backup"
                }
            ],
            "uid": 340,
            "ticket_type": "REDIS_BACKUP",
            "created_by": "admin",
            "bk_biz_id": 1111,
            "backup_server": {
                "url": "制品库地址",
                "bucket": "目标bucket",
                "password": "制品库token",
                "username": "制品库username",
                "project": "制品库project"
            }
        }
        """

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


@builders.BuilderFactory.register(TicketType.REDIS_BACKUP)
class RedisBackupFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisBackupDetailSerializer
    inner_flow_builder = RedisBackupFlowParamBuilder
    inner_flow_name = _("集群备份")
    pause_node_builder = RedisBasePauseParamBuilder

    @property
    def need_manual_confirm(self):
        return True

    @property
    def need_itsm(self):
        return False
