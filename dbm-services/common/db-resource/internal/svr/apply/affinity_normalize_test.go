/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package apply

import (
	"strings"
	"testing"
)

func TestNormalizeAffinity(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"None", NONE},
		{"none", NONE},
		{"NONE", NONE},
		{"", NONE},
		{"  ", NONE},
		{"cros_subzone", CROS_SUBZONE},
		{"  Cross_Rack  ", CROSS_RACK},
	}
	for _, tc := range cases {
		if got := NormalizeAffinity(tc.in); got != tc.want {
			t.Errorf("NormalizeAffinity(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestParamCheckNormalizesAffinityInPlace(t *testing.T) {
	param := &RequestInputParam{
		Details: []ObjectDetail{
			{Count: 1, Affinity: "None", GroupMark: "0_new_slave_0"},
		},
	}
	if err := param.ParamCheck(); err != nil {
		t.Fatalf("ParamCheck: %v", err)
	}
	if param.Details[0].Affinity != NONE {
		t.Errorf("affinity 应为 %s, 实际 %s", NONE, param.Details[0].Affinity)
	}
}

func TestParamCheckNONEDoesNotSkipLaterDetails(t *testing.T) {
	param := &RequestInputParam{
		Details: []ObjectDetail{
			{Count: 2, Affinity: "None", GroupMark: "none_group"},
			{Count: 2, Affinity: CROS_SUBZONE, GroupMark: "cross_group"},
		},
	}
	err := param.ParamCheck()
	if err == nil {
		t.Fatal("后面 CROS_SUBZONE 分组缺城市时应失败，不能被前面的 NONE 短路")
	}
	if !strings.Contains(err.Error(), "you need choose a city") {
		t.Fatalf("unexpected error: %v", err)
	}
}
