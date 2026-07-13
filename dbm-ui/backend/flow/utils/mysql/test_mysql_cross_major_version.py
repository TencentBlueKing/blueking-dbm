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
from django.test import SimpleTestCase

from backend.flow.utils.mysql.mysql_version_parse import module_version_parse, mysql_cross_major_version


class TestMysqlCrossMajorVersion(SimpleTestCase):
    """mysql_cross_major_version：目标须更高且最多跨 1 个主版本"""

    def test_upgrade_adjacent_major_allowed(self):
        # 5.6 -> 5.7、5.7 -> 8.0 允许
        self.assertTrue(
            mysql_cross_major_version(module_version_parse("MySQL-5.7"), module_version_parse("MySQL-5.6"))
        )
        self.assertTrue(
            mysql_cross_major_version(module_version_parse("MySQL-8.0-Community"), module_version_parse("MySQL-5.7"))
        )

    def test_downgrade_rejected(self):
        # 8.0 -> 5.7 / 5.7 -> 5.6 禁止（本次线上问题）
        self.assertFalse(
            mysql_cross_major_version(module_version_parse("MySQL-5.7"), module_version_parse("MySQL-8.0-Community"))
        )
        self.assertFalse(
            mysql_cross_major_version(module_version_parse("MySQL-5.6"), module_version_parse("MySQL-5.7"))
        )

    def test_skip_major_and_same_rejected(self):
        # 5.6 直接跳 8.0、同主版本均不允许
        self.assertFalse(
            mysql_cross_major_version(module_version_parse("MySQL-8.0-Community"), module_version_parse("MySQL-5.6"))
        )
        self.assertFalse(
            mysql_cross_major_version(module_version_parse("MySQL-8.0-Community"), module_version_parse("MySQL-8.0"))
        )
