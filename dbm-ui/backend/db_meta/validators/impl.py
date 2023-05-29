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
from validators import *  # pylint: disable=wildcard-import


@validator
def instance(value):
    groups = value.split(":")
    if len(groups) != 2:
        return False

    return (ipv4(groups[0]) or ipv6(groups[0])) and groups[1].isdigit()


@validator
def port(value):
    return isinstance(value, int) and 0 < value < 65535
