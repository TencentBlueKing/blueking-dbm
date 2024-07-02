/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package lock

import (
	"fmt"
	"math/rand"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// TryLocker trylocker
type TryLocker interface {
	TryLock() error
	Unlock() error
}

// NewSpinLock 自旋锁
func NewSpinLock(lock TryLocker, spinTries int, spinInterval time.Duration) *SpinLock {
	return &SpinLock{
		lock:         lock,
		spinTries:    spinTries,
		spinInterval: spinInterval,
	}
}

// SpinLock define spinlock
type SpinLock struct {
	lock         TryLocker
	spinTries    int
	spinInterval time.Duration
}

// Lock do lock
func (l *SpinLock) Lock() (err error) {
	for i := 0; i < l.spinTries; i++ {
		if err = l.lock.TryLock(); err == nil {
			return nil
		}
		logger.Warn("%d: lock %s failed %s", i, err.Error())
		time.Sleep(l.spinInterval)
		time.Sleep(time.Duration(rand.Intn(1000)) * time.Millisecond)
	}
	return fmt.Errorf("spin lock failed:%s  ,after %f seconds", err.Error(), float64(l.spinTries)*l.spinInterval.Seconds())
}

// Unlock do unlock
func (l *SpinLock) Unlock() error {
	return l.lock.Unlock()
}
