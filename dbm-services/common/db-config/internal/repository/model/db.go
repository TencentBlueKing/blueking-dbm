package model

import (
	"database/sql"
	"fmt"
	"log"
	"strconv"
	"time"

	"github.com/spf13/viper"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/core/config"
)

// Database TODO
type Database struct {
	Self *gorm.DB
	// DBV1 *gorm.DB
}

// DB TODO
var DB *Database

// Connection TODO
// DB
type Connection struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
	// User   string `json:"user"`
	// Pwd    string `json:"pwd"`
	DBName string `json:"dbName"`
}

// migrateDatabase initialize the database tables.
func migrateDatabase(db *gorm.DB) {
	// db.AutoMigrate(&UserModel{})
	// db.AutoMigrate(&RoleModel{})
}

/*
 cleanDatabase tear downs the database tables.
func cleanDatabase(db *gorm.DB) {
    //db.DropTable(&UserModel{})
    //db.DropTable(&RoleModel{})
}


// resetDatabase resets the database tables.
func resetDatabase(db *gorm.DB) {
    //cleanDatabase(db)
    migrateDatabase(db)
}
*/

// openDB godoc
// options="multiStatements=true&interpolateParams=true"
func openDB(username, password, addr, name string, options string) *gorm.DB {
	// multiStatements
	dsn := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8&parseTime=%t&loc=%s",
		username,
		password,
		addr,
		name,
		true,
		// "Asia/Shanghai"),
		"Local")
	if options != "" {
		dsn += "&" + options
	}
	// log.Printf("connect string: %s", dsn)
	sqlDB, err := sql.Open("mysql", dsn)
	db, err := gorm.Open(mysql.New(mysql.Config{Conn: sqlDB}), &gorm.Config{})
	if err != nil {
		log.Fatalf("Database connection failed. Database name: %s, error: %v", name, err)
	}

	// set for db connection
	setupDB(db)
	return db
}

func setupDB(db *gorm.DB) {
	// setup tables
	sqlDB, err := db.DB()
	if err != nil {
		log.Fatalf("setupDB failed: %s", err.Error())
		return
	}
	migrateDatabase(db)
	// sqlDB.LogMode(viper.GetBool("gormlog"))
	// 用于设置闲置的连接数.设置闲置的连接数则当开启的一个连接使用完成后可以放在池里等候下一次使用。
	sqlDB.SetMaxIdleConns(viper.GetInt("dbConnConf.maxIdleConns"))
	// 用于设置最大打开的连接数，默认值为0表示不限制.设置最大的连接数，可以避免并发太高导致连接mysql出现too many connections的错误。
	sqlDB.SetMaxOpenConns(viper.GetInt("dbConnConf.maxOpenConns"))
	sqlDB.SetConnMaxLifetime(time.Duration(viper.GetInt("dbConnConf.connMaxLifetime")) * time.Hour)
}

// InitSelfDB 获取 gorm.DB 对象
func InitSelfDB(options string) *gorm.DB {
	log.Println(config.GetString("db.username"), "****", config.GetString("db.addr"),
		config.GetString("db.name"))
	return openDB(config.GetString("db.username"),
		config.GetString("db.password"),
		config.GetString("db.addr"),
		config.GetString("db.name"),
		options)
}

func getTestDB() *gorm.DB {
	return openDB(config.GetString("testdb.name"),
		config.GetString("testdb.password"),
		config.GetString("testdb.addr"),
		config.GetString("testdb.name"), "")
}

// GetSelfDB 返回原生 sql.DB 对象
func GetSelfDB() *sql.DB {
	sqlDB, _ := DB.Self.DB()
	return sqlDB
}

// Init TODO
func (db *Database) Init() {
	DB = &Database{
		Self: InitSelfDB(""),
		// DBV1: getDBV1(),
	}
}

// Close TODO
func (db *Database) Close() {
	sqlDB, err := DB.Self.DB()
	if err == nil {
		sqlDB.Close()
	}
	// DB.DBV1.Close()
}

// GetDBconn TODO
func GetDBconn(connParam Connection) *gorm.DB {
	address := connParam.IP + ":" + strconv.Itoa(connParam.Port)
	if connParam.DBName == "" {
		connParam.DBName = "information_schema"
	}
	return openDB(config.GetString("monitor.username"),
		config.GetString("monitor.password"),
		address,
		connParam.DBName, "")
}

// GetProxyconn TODO
func GetProxyconn(username, password, addr, name string) *gorm.DB {
	if username == "" {
		username = config.GetString("proxy.username")
	}
	if password == "" {
		password = config.GetString("proxy.password")
	}
	return openDB(username, password, addr, name, "")
}
