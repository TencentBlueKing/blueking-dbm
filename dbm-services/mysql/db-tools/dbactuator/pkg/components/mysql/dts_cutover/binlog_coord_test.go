/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseBinlogCoordWithParentheses(t *testing.T) {
	coord, ok := ParseBinlogCoord("(binlog20000.002894, 12105)")
	require.True(t, ok)
	require.Equal(t, "binlog20000.002894", coord.File)
	require.Equal(t, int64(12105), coord.Position)
}

func TestParseBinlogCoordWithoutParentheses(t *testing.T) {
	coord, ok := ParseBinlogCoord("binlog20000.002894, 11184")
	require.True(t, ok)
	require.Equal(t, "binlog20000.002894", coord.File)
	require.Equal(t, int64(11184), coord.Position)
}

func TestParseBinlogCoordMalformed(t *testing.T) {
	cases := []string{"", "binlog20000.002894", "(binlog20000.002894, abc)", "(, 12105)", "  "}
	for _, raw := range cases {
		_, ok := ParseBinlogCoord(raw)
		require.False(t, ok, "raw=%q", raw)
	}
}

func TestCompareBinlogCoord(t *testing.T) {
	a, _ := ParseBinlogCoord("(binlog.000001, 100)")
	b, _ := ParseBinlogCoord("(binlog.000001, 90)")
	require.Equal(t, 1, CompareBinlogCoord(a, b))
	require.Equal(t, -1, CompareBinlogCoord(b, a))
	require.Equal(t, 0, CompareBinlogCoord(a, a))

	newer, _ := ParseBinlogCoord("(binlog.000002, 10)")
	older, _ := ParseBinlogCoord("(binlog.000001, 99999)")
	require.Equal(t, 1, CompareBinlogCoord(newer, older))
}

func TestIsCaughtUpToSnapshot(t *testing.T) {
	snapEqual, _ := ParseBinlogCoord("(binlog.000001, 100)")
	require.True(t, IsCaughtUpToSnapshot("(binlog.000001, 100)", snapEqual, 0))

	// syncer 追上并超过加锁快照 → 允许
	snap90, _ := ParseBinlogCoord("(binlog.000001, 90)")
	require.True(t, IsCaughtUpToSnapshot("(binlog.000001, 100)", snap90, 0))

	// syncer file 超过快照 → 允许
	snapOldFile, _ := ParseBinlogCoord("(binlog.000001, 10)")
	require.True(t, IsCaughtUpToSnapshot("(binlog.000002, 10)", snapOldFile, 0))

	// syncer 仍落后于加锁快照 → 拒绝
	snap100, _ := ParseBinlogCoord("(binlog.000001, 100)")
	require.False(t, IsCaughtUpToSnapshot("(binlog.000001, 90)", snap100, 0))
	snapNewFile, _ := ParseBinlogCoord("(binlog.000002, 10)")
	require.False(t, IsCaughtUpToSnapshot("(binlog.000001, 10)", snapNewFile, 0))

	// SBM != 0
	require.False(t, IsCaughtUpToSnapshot("(binlog.000001, 100)", snapEqual, 1))

	// 非法串
	require.False(t, IsCaughtUpToSnapshot("", snapEqual, 0))
	require.False(t, IsCaughtUpToSnapshot("bad", snapEqual, 0))
}
