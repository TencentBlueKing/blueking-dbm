/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil_test

import (
	"testing"

	"dbm-services/common/go-pubpkg/cmutil"
)

func TestSplitGroup(t *testing.T) {
	t.Log("start testing ...")
	ars := []int{1, 2, 3, 4, 6}
	t.Log(cmutil.SplitGroup(ars, 10))
}

func TestStringsRemoveEmpty(t *testing.T) {
	t.Log("start testing ...")
	t.Log(cmutil.StringsRemoveEmpty([]string{"", "33", "foo", "", " "}))
}

func TestRemoveDuplicate(t *testing.T) {
	t.Log("start testing ...")
	t.Log(cmutil.RemoveDuplicate([]string{"33", "foo", "foo", "55", "55"}))
}

func TestFilterOutStringSlice(t *testing.T) {
	t.Log("start testing ...")
	t.Log(cmutil.FilterOutStringSlice([]string{"33", "foo", "foo", "55", "55"}, []string{"55"}))
}
