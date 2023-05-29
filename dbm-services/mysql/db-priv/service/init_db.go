package service

import (
	"fmt"
	"log"
	"time"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql" // mysql TODO
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// Database TODO
type Database struct {
	Self *gorm.DB
}

// DB TODO
var DB *Database

// DBVersion56 TODO
var DBVersion56 *Database

// setupDatabase initialize the database tables.
func setupDatabase(db *gorm.DB) {
}

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
	// setup tables
	setupDatabase(db)

	db.LogMode(viper.GetBool("gormlog"))
	db.DB().SetMaxIdleConns(60) // 用于设置闲置的连接数.设置闲置的连接数则当开启的一个连接使用完成后可以放在池里等候下一次使用。
	db.DB().SetMaxOpenConns(200)
	/*
		First of all, you should use DB.SetConnMaxLifetime() instead of wait_timeout.
		Closing connection from client is always better than closing from server,
		because client may send query just when server start closing the connection.
		In such case, client can't know sent query is received or not.
	*/
	db.DB().SetConnMaxLifetime(3600 * time.Second)
}

// initSelfDB TODO
// used for cli
func initSelfDB(dbconfig string) *gorm.DB {
	slog.Info(fmt.Sprintf("%s.%s", dbconfig, "addr"))
	return openDB(viper.GetString(fmt.Sprintf("%s.%s", dbconfig, "username")),
		viper.GetString(fmt.Sprintf("%s.%s", dbconfig, "password")),
		viper.GetString(fmt.Sprintf("%s.%s", dbconfig, "addr")),
		viper.GetString(fmt.Sprintf("%s.%s", dbconfig, "name")))
}

// Init TODO
func (db *Database) Init() {
	DB = &Database{
		Self: initSelfDB("db"),
	}

	DBVersion56 = &Database{
		Self: initSelfDB("generatePswDBVersion56"),
	}

}

// Close TODO
func (db *Database) Close() {
	DB.Self.Close()
	DBVersion56.Self.Close()
}
