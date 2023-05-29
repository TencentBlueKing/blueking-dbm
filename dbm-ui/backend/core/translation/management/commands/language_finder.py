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
from backend.core.translation.language_finder import LanguageFinder


class Command(BaseCommand):
    help = "This command can find untranslated text in the specified directory and also can find the formatted strings"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--path", help="[file|file path] to handle", type=str)
        parser.add_argument("-s", "--suffix", help="file suffix to handle", default=".py", type=str)
        parser.add_argument(
            "-e",
            "--exclude",
            nargs="*",
            help="exclude dir path or file path, default is [migrations, "
            "tests, venv, webpack, translate, conf, config]. If too "
            "many file names or folders need to be excluded, "
            "create an exclude_file_or_dir_path.py file in the same "
            "directory as the find_ch.py file, "
            "declare a variable ALL_EXCLUDE_DIRS in the file, "
            "and save the parameter",
            type=str,
        )
        parser.add_argument("-i", "--ignored", nargs="*", help="ignored chinese string", type=list)
        parser.add_argument(
            "-l", "--language", choices=["zh-cn", "en"], default="zh-cn", help="the translate language"
        )
        parser.add_argument(
            "-m",
            "--mode",
            choices=["visit", "ast_alter", "simple_alter", "error"],
            default="visit",
            help="visit----Just found code snippets for untranslated languages\n"
            "ast_alter----Automatically add translation functions for code snippets in untranslated languages\n"
            "warning: Using ast_alter mode will lead to changes in source code structure, "
            "including but not limited to: comments, judgment conditions and etc"
            "simple_alter----Use string function to add translation function "
            "according to the result of untranslated languages"
            "error----Throws an exception if there is an untranslated code fragment or if "
            "there is a language-specific fstrig",
            type=str,
        )

    def handle(self, *args, **options):
        if not options.get("path"):
            raise TranslationPathNotFindException("The translation file directory is not filled")

        if os.path.exists(options["path"]):
            if not options["suffix"].startswith("."):
                options["suffix"] = f".{options['suffix']}"

            finder = LanguageFinder(
                path=options["path"],
                suffix=options["suffix"],
                exclude_dir_or_file_list=options["exclude"],
                ignored_string=options["ignored"],
                translate_language=options["language"],
                mode=options["mode"],
            )
            finder.run()
        else:
            raise TranslationPathNotFindException("The translation file directory does not exist")
