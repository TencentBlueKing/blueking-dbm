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

from backend.db_monitor.models import CollectInstance

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument("-f", "--force", dest="force", action="store_true", help="false by default")
        parser.add_argument(
            "-d",
            "--dbtype",
            choices=["mysql", "redis", "es", "hdfs", "kafka", "pulsar", "influxdb", "all"],
            type=str,
            help="db类型",
        )

    def handle(self, *args, **options):
        dbtype = options["dbtype"]

        if options["force"]:
            qs = CollectInstance.objects.all()
            if dbtype:
                qs = qs.filter(db_type=dbtype)
            qs.update(version=0)

        # 加载采集策略
        CollectInstance.sync_collect_strategy()
