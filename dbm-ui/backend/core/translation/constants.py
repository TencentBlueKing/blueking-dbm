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

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 寻找未翻译语言时，忽略方法名
IGNORED_METHOD_LIST = [
    "print",
    "log",
    "critical",
    "exception",
    "fatal",
    "warning",
    "get_type_env",
]

# 寻找未翻译语言时，忽略目录的路径
EXCLUDE_DIRS = [
    "backend/core/translation",
    "backend/dbm_init",
    "backend/locale",
    "backend/settings",
    "backend/env",
    "backend/tests",
    "backend/db_monitor/management",
    "backend/db_event/management",
    "backend/flow/utils/cloud/script_template",
    "dbm-ui/backend/db_services/report/mock_data",
]
# 寻找未翻译语言时，忽略的文件路径
EXCLUDE_FILE_PATHS = [
    # 因为permission/constants.py下存在常量恒为中文的excel头，暂时不处理
    "backend/db_services/mysql/permission/constants.py",
    "backend/flow/utils/cloud/cloud_script_template.py",
    # 忽略权限模型json初始化的中文
    "backend/iam_app/dataclass/__init__.py",
]
ALL_EXCLUDE_DIRS = set(EXCLUDE_DIRS + EXCLUDE_FILE_PATHS)

# 寻找未翻译语言时，忽略特定文件下的特定语言
EXCLUDE_LANGUAGES_IN_FILE = {}


class Language(str, StructuredEnum):
    ZH_CN = EnumField("zh-cn", "ZH-CN")
    EN = EnumField("en", "EN")


# 不同语言的正则匹配模式
LANGUAGE_REGEX_MAP = {Language.ZH_CN.value: r"[\u4e00-\u9fff]", Language.EN.value: r"[a-zA-Z]"}


class LanguageFindMode(str, StructuredEnum):
    VISIT = EnumField("visit", "VISIT")
    AST_ALTER = EnumField("alter", "ALTER")
    SIMPLE_ALTER = EnumField("simple_alter", "SIMPLE_ALTER")
    ERROR = EnumField("error", "ERROR")
