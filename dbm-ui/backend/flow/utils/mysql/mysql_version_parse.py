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
import re


def mysql_version_parse(mysql_version: str) -> int:
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if len(result) == 0:
        return 0

    billion, thousand, single = result[0]

    total = 0

    if billion != "":
        total += int(billion) * 1000000

    if thousand != "":
        total += int(thousand) * 1000

    if single != "":
        total += int(single)

    return total
