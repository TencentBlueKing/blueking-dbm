/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import "testing"

func TestGetUpdateMapWritesOsName(t *testing.T) {
	osName := "tlinux-2.6"
	updateMap, err := (UpdateRsMeta{OsName: &osName}).getUpdateMap()
	if err != nil {
		t.Fatalf("getUpdateMap: %v", err)
	}
	got, ok := updateMap["os_name"]
	if !ok {
		t.Fatal("os_name missing from update map")
	}
	if got != osName {
		t.Fatalf("os_name = %v, want %s", got, osName)
	}
	if _, ok := updateMap["os_version"]; ok {
		t.Fatal("os_version should not be written")
	}
}

func TestGetUpdateMapWritesEmptyOsName(t *testing.T) {
	osName := ""
	updateMap, err := (UpdateRsMeta{OsName: &osName}).getUpdateMap()
	if err != nil {
		t.Fatalf("getUpdateMap: %v", err)
	}
	got, ok := updateMap["os_name"]
	if !ok {
		t.Fatal("empty os_name should still be written")
	}
	if got != "" {
		t.Fatalf("os_name = %v, want empty string", got)
	}
}

func TestGetUpdateMapOmitsOsNameWhenNil(t *testing.T) {
	updateMap, err := (UpdateRsMeta{}).getUpdateMap()
	if err != nil {
		t.Fatalf("getUpdateMap: %v", err)
	}
	if _, ok := updateMap["os_name"]; ok {
		t.Fatal("nil os_name should not be written")
	}
}
