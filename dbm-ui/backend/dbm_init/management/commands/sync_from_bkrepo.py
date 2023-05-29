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
from datetime import datetime

from django.core.management.base import BaseCommand

from backend.configuration.constants import DBType
from backend.core.storages.storage import get_storage
from backend.db_package.models import Package

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "从制品库提取介质到本地数据库"

    def add_arguments(self, parser):
        parser.add_argument("-t", "--type", required=True, choices=DBType.get_values(), help="db类型")

    def handle(self, *args, **options):
        db_type = options["type"]
        storage = get_storage()

        for pkg_type in storage.listdir(f"/{db_type}")[0]:
            for version in storage.listdir(pkg_type["fullPath"])[0]:
                for media in storage.listdir(version["fullPath"])[1]:
                    create_at = datetime.strptime(media["createdDate"], "%Y-%m-%dT%H:%M:%S.%f")
                    logger.info(
                        "{}\t{}\t{}\t{}\t{}\t{}\t".format(
                            media["name"],
                            media["fullPath"],
                            media["path"],
                            media["size"],
                            media["md5"],
                            create_at,
                        )
                    )
                    Package.objects.update_or_create(
                        defaults={
                            "path": media["fullPath"],
                            "size": media["size"],
                            "md5": media["md5"],
                            "create_at": create_at,
                        },
                        db_type=db_type,
                        pkg_type=pkg_type["name"],
                        version=version["name"],
                        name=media["name"],
                    )
