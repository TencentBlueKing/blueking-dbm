/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package model dao
package model

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/assets"
)

// DB TODO
var DB *gorm.DB

func init() {
	user := config.GAppConfig.DbConf.User
	pwd := config.GAppConfig.DbConf.Pwd
	addr := fmt.Sprintf("%s:%d", config.GAppConfig.DbConf.Host, config.GAppConfig.DbConf.Port)
	dbName := config.GAppConfig.DbConf.Name
	log.Printf("connect to %s", addr)
	testConn := openDB(user, pwd, addr, "")
	err := testConn.Exec(fmt.Sprintf("create database IF NOT EXISTS `%s`;", dbName)).Error
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb, err := testConn.DB()
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	log.Println("make dbeug dbname", dbName)
	err = assets.DoMigrateFromEmbed(user, addr, pwd, dbName)
	if err != nil {
		log.Fatalf("init migrate from embed failed:%s", err.Error())
	}
	sqldb.Close()
	DB = openDB(user, pwd, addr, dbName)
}

func openDB(username, password, addr, name string) *gorm.DB {
	newLogger := logger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags), // io writer
		logger.Config{
			SlowThreshold: time.Second, // Slow SQL threshold
			LogLevel:      logger.Info, // Log level
			Colorful:      true,        // Disable color
		},
	)
	dsn := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8mb4&parseTime=%t&loc=%s",
		username,
		password,
		addr,
		name,
		true,
		"Local")
	var err error
	dbc, err := sql.Open("mysql", dsn)
	if err != nil {
		log.Fatalf("connect to mysql failed %s", err.Error())
		return nil
	}
	db, err := gorm.Open(mysql.New(mysql.Config{
		Conn: dbc,
	}), &gorm.Config{
		DisableForeignKeyConstraintWhenMigrating: true,
		Logger:                                   newLogger,
	})

	if err != nil {
		log.Fatalf("Database connection failed. Database name: %s, error: %v", name, err)
	}
	return db
}
