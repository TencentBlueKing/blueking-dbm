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

from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save

logger = logging.getLogger("root")


def init_ticket_flow_config(sender, **kwargs):
    from backend.ticket.handler import TicketHandler

    try:
        TicketHandler.ticket_flow_config_init()
    except Exception as err:  # pylint: disable=broad-except:
        logger.warning(f"ticket_flow_config_init occur error, {err}")


class TicketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.ticket"

    def ready(self):
        from backend.ticket.builders import register_all_builders
        from backend.ticket.models import Flow
        from backend.ticket.signals import update_ticket_status
        from backend.ticket.todos import register_all_todos

        register_all_builders()
        register_all_todos()
        post_migrate.connect(init_ticket_flow_config, sender=self)
        post_save.connect(update_ticket_status, sender=Flow)
