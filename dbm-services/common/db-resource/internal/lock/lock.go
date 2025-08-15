/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package lock resource
package lock

import (
	"context"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-redis/redis/v8"
)

var (
	rdb     *redis.Client
	rdbOnce sync.Once
)

// GetRedisClient 获取Redis客户端，使用单例模式确保线程安全
func GetRedisClient() *redis.Client {
	rdbOnce.Do(func() {
		logger.Info("initializing redis client, addr: %s", config.AppConfig.Redis.Addr)
		rdb = redis.NewClient(&redis.Options{
			Addr:         config.AppConfig.Redis.Addr,
			Password:     config.AppConfig.Redis.Password,
			DB:           0,
			PoolSize:     10,
			MinIdleConns: 5,
			DialTimeout:  5 * time.Second,
			ReadTimeout:  3 * time.Second,
			WriteTimeout: 3 * time.Second,
			IdleTimeout:  5 * time.Minute,
		})

		// 测试连接
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := rdb.Ping(ctx).Err(); err != nil {
			logger.Error("failed to connect to redis: %s", err.Error())
		} else {
			logger.Info("redis connection established successfully")
		}
	})
	return rdb
}

// RedisLock redis lock with timeout context support
type RedisLock struct {
	Name    string
	RandKey string
	Expiry  time.Duration
	ctx     context.Context
	cancel  context.CancelFunc
}

// NewRedisLock 创建新的Redis锁实例
func NewRedisLock(name, randKey string, expiry time.Duration) *RedisLock {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	return &RedisLock{
		Name:    name,
		RandKey: randKey,
		Expiry:  expiry,
		ctx:     ctx,
		cancel:  cancel,
	}
}

// TryLock try to lock with proper context and error handling
func (r *RedisLock) TryLock() error {
	if r.ctx == nil {
		return fmt.Errorf("lock context is nil, use NewRedisLock to create instance")
	}

	client := GetRedisClient()
	if client == nil {
		return fmt.Errorf("redis client is not initialized")
	}

	// 使用带超时的上下文
	ctx, cancel := context.WithTimeout(r.ctx, 5*time.Second)
	defer cancel()

	ok, err := client.SetNX(ctx, r.Name, r.RandKey, r.Expiry).Result()
	if err != nil {
		logger.Error("redis setnx failed for key %s: %s", r.Name, err.Error())
		return fmt.Errorf("redis setnx operation failed: %w", err)
	}

	if !ok {
		return fmt.Errorf("lock %s is already held by another process", r.Name)
	}

	logger.Debug("successfully acquired lock: %s", r.Name)
	return nil
}

// Unlock unlock with proper context and atomic operation
func (r *RedisLock) Unlock() error {
	if r.cancel != nil {
		defer r.cancel() // 确保context被取消
	}

	client := GetRedisClient()
	if client == nil {
		return fmt.Errorf("redis client is not initialized")
	}

	// 使用原子的Lua脚本确保只有锁的持有者才能解锁
	luaScript := `
		local key = KEYS[1]
		local expected_value = ARGV[1]
		local current_value = redis.call('GET', key)
		
		if current_value == false then
			return 0  -- 锁不存在
		end
		
		if current_value == expected_value then
			return redis.call('DEL', key)  -- 删除锁
		else
			return -1  -- 锁被其他进程持有
		end
	`

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := client.Eval(ctx, luaScript, []string{r.Name}, r.RandKey).Int()
	if err != nil {
		logger.Error("redis eval failed for unlock key %s: %s", r.Name, err.Error())
		return fmt.Errorf("redis unlock operation failed: %w", err)
	}

	switch result {
	case 0:
		logger.Warn("attempted to unlock non-existent lock: %s", r.Name)
		return fmt.Errorf("lock %s does not exist", r.Name)
	case 1:
		logger.Debug("successfully released lock: %s", r.Name)
		return nil
	case -1:
		logger.Error("attempted to unlock lock held by another process: %s", r.Name)
		return fmt.Errorf("lock %s is held by another process", r.Name)
	default:
		return fmt.Errorf("unexpected unlock result: %d for lock %s", result, r.Name)
	}
}

// Refresh 刷新锁的过期时间（可选功能，用于长时间运行的任务）
func (r *RedisLock) Refresh() error {
	client := GetRedisClient()
	if client == nil {
		return fmt.Errorf("redis client is not initialized")
	}

	// 只有锁的持有者才能刷新锁
	luaScript := `
		local key = KEYS[1]
		local expected_value = ARGV[1]
		local expiry = ARGV[2]
		local current_value = redis.call('GET', key)
		
		if current_value == expected_value then
			return redis.call('EXPIRE', key, expiry)
		else
			return 0
		end
	`

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	result, err := client.Eval(ctx, luaScript, []string{r.Name}, r.RandKey, int(r.Expiry.Seconds())).Int()
	if err != nil {
		return fmt.Errorf("failed to refresh lock: %w", err)
	}

	if result != 1 {
		return fmt.Errorf("failed to refresh lock %s: not owner or lock expired", r.Name)
	}

	return nil
}
