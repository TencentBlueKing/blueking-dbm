// Package model TODO
package model

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	"dbm-services/mysql/db-simulation/app/config"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// DB TODO
var DB *gorm.DB

// SqlDB TODO
var SqlDB *sql.DB

func init() {
	user := config.GAppConfig.DbConf.User
	pwd := config.GAppConfig.DbConf.Pwd
	addr := fmt.Sprintf("%s:%d", config.GAppConfig.DbConf.Host, config.GAppConfig.DbConf.Port)
	db := config.GAppConfig.DbConf.Name
	log.Printf("connect to %s", addr)
	testConn := openDB(user, pwd, addr, "")
	err := testConn.Exec(fmt.Sprintf("create database IF NOT EXISTS `%s`;", db)).Error
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb, err := testConn.DB()
	if err != nil {
		log.Fatalf("init create db failed:%s", err.Error())
	}
	sqldb.Close()
	DB = openDB(user, pwd, addr, db)
	Migration()
}

// Migration TODO
func Migration() {
	DB.AutoMigrate(&TbSimulationTask{}, &TbRequestRecord{}, &TbSyntaxRule{})
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
	// SqlDB是上面定义了全局变量
	SqlDB, err = sql.Open("mysql", dsn)
	if err != nil {
		log.Fatalf("connect to mysql failed %s", err.Error())
		return nil
	}
	db, err := gorm.Open(mysql.New(mysql.Config{
		Conn: SqlDB,
	}), &gorm.Config{
		DisableForeignKeyConstraintWhenMigrating: true,
		Logger:                                   newLogger,
	})

	if err != nil {
		log.Fatalf("Database connection failed. Database name: %s, error: %v", name, err)
	}
	return db
}
