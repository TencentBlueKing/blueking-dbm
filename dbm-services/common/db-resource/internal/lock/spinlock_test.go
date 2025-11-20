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
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// MockTryLocker 模拟锁实现，用于测试
type MockTryLocker struct {
	locked         int64         // 使用原子操作
	failAttempts   int           // 前N次尝试会失败
	currentTries   int64         // 当前尝试次数
	unlockDelay    time.Duration // 解锁延迟
	lastLockTime   time.Time     // 最后一次加锁时间
	lastUnlockTime time.Time     // 最后一次解锁时间
}

func NewMockTryLocker(failAttempts int) *MockTryLocker {
	return &MockTryLocker{
		failAttempts: failAttempts,
	}
}

func (m *MockTryLocker) TryLock() error {
	atomic.AddInt64(&m.currentTries, 1)

	// 前N次尝试失败
	if int(atomic.LoadInt64(&m.currentTries)) <= m.failAttempts {
		return fmt.Errorf("mock lock failed, attempt %d", atomic.LoadInt64(&m.currentTries))
	}

	// 尝试获取锁
	if atomic.CompareAndSwapInt64(&m.locked, 0, 1) {
		m.lastLockTime = time.Now()
		return nil
	}

	return fmt.Errorf("lock is already held")
}

func (m *MockTryLocker) Unlock() error {
	if m.unlockDelay > 0 {
		time.Sleep(m.unlockDelay)
	}

	if atomic.CompareAndSwapInt64(&m.locked, 1, 0) {
		m.lastUnlockTime = time.Now()
		return nil
	}

	return fmt.Errorf("lock is not held")
}

func (m *MockTryLocker) IsLocked() bool {
	return atomic.LoadInt64(&m.locked) == 1
}

func (m *MockTryLocker) GetTryCount() int64 {
	return atomic.LoadInt64(&m.currentTries)
}

func (m *MockTryLocker) Reset() {
	atomic.StoreInt64(&m.locked, 0)
	atomic.StoreInt64(&m.currentTries, 0)
}

// TestSpinLockBasicOperation 测试基本操作
func TestSpinLockBasicOperation(t *testing.T) {
	mockLock := NewMockTryLocker(0) // 不失败
	spinLock := NewSpinLock(mockLock, 5, 100*time.Millisecond)

	// 测试获取锁
	err := spinLock.Lock()
	if err != nil {
		t.Fatalf("Expected to acquire lock but failed: %v", err)
	}

	// 检查状态
	if !spinLock.IsLocked() {
		t.Error("Expected lock to be acquired")
	}

	if !mockLock.IsLocked() {
		t.Error("Expected underlying lock to be acquired")
	}

	// 测试释放锁
	err = spinLock.Unlock()
	if err != nil {
		t.Fatalf("Failed to unlock: %v", err)
	}

	// 检查状态
	if spinLock.IsLocked() {
		t.Error("Expected lock to be released")
	}

	if mockLock.IsLocked() {
		t.Error("Expected underlying lock to be released")
	}
}

// TestSpinLockRetryMechanism 测试重试机制
func TestSpinLockRetryMechanism(t *testing.T) {
	failAttempts := 3
	mockLock := NewMockTryLocker(failAttempts)
	spinLock := NewSpinLock(mockLock, 10, 50*time.Millisecond)

	startTime := time.Now()
	err := spinLock.Lock()
	duration := time.Since(startTime)

	if err != nil {
		t.Fatalf("Expected to acquire lock after retries but failed: %v", err)
	}

	// 验证重试次数
	expectedTries := int64(failAttempts + 1)
	if mockLock.GetTryCount() != expectedTries {
		t.Errorf("Expected %d tries, got %d", expectedTries, mockLock.GetTryCount())
	}

	// 验证耗时（应该有重试延迟）
	expectedMinDuration := time.Duration(failAttempts) * 50 * time.Millisecond
	if duration < expectedMinDuration {
		t.Errorf("Expected duration >= %v, got %v", expectedMinDuration, duration)
	}

	t.Logf("Lock acquired after %d attempts in %v", mockLock.GetTryCount(), duration)

	// 清理
	if err := spinLock.Unlock(); err != nil {
		t.Errorf("Failed to unlock: %v", err)
	}
}

// TestSpinLockMaxTriesExceeded 测试超过最大尝试次数
func TestSpinLockMaxTriesExceeded(t *testing.T) {
	maxTries := 3
	mockLock := NewMockTryLocker(10) // 永远失败
	spinLock := NewSpinLock(mockLock, maxTries, 10*time.Millisecond)

	startTime := time.Now()
	err := spinLock.Lock()
	duration := time.Since(startTime)

	if err == nil {
		t.Fatal("Expected lock acquisition to fail after max tries")
	}

	// 验证尝试次数
	if mockLock.GetTryCount() != int64(maxTries) {
		t.Errorf("Expected %d tries, got %d", maxTries, mockLock.GetTryCount())
	}

	// 验证错误信息包含详细信息
	expectedErrorSubstring := fmt.Sprintf("after %d attempts", maxTries)
	if !contains(err.Error(), expectedErrorSubstring) {
		t.Errorf("Expected error to contain '%s', got: %s", expectedErrorSubstring, err.Error())
	}

	t.Logf("Lock acquisition correctly failed after %d attempts in %v: %v", maxTries, duration, err)
}

// TestSpinLockWithContext 测试上下文取消
func TestSpinLockWithContext(t *testing.T) {
	mockLock := NewMockTryLocker(100) // 永远失败
	spinLock := NewSpinLock(mockLock, 50, 100*time.Millisecond)

	// 创建一个会取消的上下文
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	startTime := time.Now()
	err := spinLock.LockWithContext(ctx)
	duration := time.Since(startTime)

	if err == nil {
		t.Fatal("Expected lock acquisition to be cancelled")
	}

	// 验证是因为上下文取消而失败
	if !contains(err.Error(), "cancelled") {
		t.Errorf("Expected error to indicate cancellation, got: %s", err.Error())
	}

	// 验证持续时间合理（应该接近上下文超时时间）
	if duration > 500*time.Millisecond {
		t.Errorf("Lock acquisition took too long: %v", duration)
	}

	t.Logf("Lock acquisition correctly cancelled after %v: %v", duration, err)
}

// TestSpinLockConcurrency 测试并发访问
func TestSpinLockConcurrency(t *testing.T) {
	const numGoroutines = 10
	const lockHoldTime = 50 * time.Millisecond

	mockLock := NewMockTryLocker(0)
	var successCount int64
	var wg sync.WaitGroup

	// 记录执行顺序
	var executionOrder []int
	var orderMutex sync.Mutex

	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			spinLock := NewSpinLock(mockLock, 20, 20*time.Millisecond)

			if lockErr := spinLock.Lock(); lockErr == nil {
				atomic.AddInt64(&successCount, 1)

				// 记录获取锁的顺序
				orderMutex.Lock()
				executionOrder = append(executionOrder, id)
				orderMutex.Unlock()

				// 持有锁一段时间
				time.Sleep(lockHoldTime)

				if unlockErr := spinLock.Unlock(); unlockErr != nil {
					t.Errorf("Goroutine %d failed to unlock: %v", id, unlockErr)
				}
			} else {
				t.Logf("Goroutine %d failed to acquire lock: %v", id, lockErr)
			}
		}(i)
	}

	wg.Wait()

	// 验证只有一个goroutine能同时持有锁
	if successCount != int64(numGoroutines) {
		t.Errorf("Expected all %d goroutines to eventually acquire lock, but only %d succeeded",
			numGoroutines, successCount)
	}

	// 验证执行是串行的
	if len(executionOrder) != numGoroutines {
		t.Errorf("Expected %d executions, got %d", numGoroutines, len(executionOrder))
	}

	t.Logf("All %d goroutines successfully acquired and released lock in order: %v",
		numGoroutines, executionOrder)
}

// TestSpinLockConfigCustomization 测试自定义配置
func TestSpinLockConfigCustomization(t *testing.T) {
	mockLock := NewMockTryLocker(2) // 前2次失败

	config := SpinLockConfig{
		MaxTries:          5,
		BaseInterval:      10 * time.Millisecond,
		MaxInterval:       100 * time.Millisecond,
		BackoffMultiplier: 2.0,
		JitterEnabled:     false, // 关闭抖动以便测试
		EnableProgressLog: true,
		LogInterval:       2,
	}

	spinLock := NewSpinLockWithConfig(mockLock, config)

	startTime := time.Now()
	err := spinLock.Lock()
	duration := time.Since(startTime)

	if err != nil {
		t.Fatalf("Expected to acquire lock but failed: %v", err)
	}

	// 验证配置生效 - 应该在第3次尝试成功
	if mockLock.GetTryCount() != 3 {
		t.Errorf("Expected 3 tries, got %d", mockLock.GetTryCount())
	}

	// 验证指数退避时间
	// 第1次失败后等待10ms，第2次失败后等待20ms，第3次成功
	expectedMinDuration := 10*time.Millisecond + 20*time.Millisecond
	if duration < expectedMinDuration {
		t.Errorf("Expected duration >= %v, got %v", expectedMinDuration, duration)
	}

	t.Logf("Lock acquired with custom config in %v after %d attempts", duration, mockLock.GetTryCount())

	if err := spinLock.Unlock(); err != nil {
		t.Errorf("Failed to unlock: %v", err)
	}
}

// TestSpinLockWrongUnlock 测试错误解锁
func TestSpinLockWrongUnlock(t *testing.T) {
	mockLock := NewMockTryLocker(0)
	spinLock := NewSpinLock(mockLock, 5, 10*time.Millisecond)

	// 尝试解锁未获取的锁
	err := spinLock.Unlock()
	if err == nil {
		t.Error("Expected unlock to fail when lock was not acquired")
	}

	expectedErrorSubstring := "not acquired by this instance"
	if !contains(err.Error(), expectedErrorSubstring) {
		t.Errorf("Expected error to contain '%s', got: %s", expectedErrorSubstring, err.Error())
	}

	t.Logf("Correctly failed to unlock non-acquired lock: %v", err)
}

// TestSpinLockUtilityMethods 测试工具方法
func TestSpinLockUtilityMethods(t *testing.T) {
	mockLock := NewMockTryLocker(2)
	spinLock := NewSpinLock(mockLock, 10, 50*time.Millisecond)

	// 初始状态
	if spinLock.IsLocked() {
		t.Error("Expected lock to be unlocked initially")
	}

	if spinLock.GetAttemptDuration() != 0 {
		t.Error("Expected attempt duration to be 0 initially")
	}

	// 开始尝试获取锁
	go func() {
		time.Sleep(100 * time.Millisecond) // 让主线程检查duration
		if lockErr := spinLock.Lock(); lockErr != nil {
			t.Errorf("Failed to acquire lock in goroutine: %v", lockErr)
		}
	}()

	// 等待一下然后检查duration
	time.Sleep(150 * time.Millisecond)
	duration := spinLock.GetAttemptDuration()

	if duration <= 0 {
		t.Error("Expected positive attempt duration")
	}

	// 等待锁获取完成
	time.Sleep(200 * time.Millisecond)

	if !spinLock.IsLocked() {
		t.Error("Expected lock to be acquired")
	}

	t.Logf("Lock attempt took %v", duration)

	if err := spinLock.Unlock(); err != nil {
		t.Errorf("Failed to unlock: %v", err)
	}
}

// TestDefaultSpinLockConfig 测试默认配置
func TestDefaultSpinLockConfig(t *testing.T) {
	config := DefaultSpinLockConfig()

	// 验证默认值合理性
	if config.MaxTries <= 0 {
		t.Error("Expected positive MaxTries")
	}

	if config.BaseInterval <= 0 {
		t.Error("Expected positive BaseInterval")
	}

	if config.MaxInterval <= config.BaseInterval {
		t.Error("Expected MaxInterval > BaseInterval")
	}

	if config.BackoffMultiplier <= 1.0 {
		t.Error("Expected BackoffMultiplier > 1.0")
	}

	if config.LogInterval <= 0 {
		t.Error("Expected positive LogInterval")
	}

	t.Logf("Default config: MaxTries=%d, BaseInterval=%v, MaxInterval=%v, BackoffMultiplier=%.1f",
		config.MaxTries, config.BaseInterval, config.MaxInterval, config.BackoffMultiplier)
}

// TestSpinLockBackoffStrategy 测试退避策略
func TestSpinLockBackoffStrategy(t *testing.T) {
	config := SpinLockConfig{
		MaxTries:          5,
		BaseInterval:      10 * time.Millisecond,
		MaxInterval:       50 * time.Millisecond,
		BackoffMultiplier: 2.0,
		JitterEnabled:     false,
		EnableProgressLog: false,
		LogInterval:       1,
	}

	spinLock := NewSpinLockWithConfig(nil, config)

	// 测试间隔计算
	testCases := []struct {
		currentInterval time.Duration
		expectedNext    time.Duration
	}{
		{10 * time.Millisecond, 20 * time.Millisecond},
		{20 * time.Millisecond, 40 * time.Millisecond},
		{40 * time.Millisecond, 50 * time.Millisecond}, // 受MaxInterval限制
		{50 * time.Millisecond, 50 * time.Millisecond}, // 已达到最大值
	}

	for _, tc := range testCases {
		next := spinLock.updateInterval(tc.currentInterval)
		if next != tc.expectedNext {
			t.Errorf("For interval %v, expected next %v, got %v",
				tc.currentInterval, tc.expectedNext, next)
		}
	}
}

// 辅助函数
func contains(s, substr string) bool {
	return len(s) >= len(substr) &&
		(s == substr ||
			(len(s) > len(substr) &&
				(s[:len(substr)] == substr ||
					s[len(s)-len(substr):] == substr ||
					containsHelper(s, substr))))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// BenchmarkSpinLock 性能基准测试
func BenchmarkSpinLock(b *testing.B) {
	mockLock := NewMockTryLocker(0)
	spinLock := NewSpinLock(mockLock, 5, 1*time.Millisecond)

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		mockLock.Reset()
		if err := spinLock.Lock(); err != nil {
			b.Fatalf("Failed to acquire lock: %v", err)
		}
		if err := spinLock.Unlock(); err != nil {
			b.Fatalf("Failed to release lock: %v", err)
		}
	}
}
