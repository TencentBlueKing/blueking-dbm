// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"strings"
	"testing"
)

type logEntry struct {
	level string
	msg   string
}

func assertNodeLogWidths(t *testing.T, entries []logEntry) {
	t.Helper()
	for _, e := range entries {
		for i, line := range strings.Split(e.msg, "\n") {
			width := lineWidth
			if i == 0 {
				width = headWidth
			}
			if n := len([]rune(line)); n > width {
				t.Fatalf("line %d is %d wide, over %d:\n%s", i, n, width, e.msg)
			}
		}
	}
}

func TestWrapRecordBreaksAtSpacesAndCutsLongWords(t *testing.T) {
	got := wrapRecord("[30000] failed: restore rocksdb from /data1/recover_redis/30000/backup failed: " +
		strings.Repeat("x", 100) + "\nshort\n" + strings.Repeat("y ", 50))
	assertNodeLogWidths(t, []logEntry{{levelInfo, got}})
	lines := strings.Split(got, "\n")
	if lines[0] != "[30000] failed: restore rocksdb from" || !strings.HasPrefix(lines[1], wrapIndent+"/data1/") {
		t.Fatalf("got:\n%s", got)
	}
	if !strings.Contains(got, "\nshort\n") || strings.Count(got, "x") != 100 {
		t.Fatalf("lost text:\n%s", got)
	}
}
