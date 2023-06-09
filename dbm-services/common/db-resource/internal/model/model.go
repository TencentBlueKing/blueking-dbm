// Package model TODO
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

// Database TODO
type Database struct {
	Self      *gorm.DB
	SelfSqlDB *sql.DB
}

// DB TODO
var DB *Database

// CMDBDB TODO
var CMDBDB *Database

func init() {
	log.Println("init db model..")
	createSysDb()
	orm_db := initSelfDB()
	sqlDB, err := orm_db.DB()
	if err != nil {
		logger.Fatal("init db connect failed %s", err.Error())
		return
	}
	DB = &Database{
		Self:      orm_db,
		SelfSqlDB: sqlDB,
	}
	d2 := initDBMDB()
	d2sqlDb, err := d2.DB()
	if err != nil {
		logger.Fatal("init db connect failed %s", err.Error())
		return
	}
	CMDBDB = &Database{
		Self:      d2,
		SelfSqlDB: d2sqlDb,
	}
	migration()
	initarchive()
}

func createSysDb() {
	user := config.AppConfig.Db.UserName
	pwd := config.AppConfig.Db.PassWord
	addr := config.AppConfig.Db.Addr
	testConn := openDB(user, pwd, addr, "")
	err := testConn.Exec(fmt.Sprintf("create database IF NOT EXISTS `%s`;", config.AppConfig.Db.Name)).Error
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb, err := testConn.DB()
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
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

// initSelfDB TODO
// used for cli
func initSelfDB() *gorm.DB {
	return openDB(
		config.AppConfig.Db.UserName,
		config.AppConfig.Db.PassWord,
		config.AppConfig.Db.Addr,
		config.AppConfig.Db.Name,
	)
}

func initDBMDB() *gorm.DB {
	return openDB(
		config.AppConfig.CmdbDb.UserName,
		config.AppConfig.CmdbDb.PassWord,
		config.AppConfig.CmdbDb.Addr,
		config.AppConfig.CmdbDb.Name,
	)
}

// migration TODO
func migration() {
	DB.Self.AutoMigrate(&TbRpDetail{}, &TbRequestLog{}, &TbRpDetailArchive{}, &TbRpApplyDetailLog{}, &TbRpOperationInfo{})
}

// QueryCountSelfCommon TODO
func (db Database) QueryCountSelfCommon(sqltext string) (int, error) {
	var count int
	c_db := db.Self.Raw(sqltext)
	if c_db.Error != nil {
		return 0, c_db.Error
	}
	if err := c_db.Row().Scan(&count); err != nil {
		return 0, err
	}
	return count, nil
}

// QuerySelfCommon TODO
func (db *Database) QuerySelfCommon(sqltext string) ([]map[string]interface{}, error) {
	cursor, err := db.SelfSqlDB.Query(sqltext)
	if err != nil || cursor.Err() != nil {
		return nil, fmt.Errorf("db query failed, err: %+v", err)
	}
	defer cursor.Close()
	columns, err := cursor.Columns()
	if err != nil {
		return nil, fmt.Errorf("get columns failed, err: %+v", err)
	}
	columnTypes, err := cursor.ColumnTypes()
	if err != nil {
		return nil, fmt.Errorf("get column types failed, err: %+v", err)
	}

	count := len(columns)
	values := make([]interface{}, count)
	scanArgs := make([]interface{}, count)
	for i := range values {
		scanArgs[i] = &values[i]
	}

	dataRows := make([]map[string]interface{}, 0)
	for cursor.Next() {
		row := make(map[string]interface{})
		err := cursor.Scan(scanArgs...)
		if err != nil {
			return nil, fmt.Errorf("scan data failed, err: %+v", err)
		}
		for i, col := range columns {
			columnType := columnTypes[i]
			columnType.ScanType()
			var v interface{}
			val := values[i]
			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}
			row[col] = v
		}
		dataRows = append(dataRows, row)
	}
	return dataRows, err
}

// JSONQueryExpression json query expression, implements clause.Expression interface to use as querier
type JSONQueryExpression struct {
	column         string
	keys           []string
	hasKeys        bool
	equals         bool
	equalsValue    interface{}
	extract        bool
	path           string
	numranges      bool
	numRange       NumRange
	Gtv            int
	gte            bool
	Ltv            int
	lte            bool
	contains       bool
	containVals    []string
	mapcontains    bool
	mapcontainVals []string
	subcontains    bool
	subcontainVal  string
}

// NumRange TODO
type NumRange struct {
	Min int
	Max int
}

// JSONQuery query column as json
func JSONQuery(column string) *JSONQueryExpression {
	return &JSONQueryExpression{column: column}
}

// SubValContains TODO
func (jsonQuery *JSONQueryExpression) SubValContains(val string, key string) *JSONQueryExpression {
	jsonQuery.subcontains = true
	jsonQuery.subcontainVal = val
	jsonQuery.keys = []string{key}
	return jsonQuery
}

// KeysContains TODO
func (jsonQuery *JSONQueryExpression) KeysContains(val []string) *JSONQueryExpression {
	jsonQuery.mapcontains = true
	jsonQuery.mapcontainVals = val
	return jsonQuery
}

// Contains TODO
// Extract extract json with path
func (jsonQuery *JSONQueryExpression) Contains(val []string) *JSONQueryExpression {
	jsonQuery.contains = true
	jsonQuery.containVals = val
	return jsonQuery
}

// Extract extract json with path
func (jsonQuery *JSONQueryExpression) Extract(path string) *JSONQueryExpression {
	jsonQuery.extract = true
	jsonQuery.path = path
	return jsonQuery
}

// NumRange TODO
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

// Gte TODO
func (jsonQuery *JSONQueryExpression) Gte(val int, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.Gtv = val
	return jsonQuery
}

// Lte TODO
func (jsonQuery *JSONQueryExpression) Lte(val int, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.Ltv = val
	return jsonQuery
}

// HasKey returns clause.Expression
func (jsonQuery *JSONQueryExpression) HasKey(keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.hasKeys = true
	return jsonQuery
}

// Equals TODO
// Keys returns clause.Expression
func (jsonQuery *JSONQueryExpression) Equals(value interface{}, keys ...string) *JSONQueryExpression {
	jsonQuery.keys = keys
	jsonQuery.equals = true
	jsonQuery.equalsValue = value
	return jsonQuery
}

// Build implements clause.Expression
func (jsonQuery *JSONQueryExpression) Build(builder clause.Builder) {
	if stmt, ok := builder.(*gorm.Statement); ok {
		switch stmt.Dialector.Name() {
		case "mysql", "sqlite":
			switch {
			case jsonQuery.extract:
				builder.WriteString("JSON_EXTRACT(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteByte(',')
				builder.AddVar(stmt, jsonQuery.path)
				builder.WriteString(")")
			case jsonQuery.hasKeys:
				if len(jsonQuery.keys) > 0 {
					builder.WriteString("JSON_EXTRACT(")
					builder.WriteQuoted(jsonQuery.column)
					builder.WriteByte(',')
					builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
					builder.WriteString(") IS NOT NULL")
				}
			case jsonQuery.gte:
				builder.WriteString("JSON_EXTRACT(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteByte(',')
				builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
				builder.WriteString(") >=")
				builder.WriteString(strconv.Itoa(jsonQuery.Gtv))
			case jsonQuery.lte:
				builder.WriteString("JSON_EXTRACT(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteByte(',')
				builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
				builder.WriteString(") <=")
				builder.WriteString(strconv.Itoa(jsonQuery.Ltv))
			case jsonQuery.numranges:
				builder.WriteString("JSON_EXTRACT(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteByte(',')
				builder.AddVar(stmt, jsonQueryJoin(jsonQuery.keys))
				builder.WriteString(") ")
				builder.WriteString(" BETWEEN ")
				builder.WriteString(strconv.Itoa(jsonQuery.numRange.Min))
				builder.WriteString(" AND ")
				builder.WriteString(strconv.Itoa(jsonQuery.numRange.Max))
			case jsonQuery.mapcontains:
				builder.WriteString("JSON_CONTAINS(JSON_KEYS(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteString("),'[")
				builder.WriteString(jsonArryJoin(jsonQuery.mapcontainVals))
				builder.WriteString("]') ")
			case jsonQuery.contains:
				builder.WriteString("JSON_CONTAINS(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteString(",'")
				builder.WriteString("[")
				builder.WriteString(jsonArryJoin(jsonQuery.containVals))
				builder.WriteString("]') ")
			case jsonQuery.subcontains:
				builder.WriteString("JSON_CONTAINS(JSON_EXTRACT(")
				builder.WriteQuoted(jsonQuery.column)
				builder.WriteString(",'$.*.\"")
				builder.WriteString(jsonQuery.keys[0])
				builder.WriteString("\"'),'[\"")
				builder.WriteString(jsonQuery.subcontainVal)
				builder.WriteString("\"]') ")
			case jsonQuery.equals:
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
