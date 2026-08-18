package model

import (
	"database/sql"
	"fmt"
	"net/url"
	"time"

	"dbm-services/common/dbha/hadb-api/initc"
	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/util"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// Database TODO
type Database struct {
	Self *gorm.DB
}

// HADB TODO
var HADB *Database

// InitHaDB TODO
func InitHaDB() *gorm.DB {
	if err := DoCreateDBIfNotExist(); err != nil {
		log.Logger.Errorf("init hadb failed,%s", err.Error())
		return nil
	}

	haDBInfo := initc.GlobalConfig.HadbInfo
	// 把 sql_mode='' 固化到 DSN 中，避免每条 SQL 前再执行一次 SET sql_mode
	// 同时设置合理的超时，避免网络抖动时连接长时间挂起放大雪崩
	haDBDsn := fmt.Sprintf(
		"%s:%s@tcp(%s:%d)/%s?charset=%s&parseTime=True&loc=Local"+
			"&sql_mode=%s&timeout=5s&readTimeout=10s&writeTimeout=10s",
		haDBInfo.User, haDBInfo.Password, haDBInfo.Host, haDBInfo.Port,
		haDBInfo.Db, haDBInfo.Charset, url.QueryEscape("''"),
	)
	hadb, err := gorm.Open(mysql.Open(haDBDsn), GenerateGormConfig())
	if err != nil {
		log.Logger.Errorf("connect to %s:%d failed:%s", haDBInfo.Host, haDBInfo.Port, err.Error())
		return nil
	}

	if err = DoAutoMigrate(hadb); err != nil {
		log.Logger.Errorf("hadb auto migrate failed, err:%s", err.Error())
	}
	return hadb
}

// 连接池默认参数，配置项缺省或 <=0 时使用
const (
	defaultMaxOpenConns    = 50
	defaultMaxIdleConns    = 10
	defaultConnMaxLifetime = 30 * time.Minute
	defaultConnMaxIdleTime = 5 * time.Minute
)

// setupDB 配置连接池参数，避免连接无上限增长与死连接残留造成的雪崩
// 各参数从 config.yaml 的 hadbInfo.pool 读取，未配置或 <=0 时走默认值
func (db *Database) setupDB() {
	if db == nil || db.Self == nil {
		return
	}
	d, err := db.Self.DB()
	if err != nil {
		log.Logger.Errorf("get db for setup failed:%s", err.Error())
		return
	}

	pool := initc.GlobalConfig.HadbInfo.Pool

	maxOpen := pool.MaxOpenConns
	if maxOpen <= 0 {
		maxOpen = defaultMaxOpenConns
	}
	maxIdle := pool.MaxIdleConns
	if maxIdle <= 0 {
		maxIdle = defaultMaxIdleConns
	}
	// 避免 idle > open 造成不必要的连接抖动
	if maxIdle > maxOpen {
		maxIdle = maxOpen
	}
	lifetime := time.Duration(pool.ConnMaxLifetimeSec) * time.Second
	if lifetime <= 0 {
		lifetime = defaultConnMaxLifetime
	}
	idleTime := time.Duration(pool.ConnMaxIdleTimeSec) * time.Second
	if idleTime <= 0 {
		idleTime = defaultConnMaxIdleTime
	}

	// 上限保护：防止 DB 抖动或慢查询时连接数无上限暴涨，进而打满 MySQL max_connections
	d.SetMaxOpenConns(maxOpen)
	// 保留一部分空闲连接，避免频繁 TCP + 鉴权握手
	d.SetMaxIdleConns(maxIdle)
	// 定期回收连接，规避 MySQL wait_timeout / 主从切换 / DNS 漂移导致的死连接
	d.SetConnMaxLifetime(lifetime)
	d.SetConnMaxIdleTime(idleTime)

	log.Logger.Infof("hadb pool setup: maxOpen=%d maxIdle=%d lifetime=%s idleTime=%s",
		maxOpen, maxIdle, lifetime, idleTime)
}

func (db *Database) closeDB() {
	d, err := db.Self.DB()
	if err != nil {
		log.Logger.Error("get db for close failed:%s", err.Error())
		return
	}
	if err := d.Close(); err != nil {
		log.Logger.Error("close db failed:%s", err.Error())
	}
}

// Init TODO
func (db *Database) Init() {
	HADB = &Database{
		Self: InitHaDB(),
	}
	HADB.setupDB()
}

// Close TODO
func (db *Database) Close() {
	HADB.closeDB()
}

// DoCreateDBIfNotExist TODO
func DoCreateDBIfNotExist() error {
	haDBInfo := initc.GlobalConfig.HadbInfo
	connStr := fmt.Sprintf("%s:%s@tcp(%s:%d)/?timeout=5s&readTimeout=10s&writeTimeout=10s",
		haDBInfo.User, haDBInfo.Password, haDBInfo.Host, haDBInfo.Port)
	haDB, err := sql.Open("mysql", connStr)
	if err != nil {
		log.Logger.Infof("exec database/sql failed, err:%s", err.Error())
		return err
	}

	defer haDB.Close()

	databaseStr := fmt.Sprintf("CREATE DATABASE IF NOT EXISTS %s", haDBInfo.Db)
	log.Logger.Infof("database sql:%s", databaseStr)
	_, err = haDB.Exec(databaseStr)
	if err != nil {
		log.Logger.Infof("exec database failed, err:%s", err.Error())
		return err
	}
	log.Logger.Infof("Hadb init db success")
	return nil
}

// DoAutoMigrate do gorm auto migrate
func DoAutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(&HAAgentLogs{}, &HaGMLogs{}, &HaStatus{}, &HASwitchLogs{}, &HASwitchQueue{}, &HAShield{},
		&HABlackWhiteList{})
}

// GenerateGormConfig generate GORM.config
func GenerateGormConfig() *gorm.Config {
	var nowFunc func() time.Time
	switch initc.GlobalConfig.TimezoneInfo.Local {
	case util.TZ_UTC:
		nowFunc = func() time.Time {
			return time.Now().UTC()
		}
	case util.TZ_CST:
		nowFunc = func() time.Time {
			return time.Now().In(time.FixedZone("CST", 8*3600))
		}
	default:
		nowFunc = func() time.Time {
			return time.Now().In(time.FixedZone("CST", 8*3600))
		}
	}

	return &gorm.Config{
		NowFunc: nowFunc,
	}
}
