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
	"sync"
	"time"

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
var (
	// SubzoneIdMap 园区ID,园区名称对应关系
	SubzoneIdMap map[string]string
	once         sync.Once
)

// InitModel 初始化模型
func InitModel() {
	createSysDb()
	ormDB := initSelfDB()
	sqlDB, err := ormDB.DB()
	if err != nil {
		logger.Fatal("init db connect failed %s", err.Error())
		return
	}
	// GORM AutoMigrate - 自动同步所有模型到数据库
	err = ormDB.AutoMigrate(&TbRequestLog{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRequestLog failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpAnalysisResult{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpAnalysisResult failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpDetailArchive{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpDetailArchive failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpApplyDetailLog{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpApplyDetailLog failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpDetail{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpDetail failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpOperationInfo{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpOperationInfo failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpStatusChangeLog{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpStatusChangeLog failed: %s", err.Error())
		return
	}
	err = ormDB.AutoMigrate(&TbRpDailySnapShot{})
	if err != nil {
		logger.Fatal("AutoMigrate TbRpDailySnapShot failed: %s", err.Error())
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

	once.Do(func() {
		subzoneIdMap, err := GetSubzoneIdMap()
		if err != nil {
			logger.Error("GetSubzoneIdMap failed, err:%s", err.Error())
			SubzoneIdMap = make(map[string]string) // 避免panic，初始化为空map
			return
		}
		SubzoneIdMap = subzoneIdMap
	})
	for k, v := range SubzoneIdMap {
		logger.Info("subzoneIdMap %s:%s", k, v)
	}
	logger.Info("tb_rp_operation_info columns %v", TbRpOperationInfoColumns)
}

// validateIdentifier 校验数据库标识符（数据库名、表名等）的安全性
func validateIdentifier(name string) error {
	// 只允许字母、数字、下划线，且不能以数字开头
	if len(name) == 0 || len(name) > 64 {
		return fmt.Errorf("invalid identifier length: %s", name)
	}
	for i, r := range name {
		if i == 0 && (r >= '0' && r <= '9') {
			return fmt.Errorf("identifier cannot start with digit: %s", name)
		}
		if !((r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '_' || r == '-') {
			return fmt.Errorf("invalid character in identifier: %s", name)
		}
	}
	return nil
}

func createSysDb() {
	user := config.AppConfig.Db.UserName
	pwd := config.AppConfig.Db.PassWord
	addr := config.AppConfig.Db.Addr
	testConn := openDB(user, pwd, addr, "")
	dbname := config.AppConfig.Db.Name

	// 安全校验数据库名
	if err := validateIdentifier(dbname); err != nil {
		log.Fatalf("invalid database name: %s", err.Error())
	}

	// 使用参数化查询创建数据库（注意：MySQL不支持参数化DDL，但我们已经校验了标识符）
	err := testConn.Exec(fmt.Sprintf("CREATE DATABASE IF NOT EXISTS `%s`", dbname)).Error
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb, err := testConn.DB()
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	// 注释掉 migration 模式，完全使用 GORM AutoMigrate
	// err = assets.DoMigrateFromEmbed(user, addr, pwd, dbname)
	// if err != nil {
	// 	log.Fatalf("init migrate from embed failed:%s", err.Error())
	// }

	// 获取表名并校验
	archiveTableName := TbRpDetailArchiveName()
	detailTableName := TbRpDetailName()
	err = validateIdentifier(archiveTableName)
	if err != nil {
		log.Fatalf("invalid archive table name: %s", err.Error())
	}
	err = validateIdentifier(detailTableName)
	if err != nil {
		log.Fatalf("invalid detail table name: %s", err.Error())
	}

	var autoIncrement sql.NullInt64
	// 使用校验过的标识符构建查询
	query := fmt.Sprintf("SELECT MAX(id) FROM `%s`.`%s`", dbname, archiveTableName)
	err = testConn.Raw(query).Scan(&autoIncrement).Error
	if err != nil {
		log.Printf("get max autoIncrement from tb_rp_detail_archive failed :%s", err.Error())
	}

	if autoIncrement.Valid {
		alterQuery := fmt.Sprintf("ALTER TABLE `%s`.`%s` AUTO_INCREMENT = %d", dbname, detailTableName, autoIncrement.Int64+1)
		err = testConn.Exec(alterQuery).Error
		if err != nil {
			log.Fatalf("alter table auto_increment failed :%s", err.Error())
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
