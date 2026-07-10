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

from backend.components.mysqldtsapi.types import SyncStatus, compare_dts_binlog_coord, parse_dts_binlog_coord


class ParseDtsBinlogCoordTest(SimpleTestCase):
    def test_parse_with_parentheses(self):
        coord = parse_dts_binlog_coord("(binlog20000.002894, 12105)")
        self.assertIsNotNone(coord)
        self.assertEqual(coord.file, "binlog20000.002894")
        self.assertEqual(coord.position, 12105)

    def test_parse_without_parentheses(self):
        coord = parse_dts_binlog_coord("binlog20000.002894, 11184")
        self.assertIsNotNone(coord)
        self.assertEqual(coord.file, "binlog20000.002894")
        self.assertEqual(coord.position, 11184)

    def test_parse_empty_or_malformed(self):
        self.assertIsNone(parse_dts_binlog_coord(""))
        self.assertIsNone(parse_dts_binlog_coord(None))
        self.assertIsNone(parse_dts_binlog_coord("binlog20000.002894"))
        self.assertIsNone(parse_dts_binlog_coord("(binlog20000.002894, abc)"))
        self.assertIsNone(parse_dts_binlog_coord("(, 12105)"))


class SyncStatusCatchupTest(SimpleTestCase):
    def _status(self, *, sbm=0, master="(binlog.000001, 100)", syncer="(binlog.000001, 90)"):
        return SyncStatus(
            seconds_behind_master=sbm,
            master_binlog=master,
            syncer_binlog=syncer,
        )

    def test_poll_caught_up_master_ahead_ok(self):
        # 部分同步：同 file 下 master pos 超前仍可进入校验窗口
        st = self._status(sbm=0, master="(binlog.000001, 100)", syncer="(binlog.000001, 90)")
        self.assertTrue(st.is_same_binlog_file())
        self.assertTrue(st.is_poll_caught_up())

    def test_poll_caught_up_when_master_file_ahead(self):
        st = self._status(sbm=0, master="(binlog.000002, 10)", syncer="(binlog.000001, 10)")
        self.assertFalse(st.is_same_binlog_file())
        self.assertTrue(st.is_poll_caught_up())

    def test_reject_when_syncer_ahead(self):
        st = self._status(sbm=0, master="(binlog.000001, 90)", syncer="(binlog.000001, 100)")
        self.assertFalse(st.is_poll_caught_up())

    def test_poll_caught_up_equal_ok(self):
        st = self._status(sbm=0, master="(binlog.000001, 100)", syncer="(binlog.000001, 100)")
        self.assertTrue(st.is_poll_caught_up())

    def test_poll_fails_when_sbm_nonzero(self):
        st = self._status(sbm=1, master="(binlog.000001, 100)", syncer="(binlog.000001, 100)")
        self.assertFalse(st.is_poll_caught_up())

    def test_compare_coords(self):
        a = parse_dts_binlog_coord("(binlog.000001, 100)")
        b = parse_dts_binlog_coord("(binlog.000001, 90)")
        self.assertEqual(compare_dts_binlog_coord(a, b), 1)
        self.assertEqual(compare_dts_binlog_coord(b, a), -1)
