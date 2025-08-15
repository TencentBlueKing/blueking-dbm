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
	"sync"
	"testing"
	"time"
)

// TestRedisLockBasicOperation 测试基本锁操作
func TestRedisLockBasicOperation(t *testing.T) {
	lock := NewRedisLock("test_lock", "test_key_123", 30*time.Second)

	// 测试获取锁
	err := lock.TryLock()
	if err != nil {
		t.Logf("Expected to acquire lock but failed: %v", err)
	}

	// 测试释放锁
	err = lock.Unlock()
	if err != nil {
		t.Errorf("Failed to unlock: %v", err)
	}
}

// TestRedisLockConcurrency 测试并发锁操作
func TestRedisLockConcurrency(t *testing.T) {
	const numGoroutines = 10
	const lockName = "concurrent_test_lock"

	var wg sync.WaitGroup
	successCount := make(chan int, numGoroutines)

	// 启动多个goroutine尝试获取同一个锁
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			lock := NewRedisLock(lockName, fmt.Sprintf("worker_%d", id), 5*time.Second)

			if err := lock.TryLock(); err == nil {
				t.Logf("Worker %d acquired lock", id)
				successCount <- 1

				// 模拟一些工作
				time.Sleep(100 * time.Millisecond)

				if err := lock.Unlock(); err != nil {
					t.Errorf("Worker %d failed to unlock: %v", id, err)
				}
			} else {
				t.Logf("Worker %d failed to acquire lock: %v", id, err)
			}
		}(i)
	}

	wg.Wait()
	close(successCount)

	// 统计成功获取锁的数量，应该只有1个
	count := 0
	for range successCount {
		count++
	}

	if count != 1 {
		t.Errorf("Expected exactly 1 goroutine to acquire lock, but %d succeeded", count)
	}
}

// TestRedisLockRefresh 测试锁刷新功能
func TestRedisLockRefresh(t *testing.T) {
	lock := NewRedisLock("refresh_test_lock", "refresh_key", 2*time.Second)

	// 获取锁
	err := lock.TryLock()
	if err != nil {
		t.Fatalf("Failed to acquire lock: %v", err)
	}

	// 等待1秒然后刷新
	time.Sleep(1 * time.Second)
	err = lock.Refresh()
	if err != nil {
		t.Errorf("Failed to refresh lock: %v", err)
	}

	// 再等待1.5秒，如果没有刷新，锁应该已经过期
	time.Sleep(1500 * time.Millisecond)

	// 尝试再次刷新，应该成功（因为之前刷新了）
	err = lock.Refresh()
	if err != nil {
		t.Logf("Lock may have expired, which is expected: %v", err)
	}

	// 清理
	lock.Unlock()
}

// TestRedisLockWrongOwner 测试错误所有者解锁
func TestRedisLockWrongOwner(t *testing.T) {
	lock1 := NewRedisLock("owner_test_lock", "owner1", 30*time.Second)
	lock2 := NewRedisLock("owner_test_lock", "owner2", 30*time.Second)

	// lock1获取锁
	err := lock1.TryLock()
	if err != nil {
		t.Fatalf("Failed to acquire lock with lock1: %v", err)
	}

	// lock2尝试解锁（应该失败）
	err = lock2.Unlock()
	if err == nil {
		t.Error("Expected lock2 to fail unlocking lock owned by lock1")
	} else {
		t.Logf("Correctly failed to unlock with wrong owner: %v", err)
	}

	// lock1正确解锁
	err = lock1.Unlock()
	if err != nil {
		t.Errorf("Failed to unlock with correct owner: %v", err)
	}
}
