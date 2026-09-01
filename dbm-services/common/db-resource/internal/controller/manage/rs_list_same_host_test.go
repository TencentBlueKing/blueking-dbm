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

import (
	"testing"

	"dbm-services/common/db-resource/internal/model"
)

func TestSlicePage(t *testing.T) {
	data := []model.TbRpDetail{
		{BkHostID: 1}, {BkHostID: 2}, {BkHostID: 3}, {BkHostID: 4}, {BkHostID: 5},
	}
	got := slicePage(data, 2, 2)
	if len(got) != 2 || got[0].BkHostID != 3 || got[1].BkHostID != 4 {
		t.Fatalf("unexpected page: %+v", got)
	}
	if len(slicePage(data, 10, 2)) != 0 {
		t.Fatalf("offset beyond len should be empty")
	}
	all := slicePage(data, 0, 0)
	if len(all) != 5 {
		t.Fatalf("limit 0 means no truncate, got %d", len(all))
	}
	// limit<=0 忽略 offset，与非排序 SQL 路径一致
	if len(slicePage(data, 2, 0)) != 5 {
		t.Fatalf("limit 0 should ignore offset")
	}
	if len(slicePage(data, 2, -1)) != 5 {
		t.Fatalf("negative limit should ignore offset")
	}
}

func TestSortDetailsBySameSvrOwnerCount(t *testing.T) {
	data := []model.TbRpDetail{
		{BkHostID: 1, SameSvrOwnerCount: 1},
		{BkHostID: 2, SameSvrOwnerCount: 5},
		{BkHostID: 3, SameSvrOwnerCount: 3},
	}
	sortDetailsBySameSvrOwnerCount(data, "desc")
	if data[0].BkHostID != 2 || data[1].BkHostID != 3 || data[2].BkHostID != 1 {
		t.Fatalf("bad desc order: %+v", data)
	}
	page := slicePage(data, 0, 2)
	if len(page) != 2 || page[0].SameSvrOwnerCount != 5 {
		t.Fatalf("bad paged sort: %+v", page)
	}

	asc := []model.TbRpDetail{
		{BkHostID: 1, SameSvrOwnerCount: 1},
		{BkHostID: 2, SameSvrOwnerCount: 5},
		{BkHostID: 3, SameSvrOwnerCount: 3},
	}
	sortDetailsBySameSvrOwnerCount(asc, "asc")
	if asc[0].BkHostID != 1 || asc[1].BkHostID != 3 || asc[2].BkHostID != 2 {
		t.Fatalf("bad asc order: %+v", asc)
	}
}

func TestParamCheckOrderBy(t *testing.T) {
	ok := MachineResourceGetterInputParam{
		OrderBy: orderBySameSvrOwnerCount,
		Order:   "desc",
		Limit:   20,
	}
	if err := ok.paramCheck(); err != nil {
		t.Fatalf("valid order_by should pass: %v", err)
	}
	badField := MachineResourceGetterInputParam{OrderBy: "create_time", Limit: 20}
	if err := badField.paramCheck(); err == nil {
		t.Fatalf("unsupported order_by should fail")
	}
	orderOnly := MachineResourceGetterInputParam{Order: "asc", Limit: 20}
	if err := orderOnly.paramCheck(); err == nil {
		t.Fatalf("order without order_by should fail")
	}
	noLimit := MachineResourceGetterInputParam{OrderBy: orderBySameSvrOwnerCount, Limit: 0}
	if err := noLimit.paramCheck(); err == nil {
		t.Fatalf("sort without positive limit should fail")
	}
	tooBig := MachineResourceGetterInputParam{
		OrderBy: orderBySameSvrOwnerCount,
		Limit:   maxSameSvrOwnerSortLimit + 1,
	}
	if err := tooBig.paramCheck(); err == nil {
		t.Fatalf("limit over max should fail")
	}
}
