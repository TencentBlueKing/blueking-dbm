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

package client

import (
	"fmt"
	"k8s-dbs/config"
	"log/slog"
	"os"
	"strconv"
	"time"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

var Db database

type database struct {
	GormDb *gorm.DB
}

func dbConfig() (*config.DatabaseConfig, error) {
	dbCfg := &config.DatabaseConfig{}
	dbCfg.Host = os.Getenv("MYSQL_HOST")
	dbCfg.Port, _ = strconv.Atoi(os.Getenv("MYSQL_PORT"))
	dbCfg.User = os.Getenv("MYSQL_USER")
	dbCfg.Password = os.Getenv("MYSQL_PASSWORD")
	dbCfg.DBName = os.Getenv("MYSQL_DBNAME")
	dbCfg.TLSMode = os.Getenv("MYSQL_TLSMODE")
	dbCfg.MaxOpenConns, _ = strconv.Atoi(os.Getenv("MYSQL_MAX_OPEN_CONN"))
	dbCfg.MaxIdleConns, _ = strconv.Atoi(os.Getenv("MYSQL_MAX_IDLE_CONN"))
	dbCfg.MaxLifetime, _ = time.ParseDuration(os.Getenv("MYSQL_MAX_LIFETIME"))
	dbCfg.MaxIdleTime, _ = time.ParseDuration(os.Getenv("MYSQL_MAX_IDLE_TIME"))
	return dbCfg, nil
}

func (d *database) Init() error {
	dbCfg, err := dbConfig()
	if err != nil {
		slog.Error("Failed to load config", "err", err)
		return err
	}
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local&tls=%s",
		dbCfg.User, dbCfg.Password, dbCfg.Host, dbCfg.Port, dbCfg.DBName, dbCfg.TLSMode)
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		slog.Error("Failed to connect to database", "err", err)
		return err
	}
	// 获取底层数据库对象
	sqlDb, err := db.DB()
	if err != nil {
		slog.Error("failed to get database object", "error", err)
		return err
	}

	// 设置数据库连接池参数
	sqlDb.SetMaxOpenConns(dbCfg.MaxOpenConns)
	sqlDb.SetMaxIdleConns(dbCfg.MaxIdleConns)
	sqlDb.SetConnMaxLifetime(dbCfg.MaxLifetime)
	sqlDb.SetConnMaxIdleTime(dbCfg.MaxIdleTime)

	// Ping 数据库，确认连接
	if err = sqlDb.Ping(); err != nil {
		slog.Error("Failed to ping database", "err", err)
		return err
	}
	slog.Info("Database connection established")
	Db.GormDb = db
	return nil
}
