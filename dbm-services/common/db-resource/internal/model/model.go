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

	"dbm-services/common/db-resource/assets"
	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"
)

// Database database object
type Database struct {
	Self      *gorm.DB
	SelfSqlDB *sql.DB
}

// DB db object
var DB *Database

// TbRpOperationInfoColumns tb_rp_operation_info all columns
var TbRpOperationInfoColumns []string

func init() {
	createSysDb()
	ormDB := initSelfDB()
	sqlDB, err := ormDB.DB()
	if err != nil {
		logger.Fatal("init db connect failed %s", err.Error())
		return
	}
	DB = &Database{
		Self:      ormDB,
		SelfSqlDB: sqlDB,
	}
	initarchive()
	TbRpOperationInfoColumns = []string{}
	TbRpOperationInfoColumns, err = getTbRpOperationInfoColumns()
	if err != nil {
		logger.Error("get table tb_rp_operation_info  columns failed  %v", err)
	}
	if len(TbRpOperationInfoColumns) <= 1 {
		TbRpOperationInfoColumns = []string{"create_time", "-create_time"}
	}
	logger.Info("tb_rp_operation_info columns %v", TbRpOperationInfoColumns)
}

// func migration() {
// 	err := DB.Self.AutoMigrate(&TbRpDailySnapShot{})
// 	if err != nil {
// 		logger.Error("auto migrate failed %v", err)
// 	}
// }

func createSysDb() {
	user := config.AppConfig.Db.UserName
	pwd := config.AppConfig.Db.PassWord
	addr := config.AppConfig.Db.Addr
	testConn := openDB(user, pwd, addr, "")
	dbname := config.AppConfig.Db.Name
	err := testConn.Exec(fmt.Sprintf("create database IF NOT EXISTS `%s`;", dbname)).Error
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb, err := testConn.DB()
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	err = assets.DoMigrateFromEmbed(user, addr, pwd, dbname)
	if err != nil {
		log.Fatalf("init migrate from embed failed:%s", err.Error())
	}
	var autoIncrement sql.NullInt64
	err = testConn.Raw(fmt.Sprintf("select max(id) from `%s`.`%s`", dbname, TbRpDetailArchiveName())).Scan(&autoIncrement).
		Error
	if err != nil {
		log.Printf("get max autoIncrement from tb_rp_detail_archive failed :%s", err.Error())
	}

	if autoIncrement.Valid {
		testConn.Exec(fmt.Sprintf("alter table `%s`.`%s` AUTO_INCREMENT  = %d ", dbname, TbRpDetailName(),
			autoIncrement.Int64+1))
		if err != nil {
			log.Fatalf("get max autoIncrement from tb_rp_detail_archive failed :%s", err.Error())
		}
	}
	sqldb.Close()
}

func openDB(username, password, addr, name string) *gorm.DB {
	dsn := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8mb4&parseTime=%t&loc=%s",
		username,
		password,
		addr,
		name,
		true,
		"Local")
	newLogger := gormlogger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		gormlogger.Config{
			SlowThreshold:             time.Second,
			LogLevel:                  gormlogger.Info,
			IgnoreRecordNotFoundError: false,
			Colorful:                  true,
			ParameterizedQueries:      false,
		},
	)
	db, err := gorm.Open(mysql.New(mysql.Config{
		DSN: dsn,
	}), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		logger.Fatal("Database connection failed. Database name: %s, error: %v", name, err)
	}
	return db
}

// initSelfDB init db
// used for cli
func initSelfDB() *gorm.DB {
	return openDB(
		config.AppConfig.Db.UserName,
		config.AppConfig.Db.PassWord,
		config.AppConfig.Db.Addr,
		config.AppConfig.Db.Name,
	)
}
