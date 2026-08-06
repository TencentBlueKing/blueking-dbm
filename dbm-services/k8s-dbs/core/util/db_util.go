/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Package util 提供 core 模块的辅助工具函数（如数据库操作）
package util

import (
	"fmt"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/config"
	"log/slog"
	"sync"

	conconst "k8s-dbs/common/constant"

	"github.com/caarlos0/env/v6"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var (
	once    sync.Once
	initErr error
	// Db 全局数据库连接单例
	Db = &database{}
)

type database struct {
	DbsGormDb  *gorm.DB
	AuthGormDb *gorm.DB
}

func dbConfig() (*config.DbsDatabaseConfig, *config.AuthDatabaseConfig, error) {
	dbsDbCfg := &config.DbsDatabaseConfig{}
	if err := env.Parse(dbsDbCfg); err != nil {
		return nil, nil, fmt.Errorf("failed to parse dbsDbCfg environment variables: %w", err)
	}
	authDbCfg := &config.AuthDatabaseConfig{}
	if err := env.Parse(authDbCfg); err != nil {
		return nil, nil, fmt.Errorf("failed to parse authDbCfg environment variables: %w", err)
	}
	return dbsDbCfg, authDbCfg, nil
}

// initDatabase 通用的数据库初始化函数
func initDatabase(cfg *config.DatabaseConfig, dbName string) (*gorm.DB, error) {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=UTC&tls=%s",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.DBName, cfg.TLSMode)

	// 根据日志级别配置 GORM 日志输出
	// 注意：GORM 的日志级别定义为 Silent < Error < Warn < Info
	// Info 是最详细的级别，会输出所有 SQL 语句
	gormConfig := &gorm.Config{}
	logLevel := commutil.GetEnv(conconst.EnvLogLevel, conconst.DefaultLogLevel)
	if logLevel == "debug" {
		gormConfig.Logger = logger.Default.LogMode(logger.Info)
		slog.Info("Database debug mode enabled", "database", dbName, "gormLogLevel", "Info")
	} else {
		gormConfig.Logger = logger.Default.LogMode(logger.Silent)
	}
	db, err := gorm.Open(mysql.Open(dsn), gormConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to %s database: %w", dbName, err)
	}

	sqlDb, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get %s database object: %w", dbName, err)
	}

	sqlDb.SetMaxOpenConns(cfg.MaxOpenConns)
	sqlDb.SetMaxIdleConns(cfg.MaxIdleConns)
	sqlDb.SetConnMaxLifetime(cfg.MaxLifetime)
	sqlDb.SetConnMaxIdleTime(cfg.MaxIdleTime)

	if err = sqlDb.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping %s database: %w", dbName, err)
	}

	slog.Info("Database connection established", "database", dbName)
	return db, nil
}

func (d *database) Init() error {
	once.Do(func() {
		dbsDbCfg, authDbCfg, err := dbConfig()
		if err != nil {
			initErr = fmt.Errorf("failed to load config: %w", err)
			slog.Error("Failed to load config", "err", err)
			return
		}

		// 初始化 DBS 数据库
		dbsDb, err := initDatabase(&dbsDbCfg.DatabaseConfig, "dbs")
		if err != nil {
			initErr = err
			slog.Error("Failed to initialize dbs database", "err", err)
			return
		}
		Db.DbsGormDb = dbsDb

		// 初始化 Auth 数据库
		authDb, err := initDatabase(&authDbCfg.DatabaseConfig, "auth")
		if err != nil {
			initErr = err
			slog.Error("Failed to initialize auth database", "err", err)
			return
		}
		Db.AuthGormDb = authDb
	})
	return initErr
}

// ResetForTesting 测试辅助函数，用于重置单例状态
// 仅在测试环境中使用
func ResetForTesting() {
	once = sync.Once{}
	initErr = nil
	Db = &database{}
}
