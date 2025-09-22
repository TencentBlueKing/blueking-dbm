/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package statistic sync.Once 使用示例
package statistic

import (
	"fmt"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// 示例1: 单例模式 - 全局配置
var (
	globalConfig *Config
	configOnce   sync.Once
)

// Config 全局配置结构
type Config struct {
	DatabaseURL string
	RedisURL    string
	LogLevel    string
	Initialized bool
}

// GetGlobalConfig 获取全局配置，确保只初始化一次
func GetGlobalConfig() *Config {
	configOnce.Do(func() {
		logger.Info("初始化全局配置...")
		globalConfig = &Config{
			DatabaseURL: "mysql://localhost:3306/dbm",
			RedisURL:    "redis://localhost:6379",
			LogLevel:    "info",
			Initialized: true,
		}
		logger.Info("全局配置初始化完成")
	})
	return globalConfig
}

// 示例2: 延迟初始化 - 数据库连接池
var (
	dbPool     *DatabasePool
	dbPoolOnce sync.Once
)

// DatabasePool 数据库连接池结构
type DatabasePool struct {
	MaxConnections int
	CurrentConn    int
	Initialized    bool
}

func (p *DatabasePool) String() string {
	return fmt.Sprintf("DatabasePool{MaxConn: %d, CurrentConn: %d, Initialized: %t}",
		p.MaxConnections, p.CurrentConn, p.Initialized)
}

// GetDatabasePool 获取数据库连接池，确保只初始化一次
func GetDatabasePool() *DatabasePool {
	dbPoolOnce.Do(func() {
		logger.Info("初始化数据库连接池...")
		// 模拟初始化过程
		time.Sleep(100 * time.Millisecond)
		dbPool = &DatabasePool{
			MaxConnections: 100,
			CurrentConn:    0,
			Initialized:    true,
		}
		logger.Info("数据库连接池初始化完成: %s", dbPool.String())
	})
	return dbPool
}

// 示例3: 缓存初始化 - 资源规格缓存
var (
	specCache     map[string]interface{}
	specCacheOnce sync.Once
)

// InitSpecCache 初始化规格缓存，确保只执行一次
func InitSpecCache() {
	specCacheOnce.Do(func() {
		logger.Info("初始化规格缓存...")
		specCache = make(map[string]interface{})

		// 模拟从数据库加载规格数据
		specCache["mysql_small"] = map[string]interface{}{
			"cpu":    2,
			"memory": 4,
			"disk":   100,
		}
		specCache["mysql_medium"] = map[string]interface{}{
			"cpu":    4,
			"memory": 8,
			"disk":   200,
		}
		specCache["mysql_large"] = map[string]interface{}{
			"cpu":    8,
			"memory": 16,
			"disk":   500,
		}

		logger.Info("规格缓存初始化完成，加载了 %d 个规格", len(specCache))
	})
}

// GetSpecCache 获取规格缓存
func GetSpecCache() map[string]interface{} {
	InitSpecCache()
	return specCache
}

// 示例4: 错误处理 - 带错误检查的初始化
var (
	serviceClient *ServiceClient
	serviceOnce   sync.Once
	serviceErr    error
)

// ServiceClient 服务客户端结构
type ServiceClient struct {
	Endpoint string
	Timeout  time.Duration
	Ready    bool
}

// InitServiceClient 初始化服务客户端，带错误处理
func InitServiceClient() (*ServiceClient, error) {
	serviceOnce.Do(func() {
		logger.Info("初始化服务客户端...")

		// 模拟可能失败的操作
		if time.Now().Unix()%2 == 0 { // 模拟50%的失败率
			serviceErr = fmt.Errorf("服务连接失败")
			logger.Error("服务客户端初始化失败: %v", serviceErr)
			return
		}

		serviceClient = &ServiceClient{
			Endpoint: "http://api.example.com",
			Timeout:  30 * time.Second,
			Ready:    true,
		}
		logger.Info("服务客户端初始化成功")
	})

	return serviceClient, serviceErr
}

// 示例5: 条件初始化 - 根据环境变量初始化
var (
	envConfig     *EnvironmentConfig
	envConfigOnce sync.Once
)

// EnvironmentConfig 环境配置结构
type EnvironmentConfig struct {
	Environment string
	DebugMode   bool
	APIVersion  string
}

// GetEnvironmentConfig 根据环境变量初始化配置
func GetEnvironmentConfig() *EnvironmentConfig {
	envConfigOnce.Do(func() {
		logger.Info("初始化环境配置...")

		env := "production" // 这里可以从环境变量读取
		debugMode := false
		apiVersion := "v1"

		if env == "development" {
			debugMode = true
			apiVersion = "v1-dev"
		}

		envConfig = &EnvironmentConfig{
			Environment: env,
			DebugMode:   debugMode,
			APIVersion:  apiVersion,
		}

		logger.Info("环境配置初始化完成: %s, Debug: %t, API: %s",
			envConfig.Environment, envConfig.DebugMode, envConfig.APIVersion)
	})
	return envConfig
}

// 示例6: 重置功能 - 允许重新初始化（谨慎使用）
var (
	counter     int
	counterOnce sync.Once
	counterMu   sync.Mutex
)

// GetCounter 获取计数器，确保只初始化一次
func GetCounter() int {
	counterOnce.Do(func() {
		logger.Info("初始化计数器...")
		counter = 0
		logger.Info("计数器初始化完成")
	})
	return counter
}

// IncrementCounter 增加计数器
func IncrementCounter() int {
	counterMu.Lock()
	defer counterMu.Unlock()

	GetCounter() // 确保已初始化
	counter++
	return counter
}

// ResetCounter 重置计数器（谨慎使用，通常不推荐）
func ResetCounter() {
	counterMu.Lock()
	defer counterMu.Unlock()

	// 注意：sync.Once 不能重置，这里只是重置变量
	// 真正的重置需要重新创建 sync.Once 实例
	counter = 0
	logger.Info("计数器已重置")
}

// TestSyncOnceConcurrency 并发测试 - 验证 sync.Once 的线程安全性
func TestSyncOnceConcurrency() {
	logger.Info("开始并发测试 sync.Once...")

	var wg sync.WaitGroup
	numGoroutines := 100

	// 启动多个 goroutine 同时调用初始化函数
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			// 每个 goroutine 都尝试初始化
			config := GetGlobalConfig()
			logger.Info("Goroutine %d 获取配置: %+v", id, config)
		}(i)
	}

	wg.Wait()
	logger.Info("并发测试完成，所有 goroutine 都获取到了相同的配置实例")
}

// BenchmarkSyncOnce 性能测试 - 比较 sync.Once 和普通初始化的性能
func BenchmarkSyncOnce() {
	// 测试 sync.Once 的性能
	start := time.Now()
	for i := 0; i < 10000; i++ {
		GetGlobalConfig()
	}
	syncOnceDuration := time.Since(start)

	logger.Info("sync.Once 性能测试完成，耗时: %v", syncOnceDuration)
}

// RunSyncOnceExamples 运行所有 sync.Once 示例
func RunSyncOnceExamples() {
	logger.Info("=== 开始运行 sync.Once 示例 ===")

	// 示例1: 全局配置
	logger.Info("\n--- 示例1: 全局配置 ---")
	config1 := GetGlobalConfig()
	config2 := GetGlobalConfig()
	logger.Info("配置1: %+v", config1)
	logger.Info("配置2: %+v", config2)
	logger.Info("是否为同一实例: %t", config1 == config2)

	// 示例2: 数据库连接池
	logger.Info("\n--- 示例2: 数据库连接池 ---")
	pool1 := GetDatabasePool()
	pool2 := GetDatabasePool()
	logger.Info("连接池1: %s", pool1.String())
	logger.Info("连接池2: %s", pool2.String())
	logger.Info("是否为同一实例: %t", pool1 == pool2)

	// 示例3: 规格缓存
	logger.Info("\n--- 示例3: 规格缓存 ---")
	cache1 := GetSpecCache()
	cache2 := GetSpecCache()
	logger.Info("缓存1大小: %d", len(cache1))
	logger.Info("缓存2大小: %d", len(cache2))
	logger.Info("是否为同一实例: %t", &cache1 == &cache2)

	// 示例4: 服务客户端（带错误处理）
	logger.Info("\n--- 示例4: 服务客户端 ---")
	client1, err1 := InitServiceClient()
	client2, err2 := InitServiceClient()
	logger.Info("客户端1: %+v, 错误: %v", client1, err1)
	logger.Info("客户端2: %+v, 错误: %v", client2, err2)

	// 示例5: 环境配置
	logger.Info("\n--- 示例5: 环境配置 ---")
	env1 := GetEnvironmentConfig()
	env2 := GetEnvironmentConfig()
	logger.Info("环境配置1: %+v", env1)
	logger.Info("环境配置2: %+v", env2)

	// 示例6: 计数器
	logger.Info("\n--- 示例6: 计数器 ---")
	for i := 0; i < 5; i++ {
		count := IncrementCounter()
		logger.Info("计数器值: %d", count)
	}

	// 示例7: 并发测试
	logger.Info("\n--- 示例7: 并发测试 ---")
	TestSyncOnceConcurrency()

	// 示例8: 性能测试
	logger.Info("\n--- 示例8: 性能测试 ---")
	BenchmarkSyncOnce()

	logger.Info("\n=== sync.Once 示例运行完成 ===")
}
