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
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/svr/dbmapi"
)

func testImportTransitEnv() dbmapi.DbmEnvData {
	var env dbmapi.DbmEnvData
	env.CC_MANAGE_TOPO.ResourceModuleId = 100
	env.CC_MANAGE_TOPO.PendingModuleId = 200
	env.CC_MANAGE_TOPO.DirtyModuleId = 300
	return env
}

func TestShouldSkipImportInTransit(t *testing.T) {
	env := testImportTransitEnv()
	recent := time.Now().Add(-2 * time.Hour)
	expired := time.Now().Add(-13 * time.Hour)

	t.Run("recent pending skips", func(t *testing.T) {
		if !shouldSkipImportInTransit(recent, 200, env) {
			t.Fatal("recent import still in pending must skip UsedByOther")
		}
	})
	t.Run("recent dirty skips", func(t *testing.T) {
		if !shouldSkipImportInTransit(recent, 300, env) {
			t.Fatal("recent import still in dirty must skip UsedByOther")
		}
	})
	t.Run("recent other module does not skip", func(t *testing.T) {
		if shouldSkipImportInTransit(recent, 999, env) {
			t.Fatal("recent import in unrelated module must not skip")
		}
	})
	t.Run("expired pending does not skip", func(t *testing.T) {
		if shouldSkipImportInTransit(expired, 200, env) {
			t.Fatal("import older than grace still in pending must not skip")
		}
	})
	t.Run("unconfigured module id does not skip", func(t *testing.T) {
		emptyEnv := dbmapi.DbmEnvData{}
		if shouldSkipImportInTransit(recent, 0, emptyEnv) {
			t.Fatal("pending/dirty id 0 must not be treated as transit")
		}
		if isImportInTransitModule(0, emptyEnv) {
			t.Fatal("module id 0 must not match unconfigured transit modules")
		}
	})
	t.Run("zero create time does not skip", func(t *testing.T) {
		if shouldSkipImportInTransit(time.Time{}, 200, env) {
			t.Fatal("zero create_time must not skip")
		}
	})
}
