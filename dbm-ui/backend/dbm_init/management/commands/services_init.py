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

from django.core.management.base import BaseCommand

from backend.dbm_init.services import Services


class Command(BaseCommand):
    help = "During the application deployment phase, automate the initial related third-party services"

    def add_arguments(self, parser):
        parser.add_argument(
            "srv_type",
            type=str,
            choices=["all", "itsm", "bklog", "bkcc", "bkmonitor_alarm", "bkmonitor_channel", "bkjob", "ssl"],
            help="all: initialize all services, "
            "itsm: initialize itsm service, "
            "bklog: initialize bk-log services"
            "bkcc: initialize bk-cc services"
            "bkjob: initialize bk-job services"
            "ssl: create and upload ssl files to bkrepo"
            "bkmonitor_channel: initialize bk-monitor report services"
            "bkmonitor_alarm: initialize bk-bkmonitor alarm services",
        )

    def handle(self, *args, **options):
        srv_type = options["srv_type"]

        if srv_type == "all" or srv_type == "itsm":
            Services.auto_create_itsm_service()

        if srv_type == "all" or srv_type == "bklog":
            Services.auto_create_bklog_service()

        if srv_type == "all" or srv_type == "bkcc":
            Services.auto_create_bkcc_service()

        if srv_type == "all" or srv_type == "bkjob":
            Services.auto_create_bkjob_service()

        if srv_type == "all" or srv_type == "bkmonitor_alarm":
            Services.auto_create_bkmonitor_alarm()

        if srv_type == "all" or srv_type == "bkmonitor_channel":
            Services.auto_create_bkmonitor_channel()

        if srv_type == "all" or srv_type == "ssl":
            Services.auto_create_ssl_service()
