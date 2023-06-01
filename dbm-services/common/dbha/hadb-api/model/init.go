package model

import (
	"database/sql"
	"fmt"
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
	err := DoCreateDBIfNotExist()
	if err != nil {
		log.Logger.Errorf("init hadb failed,%s", err.Error())
	}

	haDBInfo := initc.GlobalConfig.HadbInfo
	haDBDsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=%s&parseTime=True&loc=Local",
		haDBInfo.User, haDBInfo.Password, haDBInfo.Host, haDBInfo.Port, haDBInfo.Db, haDBInfo.Charset)
	hadb, err := gorm.Open(mysql.Open(haDBDsn), GenerateGormConfig())
	if err != nil {
		log.Logger.Errorf("connect to %s%d failed:%s", haDBInfo.Host, haDBInfo.Port, err.Error())
	}

	err = DoAutoMigrate(hadb)
	if err != nil {
		log.Logger.Errorf("hadb auto migrate failed, err:%s", err.Error())
	}
	return hadb
}

func (db *Database) setupDB() {
	d, err := db.Self.DB()
	if err != nil {
		log.Logger.Error("get db for setup failed:%s", err.Error())
	}
	d.SetMaxIdleConns(0)
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
}

// Close TODO
func (db *Database) Close() {
	HADB.closeDB()
}

// DoCreateDBIfNotExist TODO
func DoCreateDBIfNotExist() error {
	haDBInfo := initc.GlobalConfig.HadbInfo
	connStr := fmt.Sprintf("%s:%s@tcp(%s:%d)/",
		haDBInfo.User, haDBInfo.Password, haDBInfo.Host, haDBInfo.Port)
	log.Logger.Infof("connect sql:%s", connStr)
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
	return db.AutoMigrate(&DbStatus{}, &HaLogs{}, &HaStatus{}, &SwitchLogs{}, &TbMonSwitchQueue{})
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
