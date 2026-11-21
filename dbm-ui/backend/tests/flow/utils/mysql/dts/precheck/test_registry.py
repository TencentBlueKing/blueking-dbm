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

from unittest import TestCase
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured

from backend.flow.utils.mysql.dts.precheck import items  # noqa: F401
from backend.flow.utils.mysql.dts.precheck.base import _REGISTRY, all_items, register


class RegistryTest(TestCase):
    def test_builtin_codes_are_unique(self):
        codes = [item.code for item in all_items()]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertIn("version", codes)
        self.assertIn("advanced_objects", codes)
        self.assertIn("target_schema", codes)
        self.assertIn("binlog", codes)
        self.assertIn("charset_collation", codes)
        self.assertIn("instance_vars", codes)
        self.assertIn("warnings", codes)

    def test_duplicate_registration_fails(self):
        code = f"test_{uuid4().hex}"

        @register(code, "test")
        def first(_ctx):
            return []

        try:
            with self.assertRaises(ImproperlyConfigured):

                @register(code, "duplicate")
                def second(_ctx):
                    return []

        finally:
            _REGISTRY.pop(code, None)
