/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tmysqlver

import (
	"reflect"
	"testing"
)

func TestRebuild(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name string
		in   []string
		want []string
	}{
		{name: "nil", in: nil, want: nil},
		{name: "empty slice", in: []string{}, want: nil},
		{name: "5.5", in: []string{"MySQL-5.5"}, want: []string{"5.5.24"}},
		{name: "5.6", in: []string{"mysql-5.6"}, want: []string{"5.6.24"}},
		{name: "5.7", in: []string{"5.7.20-tmysql"}, want: []string{"5.7.20"}},
		{name: "8.0", in: []string{"MySQL-8.0"}, want: []string{"8.0.18"}},
		{name: "8.4", in: []string{"MySQL-8.4"}, want: []string{"8.4.0"}},
		{name: "8.4 patch", in: []string{"8.4.2"}, want: []string{"8.4.0"}},
		{name: "unknown default empty", in: []string{"unknown"}, want: []string{""}},
		{name: "mixed", in: []string{"8.0", "8.4", "foo"}, want: []string{"8.0.18", "8.4.0", ""}},
	}
	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := Rebuild(tt.in)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("Rebuild(%v) = %#v, want %#v", tt.in, got, tt.want)
			}
		})
	}
}
