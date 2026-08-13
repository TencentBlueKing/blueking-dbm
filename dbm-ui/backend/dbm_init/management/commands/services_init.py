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

from backend import env
from backend.dbm_init.services import Services


class Command(BaseCommand):
    help = "During the application deployment phase, automate the initial related third-party services"

    def add_arguments(self, parser):
        parser.add_argument(
            "srv_type",
            type=str,
            choices=[
                "all",
                "itsm",
                "bklog",
                "bkcc",
                "iam",
                "bkmonitor_alarm",
                "bkmonitor_channel",
                "register_application",
                "grafana",
                "bkjob",
                "dbm_services",
                "ssl",
                "sync_dbconfig",
                "create_job_user",
            ],
            help="all: initialize all services, "
            "itsm: initialize itsm service, "
            "bklog: initialize bk-log services, "
            "bkcc: initialize bk-cc services"
            "bkjob: initialize bk-job services"
            "ssl: create and upload ssl files to bkrepo"
            "bkmonitor_channel: initialize bk-monitor report services"
            "bkmonitor_alarm: initialize bk-bkmonitor alarm services"
            "register_application: register applications into bk_notice"
            "grafana: initialize grafana services"
            "sync_dbconfig: sync dbconfig to bkrepo"
            "create_job_user: create job user"
            "dbm_services: initialize dbm micro services"
            "register_application: register applications into bk_notice",
        )
        parser.add_argument("--namespace", type=str, required=False, help="Namespace for dbconfig")
        parser.add_argument("--conf_type", type=str, required=False, help="Type of configuration")
        parser.add_argument("--conf_file", type=str, required=False, help="Path to configuration file")
        parser.add_argument("--account_list", type=str, required=False, help="account list, e.g. 'mysql,mysql_test'")
        parser.add_argument(
            "--max_workers",
            type=int,
            required=False,
            default=1,
            help="Max concurrent workers for sync_dbconfig (default: 1)",
        )

    def handle(self, *args, **options):
        srv_type = options["srv_type"]

        if srv_type == "all" or srv_type == "itsm":
            if str(env.ITSM_API_VERSION).lower() == "v4":
                Services.auto_create_itsm_v4_service()
            else:
                Services.auto_create_itsm_service()

        if srv_type == "all" or srv_type == "bklog":
            Services.auto_create_bklog_service()

        if srv_type == "all" or srv_type == "bkcc":
            Services.auto_create_bkcc_service()

        if srv_type == "all" or srv_type == "bkjob":
            Services.auto_create_bkjob_service()

        if srv_type == "all" or srv_type == "dbm_services":
            Services.auto_create_dbm_services()

        if srv_type == "all" or srv_type == "bkmonitor_alarm":
            Services.auto_create_bkmonitor_alarm()

        if srv_type == "all" or srv_type == "bkmonitor_channel":
            Services.auto_create_bkmonitor_channel()

        if srv_type == "all" or srv_type == "grafana":
            Services.auto_init_grafana()

        if srv_type == "all" or srv_type == "ssl":
            Services.auto_create_ssl_service()

        if srv_type == "all" or srv_type == "register_application":
            Services.auto_register_application()

        if srv_type == "all" or srv_type == "iam":
            Services.auto_create_iam_migrations()

        if srv_type == "sync_dbconfig":
            namespace = options["namespace"]
            conf_type = options["conf_type"]
            conf_file = options["conf_file"]
            max_workers = options["max_workers"]
            Services.auto_sync_dbconfig(namespace, conf_type, conf_file, max_workers)

        if srv_type == "all" or srv_type == "create_job_user":
            account_list_str = options["account_list"]
            account_list = account_list_str.split(",") if account_list_str else ["mysql"]
            Services.auto_create_job_user(account_list)
