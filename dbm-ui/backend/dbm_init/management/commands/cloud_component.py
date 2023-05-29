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
from django.utils.translation import ugettext as _

from backend.ticket.handler import TicketHandler

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "初始化云区域组件"

    def add_arguments(self, parser):
        parser.add_argument("-b", "--biz", help="机器所在的业务ID", type=int)
        parser.add_argument("-c", "--cloud", help="云区域ID", type=int, default=0)
        parser.add_argument("-p", "--ips", help="云区域组件所需的两台机器，IP输入以,分割", type=str)

    def handle(self, *args, **options):
        bk_biz_id = options["biz"]
        bk_cloud_id = options["cloud"]
        ips = options["ips"].split(",")

        try:
            TicketHandler.fast_create_cloud_component_method(bk_biz_id, bk_cloud_id, ips)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(_("云区域组件初始化失败，错误信息:{}").format(e))
