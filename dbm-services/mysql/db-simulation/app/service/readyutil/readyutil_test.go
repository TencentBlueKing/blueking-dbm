/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package readyutil

import (
	"errors"
	"testing"
)

func TestClusterNodeProbePorts(t *testing.T) {
	t.Parallel()

	t.Run("one spider includes backend", func(t *testing.T) {
		t.Parallel()
		got := ClusterNodeProbePorts(1)
		want := []int{25000, 20000}
		assertIntSliceEqual(t, got, want)
	})

	t.Run("two spiders", func(t *testing.T) {
		t.Parallel()
		got := ClusterNodeProbePorts(2)
		want := []int{25000, 25001, 20000}
		assertIntSliceEqual(t, got, want)
	})

	t.Run("empty spiders still probes backend", func(t *testing.T) {
		t.Parallel()
		got := ClusterNodeProbePorts(0)
		want := []int{20000}
		assertIntSliceEqual(t, got, want)
	})
}

func TestIsRetryableCreateNodeError(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		err  error
		want bool
	}{
		{name: "nil", err: nil, want: false},
		{
			name: "12034",
			err:  errors.New("Error 12034: CREATE NODE FAILED: Failed to connect to new server SPIDER_new_127.0.0.1#25000 when checking auto-increment settings"),
			want: true,
		},
		{
			name: "failed to connect substring",
			err:  errors.New("CREATE NODE FAILED: Failed to connect to new server SPIDER_new_127.0.0.1#25000"),
			want: true,
		},
		{
			name: "auto-increment substring",
			err:  errors.New("when checking auto-increment settings"),
			want: true,
		},
		{
			name: "access denied",
			err:  errors.New("Error 1045: Access denied for user 'root'@'127.0.0.1'"),
			want: false,
		},
		{
			name: "sql syntax",
			err:  errors.New("Error 1064: You have an error in your SQL syntax"),
			want: false,
		},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := IsRetryableCreateNodeError(tc.err); got != tc.want {
				t.Fatalf("IsRetryableCreateNodeError(%v)=%v want %v", tc.err, got, tc.want)
			}
		})
	}
}

func TestIsCreateNodeSQL(t *testing.T) {
	t.Parallel()
	if !IsCreateNodeSQL("tdbctl create node wrapper 'SPIDER' options(user 'root', password 'x', host '127.0.0.1', port 25000);") {
		t.Fatal("expected create node sql to match")
	}
	if IsCreateNodeSQL("tdbctl flush routing;") {
		t.Fatal("flush routing must not be treated as create node")
	}
	if IsCreateNodeSQL("tdbctl enable primary;") {
		t.Fatal("enable primary must not be treated as create node")
	}
}

func TestBuildCreateClusterStmts(t *testing.T) {
	t.Parallel()

	got := BuildCreateClusterStmts(2)
	want := []CreateClusterStmt{
		{Kind: KindCreateNode, Wrapper: WrapperSpider, Port: 25000},
		{Kind: KindCreateNode, Wrapper: WrapperSpider, Port: 25001},
		{Kind: KindCreateNode, Wrapper: WrapperMysql, Port: BackendSimPort},
		{Kind: KindCreateNode, Wrapper: WrapperTdbctl, Port: TdbctlSimPort},
		{Kind: KindEnablePrimary},
		{Kind: KindFlushRouting},
	}
	if len(got) != len(want) {
		t.Fatalf("len=%d want %d, got=%+v", len(got), len(want), got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("stmt[%d]=%+v want %+v", i, got[i], want[i])
		}
	}
}

func TestSanitizeCreateNodeWrapper(t *testing.T) {
	t.Parallel()

	for _, wrapper := range []string{WrapperSpider, WrapperMysql, WrapperTdbctl} {
		got, err := SanitizeCreateNodeWrapper(wrapper)
		if err != nil {
			t.Fatalf("SanitizeCreateNodeWrapper(%q) err=%v", wrapper, err)
		}
		if got != wrapper {
			t.Fatalf("SanitizeCreateNodeWrapper(%q)=%q", wrapper, got)
		}
	}
	if _, err := SanitizeCreateNodeWrapper("SPIDER'; drop table t; --"); err == nil {
		t.Fatal("expected injected wrapper to be rejected")
	}
}

func assertIntSliceEqual(t *testing.T, got, want []int) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("len=%d want %d, got=%v want=%v", len(got), len(want), got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got=%v want=%v", got, want)
		}
	}
}
