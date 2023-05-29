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
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from backend.core.storages.storage import get_storage
from backend.dbm_init.medium.handlers import MediumHandler

logger = logging.getLogger("root")

BKREPO_TMP_DIR = os.path.join(settings.BASE_DIR, "backend/dbm_init/tmp")


class Command(BaseCommand):
    help = "导出制品库文件到本地"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--path", help="目录名")
        parser.add_argument("-o", "--option", help="解压", choices=["unzip", "download", "all"], default="all")

    def handle(self, *args, **options):
        path = options["path"]
        option = options["option"]
        storage = get_storage()
        # 以dbm_init为根目录进行操作
        MediumHandler(storage).download_medium(option, path, BKREPO_TMP_DIR)
