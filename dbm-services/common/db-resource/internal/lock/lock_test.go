/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package lock_test

import (
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/lock"
	"dbm-services/common/go-pubpkg/cmutil"
)

func TestRedisLock(t *testing.T) {
	t.Log("start testing...")
	// lock.InitRedisDb()
	l := lock.NewSpinLock(&lock.RedisLock{
		Name:    "Tendb",
		RandKey: cmutil.RandStr(16),
		Expiry:  10 * time.Second,
	}, 30, 1*time.Second)
	for i := 0; i < 20; i++ {
		go func(j int) {
			if err := l.Lock(); err != nil {
				t.Log(j, "lock failed")
				return
			}
			t.Log(j, "lock success")
			time.Sleep(100 * time.Millisecond)
			l.Unlock()
		}(i)
	}

	time.Sleep(20 * time.Second)
}
