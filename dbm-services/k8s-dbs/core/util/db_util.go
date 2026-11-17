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
	"database/sql"
	"fmt"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/config"
	"log/slog"
	"strings"
	"sync"
	"time"

	conconst "k8s-dbs/common/constant"

	"github.com/caarlos0/env/v6"
	mysqldriver "github.com/go-sql-driver/mysql"
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
	DbsGormDb *gorm.DB
}

func dbConfig() (*config.DbsDatabaseConfig, error) {
	dbsDbCfg := &config.DbsDatabaseConfig{}
	if err := env.Parse(dbsDbCfg); err != nil {
		return nil, fmt.Errorf("failed to parse dbsDbCfg environment variables: %w", err)
	}
	return dbsDbCfg, nil
}

// initDatabase 通用的数据库初始化函数
func initDatabase(cfg *config.DatabaseConfig, dbName string) (*gorm.DB, error) {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=UTC&tls=%s",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.DBName, cfg.TLSMode)
	driverConfig, err := mysqldriver.ParseDSN(dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to parse %s database DSN: %w", dbName, err)
	}
	probeConnector, err := mysqldriver.NewConnector(driverConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create %s database probe connector: %w", dbName, err)
	}
	probeDb := sql.OpenDB(probeConnector)
	loc, err := detectDatabaseLocation(probeDb)
	_ = probeDb.Close()
	if err != nil {
		return nil, fmt.Errorf("failed to detect %s database timezone: %w", dbName, err)
	}
	driverConfig.Loc = loc
	connector, err := mysqldriver.NewConnector(driverConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create %s database connector: %w", dbName, err)
	}
	sqlDb := sql.OpenDB(connector)

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
	db, err := gorm.Open(mysql.New(mysql.Config{Conn: sqlDb, DSNConfig: driverConfig}), gormConfig)
	if err != nil {
		_ = sqlDb.Close()
		return nil, fmt.Errorf("failed to connect to %s database: %w", dbName, err)
	}

	sqlDb.SetMaxOpenConns(cfg.MaxOpenConns)
	sqlDb.SetMaxIdleConns(cfg.MaxIdleConns)
	sqlDb.SetConnMaxLifetime(cfg.MaxLifetime)
	sqlDb.SetConnMaxIdleTime(cfg.MaxIdleTime)

	if err = sqlDb.Ping(); err != nil {
		_ = sqlDb.Close()
		return nil, fmt.Errorf("failed to ping %s database: %w", dbName, err)
	}

	slog.Info("Database connection established", "database", dbName, "timezone", loc.String())
	return db, nil
}

func detectDatabaseLocation(db *sql.DB) (*time.Location, error) {
	var sessionTimeZone, systemTimeZone string
	var offsetSeconds int
	err := db.QueryRow(
		"SELECT @@session.time_zone, @@system_time_zone, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())",
	).Scan(&sessionTimeZone, &systemTimeZone, &offsetSeconds)
	if err != nil {
		return nil, fmt.Errorf("failed to query database timezone: %w", err)
	}
	if sessionTimeZone != "SYSTEM" && !strings.HasPrefix(sessionTimeZone, "+") &&
		!strings.HasPrefix(sessionTimeZone, "-") {
		loc, err := time.LoadLocation(sessionTimeZone)
		if err != nil {
			return nil, fmt.Errorf("failed to load database timezone %q: %w", sessionTimeZone, err)
		}
		return loc, nil
	}
	if offsetSeconds == 0 {
		return time.UTC, nil
	}
	return time.FixedZone(fmt.Sprintf("MySQL(%s,%s)", sessionTimeZone, systemTimeZone), offsetSeconds), nil
}

func (d *database) Init() error {
	once.Do(func() {
		dbsDbCfg, err := dbConfig()
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
