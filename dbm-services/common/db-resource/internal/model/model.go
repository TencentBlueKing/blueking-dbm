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
	"strconv"
	"strings"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
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
	migration()
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

// migration migration
func migration() {
	err := DB.Self.AutoMigrate(&TbRpDetail{}, &TbRequestLog{}, &TbRpDetailArchive{}, &TbRpApplyDetailLog{},
		&TbRpOperationInfo{})
	if err != nil {
		logger.Error("auto migrate failed %v", err)
	}
}

// JSONQueryExpression json query expression, implements clause.Expression interface to use as querier
type JSONQueryExpression struct {
	column             string
	keys               []string
	hasKeys            bool
	equals             bool
	equalsValue        interface{}
	extract            bool
	path               string
	numranges          bool
	numRange           NumRange
	Gtv                int
	gte                bool
	Ltv                int
	lte                bool
	contains           bool
	containVals        []string
	mapcontains        bool
	mapcontainVals     []string
	subcontains        bool
	subcontainVal      string
	jointOrContains    bool
	jointOrContainVals []string
}

// NumRange num range
type NumRange struct {
	Min int
	Max int
}

// JSONQuery query column as json
func JSONQuery(column string) *JSONQueryExpression {
	return &JSONQueryExpression{column: column}
}

// SubValContains  sub value contains
func (jsonQuery *JSONQueryExpression) SubValContains(val string, key string) *JSONQueryExpression {
	jsonQuery.subcontains = true
	jsonQuery.subcontainVal = val
	jsonQuery.keys = []string{key}
	return jsonQuery
}

// KeysContains key contains
func (jsonQuery *JSONQueryExpression) KeysContains(val []string) *JSONQueryExpression {
	jsonQuery.mapcontains = true
	jsonQuery.mapcontainVals = val
	return jsonQuery
}

// Contains contains
// Extract extract json with path
func (jsonQuery *JSONQueryExpression) Contains(val []string) *JSONQueryExpression {
	jsonQuery.contains = true
	jsonQuery.containVals = val
	return jsonQuery
}

// JointOrContains jointOrContains
func (jsonQuery *JSONQueryExpression) JointOrContains(val []string) *JSONQueryExpression {
	jsonQuery.jointOrContains = true
	jsonQuery.jointOrContainVals = val

	return jsonQuery
}

// Extract extract json with path
func (jsonQuery *JSONQueryExpression) Extract(path string) *JSONQueryExpression {
	jsonQuery.extract = true
	jsonQuery.path = path
	return jsonQuery
}

// NumRange num range
// HasKey returns clause.Expression
func (jsonQuery *JSONQueryExpression) NumRange(min int, max int, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.numRange = NumRange{
		Min: min,
		Max: max,
	}
	jsonQuery.numranges = true
	return jsonQuery
}

// Gte gte
func (jsonQuery *JSONQueryExpression) Gte(val int, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.Gtv = val
	jsonQuery.gte = true
	return jsonQuery
}

// Lte lte
func (jsonQuery *JSONQueryExpression) Lte(val int, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.Ltv = val
	jsonQuery.lte = true
	return jsonQuery
}

// HasKey returns clause.Expression
func (jsonQuery *JSONQueryExpression) HasKey(keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.hasKeys = true
	return jsonQuery
}

// Equals equals
// Keys returns clause.Expression
func (jsonQuery *JSONQueryExpression) Equals(value interface{}, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.equals = true
	jsonQuery.equalsValue = value
	return jsonQuery
}

// jointOrContainsBuild jointOrContainsBuild
// nolint
func (jsonQuery *JSONQueryExpression) jointOrContainsBuild(builder clause.Builder) {
	for idx, v := range jsonQuery.jointOrContainVals {
		if idx != 0 {
			builder.WriteString(" OR ")
		}
		builder.WriteString("JSON_CONTAINS(")
		builder.WriteQuoted(jsonQuery.column)
		builder.WriteString(",'")
		builder.WriteString("[\"")
		builder.WriteString(v)
		builder.WriteString("\"]') ")
	}
}

// extractBuild extractBuild
// nolint
func (jsonQuery *JSONQueryExpression) extractBuild(stmt *gorm.Statement, builder clause.Builder) {
	builder.WriteString("JSON_EXTRACT(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteByte(',')
	builder.AddVar(stmt, jsonQuery.path)
	builder.WriteString(")")
}

// hasKeysBuild build has  key query
// nolint
func (jsonQuery *JSONQueryExpression) hasKeysBuild(stmt *gorm.Statement, builder clause.Builder) {
	if len(jsonQuery.keys) > 0 {
		builder.WriteString("JSON_EXTRACT(")
		builder.WriteQuoted(jsonQuery.column)
		builder.WriteByte(',')
		builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
		builder.WriteString(") IS NOT NULL")
	}
}

// gteBuild build gte query
// nolint
func (jsonQuery *JSONQueryExpression) gteBuild(stmt *gorm.Statement, builder clause.Builder) {
	builder.WriteString("JSON_EXTRACT(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteByte(',')
	builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
	builder.WriteString(") >=")
	builder.WriteString(strconv.Itoa(jsonQuery.Gtv))
}

// lteBuild  build lte query
// nolint
func (jsonQuery *JSONQueryExpression) lteBuild(stmt *gorm.Statement, builder clause.Builder) {
	builder.WriteString("JSON_EXTRACT(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteByte(',')
	builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
	builder.WriteString(") <=")
	builder.WriteString(strconv.Itoa(jsonQuery.Ltv))
}

// numrangesBuild build num range query
// nolint
func (jsonQuery *JSONQueryExpression) numrangesBuild(stmt *gorm.Statement, builder clause.Builder) {
	builder.WriteString("JSON_EXTRACT(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteByte(',')
	builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
	builder.WriteString(") ")
	builder.WriteString(" BETWEEN ")
	builder.WriteString(strconv.Itoa(jsonQuery.numRange.Min))
	builder.WriteString(" AND ")
	builder.WriteString(strconv.Itoa(jsonQuery.numRange.Max))
}

// mapcontainsBuild build map contains query
// nolint
func (jsonQuery *JSONQueryExpression) mapcontainsBuild(builder clause.Builder) {
	builder.WriteString("JSON_CONTAINS(JSON_KEYS(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteString("),'[")
	builder.WriteString(jsonArryJoin(jsonQuery.mapcontainVals))
	builder.WriteString("]') ")
}

// containsBuild build contains query
// nolint
func (jsonQuery *JSONQueryExpression) containsBuild(builder clause.Builder) {
	builder.WriteString("JSON_CONTAINS(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteString(",'")
	builder.WriteString("[")
	builder.WriteString(jsonArryJoin(jsonQuery.containVals))
	builder.WriteString("]') ")
}

// subcontainsBuild build subcontains query
// nolint
func (jsonQuery *JSONQueryExpression) subcontainsBuild(builder clause.Builder) {
	builder.WriteString("JSON_CONTAINS(JSON_EXTRACT(")
	builder.WriteQuoted(jsonQuery.column)
	builder.WriteString(",'$.*.\"")
	builder.WriteString(jsonQuery.keys[0])
	builder.WriteString("\"'),'[\"")
	builder.WriteString(jsonQuery.subcontainVal)
	builder.WriteString("\"]') ")
}

// equalsBuild build equal query
// nolint
func (jsonQuery *JSONQueryExpression) equalsBuild(stmt *gorm.Statement, builder clause.Builder) {
	if len(jsonQuery.keys) > 0 {
		builder.WriteString("JSON_EXTRACT(")
		builder.WriteQuoted(jsonQuery.column)
		builder.WriteByte(',')
		builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
		builder.WriteString(") = ")
		if value, ok := jsonQuery.equalsValue.(bool); ok {
			builder.WriteString(strconv.FormatBool(value))
		} else {
			stmt.AddVar(builder, jsonQuery.equalsValue)
		}
	}
}

// Build implements clause.Expression
func (jsonQuery *JSONQueryExpression) Build(builder clause.Builder) {
	if stmt, ok := builder.(*gorm.Statement); ok {
		if stmt.Dialector.Name() == "mysql" {
			switch {
			case jsonQuery.extract:
				jsonQuery.extractBuild(stmt, builder)
			case jsonQuery.hasKeys:
				jsonQuery.hasKeysBuild(stmt, builder)
			case jsonQuery.gte:
				jsonQuery.gteBuild(stmt, builder)
			case jsonQuery.lte:
				jsonQuery.lteBuild(stmt, builder)
			case jsonQuery.numranges:
				jsonQuery.numrangesBuild(stmt, builder)
			case jsonQuery.mapcontains:
				jsonQuery.mapcontainsBuild(builder)
			case jsonQuery.contains:
				jsonQuery.containsBuild(builder)
			case jsonQuery.jointOrContains:
				jsonQuery.jointOrContainsBuild(builder)
			case jsonQuery.subcontains:
				jsonQuery.subcontainsBuild(builder)
			case jsonQuery.equals:
				jsonQuery.equalsBuild(stmt, builder)
			}
		}
	}
}

func jsonArryJoin(vals []string) string {
	n := len(vals) - 1
	for i := 0; i < len(vals); i++ {
		n += len(vals[i])
	}
	var b strings.Builder
	b.Grow(n)
	for idx, val := range vals {
		b.WriteString("\"")
		b.WriteString(val)
		b.WriteString("\"")
		if idx < len(vals)-1 {
			b.WriteString(",")
		}
	}
	return b.String()
}

const prefix = "$."

func jsonQueryJoin(keys []string) string {
	if len(keys) == 1 {
		return prefix + keys[0]
	}

	n := len(prefix)
	n += len(keys) - 1
	for i := 0; i < len(keys); i++ {
		n += len(keys[i])
	}

	var b strings.Builder
	b.Grow(n)
	b.WriteString(prefix)
	b.WriteString("\"")
	b.WriteString(keys[0])
	b.WriteString("\"")
	for _, key := range keys[1:] {
		b.WriteString(".")
		b.WriteString(key)
	}
	return b.String()
}
