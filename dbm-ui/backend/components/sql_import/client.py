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

from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import MYSQL_SIMULATION_DONAIN


class _SQLImportApi(object):

    MODULE = _("SQL语句导入")

    def __init__(self):
        self.grammar_check = DataAPI(
            method="POST",
            base=MYSQL_SIMULATION_DONAIN,
            url="/syntax/check/file",
            module=self.MODULE,
            description=_("sql语法检查"),
        )


class _SQLSimulation(object):

    MODULE = _("SQL模拟执行")

    def __init__(self):
        self.mysql_simulation = DataAPI(
            method="POST",
            base=MYSQL_SIMULATION_DONAIN,
            url="/mysql/simulation",
            module=self.MODULE,
            description=_("容器化SQL模拟执行"),
        )

        self.query_simulation_task = DataAPI(
            method="POST",
            base=MYSQL_SIMULATION_DONAIN,
            url="/mysql/task",
            module=self.MODULE,
            description=_("查询模拟执行任务状态也"),
        )

        self.spider_simulation = DataAPI(
            method="POST",
            base=MYSQL_SIMULATION_DONAIN,
            url="/spider/simulation",
            module=self.MODULE,
            description=_("容器化SQL模拟执行"),
        )


SQLImportApi = _SQLImportApi()
SQLSimulation = _SQLSimulation()
