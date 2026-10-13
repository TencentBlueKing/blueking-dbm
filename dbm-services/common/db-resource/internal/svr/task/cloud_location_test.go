/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package task

import (
	"reflect"
	"testing"

	"dbm-services/common/go-pubpkg/cc.v3"
)

func TestCloudLocationUpdatesSkipsEmpty(t *testing.T) {
	got := cloudLocationUpdates(&cc.Host{
		BkCloudRegion: "ap-example",
		BkCloudZone:   "",
		BkCloudInstID: "ins-example",
	})
	want := map[string]interface{}{
		"bk_cloud_region":  "ap-example",
		"bk_cloud_inst_id": "ins-example",
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %#v want %#v", got, want)
	}
}
