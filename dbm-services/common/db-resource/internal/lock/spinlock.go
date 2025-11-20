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
	"math/rand"
	"sync/atomic"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// TryLocker trylocker interface
type TryLocker interface {
	TryLock() error
	Unlock() error
}

// SpinLockConfig 自旋锁配置
type SpinLockConfig struct {
	MaxTries          int           // 最大尝试次数
	BaseInterval      time.Duration // 基础重试间隔
	MaxInterval       time.Duration // 最大重试间隔
	BackoffMultiplier float64       // 退避乘数
	JitterEnabled     bool          // 是否启用抖动
	MaxJitter         time.Duration // 最大抖动时间
	EnableProgressLog bool          // 是否启用进度日志
	LogInterval       int           // 日志记录间隔（每N次尝试记录一次）
}

// DefaultSpinLockConfig 默认配置
func DefaultSpinLockConfig() SpinLockConfig {
	return SpinLockConfig{
		MaxTries:          60,
		BaseInterval:      350 * time.Millisecond,
		MaxInterval:       5 * time.Second,
		BackoffMultiplier: 1.5,
		JitterEnabled:     true,
		MaxJitter:         100 * time.Millisecond,
		EnableProgressLog: true,
		LogInterval:       10,
	}
}

// NewSpinLock 创建自旋锁（使用默认配置）
func NewSpinLock(lock TryLocker, spinTries int, spinInterval time.Duration) *SpinLock {
	config := DefaultSpinLockConfig()
	config.MaxTries = spinTries
	config.BaseInterval = spinInterval
	return NewSpinLockWithConfig(lock, config)
}

// NewSpinLockWithConfig 使用自定义配置创建自旋锁
func NewSpinLockWithConfig(lock TryLocker, config SpinLockConfig) *SpinLock {
	return &SpinLock{
		lock:      lock,
		config:    config,
		acquired:  0,
		startTime: 0,
	}
}

// SpinLock 改进的自旋锁实现
type SpinLock struct {
	lock      TryLocker
	config    SpinLockConfig
	acquired  int64 // 原子标记锁是否已获取
	startTime int64 // 开始尝试获取锁的时间戳
}

// Lock 获取锁，支持上下文取消
func (l *SpinLock) Lock() error {
	return l.LockWithContext(context.Background())
}

// LockWithContext 使用上下文获取锁
func (l *SpinLock) LockWithContext(ctx context.Context) error {
	atomic.StoreInt64(&l.startTime, time.Now().UnixNano())

	currentInterval := l.config.BaseInterval
	var lastErr error

	for i := 0; i < l.config.MaxTries; i++ {
		// 检查上下文是否已取消
		select {
		case <-ctx.Done():
			return fmt.Errorf("lock acquisition cancelled: %w", ctx.Err())
		default:
		}

		// 尝试获取锁
		err := l.lock.TryLock()
		if err == nil {
			atomic.StoreInt64(&l.acquired, 1)
			duration := time.Duration(time.Now().UnixNano() - atomic.LoadInt64(&l.startTime))
			logger.Info("successfully acquired lock after %d attempts in %v", i+1, duration)
			return nil
		}
		lastErr = err

		// 记录进度日志
		if l.config.EnableProgressLog && (i+1)%l.config.LogInterval == 0 {
			logger.Warn("lock acquisition attempt %d/%d failed: %s", i+1, l.config.MaxTries, lastErr.Error())
		}

		// 如果还有重试机会，则等待
		if i < l.config.MaxTries-1 {
			sleepDuration := l.calculateSleepDuration(currentInterval, i)

			select {
			case <-ctx.Done():
				return fmt.Errorf("lock acquisition cancelled during sleep: %w", ctx.Err())
			case <-time.After(sleepDuration):
			}

			// 更新下次重试间隔（指数退避）
			currentInterval = l.updateInterval(currentInterval)
		}
	}

	totalDuration := time.Duration(time.Now().UnixNano() - atomic.LoadInt64(&l.startTime))
	return fmt.Errorf("spin lock failed after %d attempts in %v: %w", l.config.MaxTries, totalDuration, lastErr)
}

// calculateSleepDuration 计算睡眠时间，包含抖动
func (l *SpinLock) calculateSleepDuration(baseInterval time.Duration, attempt int) time.Duration {
	if !l.config.JitterEnabled {
		return baseInterval
	}

	// 计算抖动时间
	maxJitter := l.config.MaxJitter
	if maxJitter > baseInterval/2 {
		maxJitter = baseInterval / 2
	}

	jitter := time.Duration(rand.Int63n(int64(maxJitter)))
	return baseInterval + jitter
}

// updateInterval 更新重试间隔（指数退避）
func (l *SpinLock) updateInterval(current time.Duration) time.Duration {
	next := time.Duration(float64(current) * l.config.BackoffMultiplier)
	if next > l.config.MaxInterval {
		return l.config.MaxInterval
	}
	return next
}

// Unlock 释放锁
func (l *SpinLock) Unlock() error {
	if atomic.LoadInt64(&l.acquired) == 0 {
		logger.Warn("attempted to unlock a lock that was not acquired by this SpinLock instance")
		return fmt.Errorf("lock was not acquired by this instance")
	}

	err := l.lock.Unlock()
	if err != nil {
		logger.Error("failed to unlock underlying lock: %s", err.Error())
		return fmt.Errorf("failed to unlock: %w", err)
	}

	atomic.StoreInt64(&l.acquired, 0)
	logger.Info("successfully released lock")
	return nil
}

// IsLocked 检查锁是否已被此实例获取
func (l *SpinLock) IsLocked() bool {
	return atomic.LoadInt64(&l.acquired) == 1
}

// GetAttemptDuration 获取尝试获取锁已用的时间
func (l *SpinLock) GetAttemptDuration() time.Duration {
	startTime := atomic.LoadInt64(&l.startTime)
	if startTime == 0 {
		return 0
	}
	return time.Duration(time.Now().UnixNano() - startTime)
}
