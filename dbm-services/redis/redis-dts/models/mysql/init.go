package mysql

import (
	"fmt"
	"log"
	"time"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql" // mysql TODO
	"github.com/spf13/viper"
)

// Database 连接MySQL
type Database struct {
	Gcs    *gorm.DB
	Tendis *gorm.DB
}

// DB TODO
var DB *Database

func openDB(username, password, addr, name string) *gorm.DB {
	config := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8&parseTime=%t&loc=%s",
		username,
		password,
		addr,
		name,
		true,
		// "Asia/Shanghai"),
		"Local")

	db, err := gorm.Open("mysql", config)
	if err != nil {
		log.Fatalf("Database connection failed. Database name: %s, error: %v", name, err)
	}

	// set for db connection
	setupDB(db)

	return db
}

func setupDB(db *gorm.DB) {
	db.LogMode(viper.GetBool("gormlog"))
	// 用于设置最大打开的连接数，默认值为0表示不限制.设置最大的连接数，可以避免并发太高导致连接mysql出现too many connections的错误。
	// db.DB().SetMaxOpenConns(20000)
	maxIdleConns := viper.GetInt("max_idle_conns")
	maxOpenConn := viper.GetInt("max_open_conns")
	maxLifeTime := viper.GetInt("max_life_time")

	db.DB().SetMaxOpenConns(maxOpenConn)
	// 用于设置闲置的连接数.设置闲置的连接数则当开启的一个连接使用完成后可以放在池里等候下一次使用
	db.DB().SetMaxIdleConns(maxIdleConns)
	// fix gorm invalid connect bug,参考问题:https://studygolang.com/topics/5576
	db.DB().SetConnMaxLifetime(time.Duration(maxLifeTime) * time.Hour)
}

// InitGcsDB 初始化 GCS DB
func InitGcsDB() *gorm.DB {
	return openDB(viper.GetString("gcs_db.username"),
		viper.GetString("gcs_db.password"),
		viper.GetString("gcs_db.addr"),
		viper.GetString("gcs_db.name"))
}

// GetGcsDB ..
func GetGcsDB() *gorm.DB {
	return InitGcsDB()
}

// InitTendisDB 初始化TendisDB
func InitTendisDB() *gorm.DB {
	return openDB(viper.GetString("tendis_db.username"),
		viper.GetString("tendis_db.password"),
		viper.GetString("tendis_db.addr"),
		viper.GetString("tendis_db.name"))
}

// GetTendisDB ..
func GetTendisDB() *gorm.DB {
	return InitTendisDB()
}

// Init 初始化MySQL连接
func (db *Database) Init() {
	DB = &Database{
		// Gcs:    GetGcsDB(),
		Tendis: GetTendisDB(),
	}
}

// Close 关闭MySQL连接
func (db *Database) Close() {
	// DB.Gcs.Close()
	DB.Tendis.Close()
}
