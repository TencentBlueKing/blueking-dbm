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

from django.core.management.base import BaseCommand

from backend.core.translation.exceptions import TranslationPathNotFindException
from backend.core.translation.translate import Translater


class Command(BaseCommand):
    help = "This command can automatically translate the po files generated by django"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--pofile", help="file path")
        parser.add_argument("-l", "--language", choices=["zh-CN", "en"], default="en", help="the translate language")

    def handle(self, *args, **options):
        if not options["pofile"]:
            raise TranslationPathNotFindException("Error: please input file path")

        if not os.path.exists(options["pofile"]):
            raise TranslationPathNotFindException("The translation file directory does not exist")

        Translater(file_path=options["pofile"], language=options["language"]).run()
