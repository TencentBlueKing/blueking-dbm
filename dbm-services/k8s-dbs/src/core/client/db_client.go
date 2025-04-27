package client

import (
	"fmt"
	"k8s-dbs/src/config"
	"log"
	"log/slog"
	"os"
	"strconv"
	"time"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

var Db database

type database struct {
	GormDb *gorm.DB
}

type DatabaseConfig struct {
	Host         string        `env:"HOST"`
	Port         int           `env:"PORT"`
	User         string        `env:"USER"`
	Password     string        `env:"PASSWORD"`
	Database     string        `env:"DATABASE"`
	DBName       string        `env:"DBNAME"`
	TLSMode      string        `env:"TLSMODE"`
	MaxOpenConns int           `env:"MAX_OPEN_CONN"`
	MaxIdleConns int           `env:"MAX_IDLE_CONN"`
	MaxLifetime  time.Duration `env:"MAX_LIFETIME"`
	MaxIdleTime  time.Duration `env:"MAX_IDLE_TIME"`
}

func LoadConfig() (*DatabaseConfig, error) {
	cfg := &DatabaseConfig{}
	cfg.Host = os.Getenv("HOST")
	cfg.Port, _ = strconv.Atoi(os.Getenv("PORT"))
	cfg.User = os.Getenv("USER")
	cfg.Password = os.Getenv("PASSWORD")
	cfg.Database = os.Getenv("DATABASE")
	cfg.DBName = os.Getenv("DBNAME")
	cfg.TLSMode = os.Getenv("TLSMODE")
	cfg.MaxOpenConns, _ = strconv.Atoi(os.Getenv("MAX_OPEN_CONN"))
	cfg.MaxIdleConns, _ = strconv.Atoi(os.Getenv("MAX_IDLE_CONN"))
	cfg.MaxLifetime, _ = time.ParseDuration(os.Getenv("MAX_LIFETIME"))
	cfg.MaxIdleTime, _ = time.ParseDuration(os.Getenv("MAX_IDLE_TIME"))
	return cfg, nil
}

func (d *database) Init() error {
	cfg, err := LoadConfig()
	if err != nil {
		slog.Error("Failed to load config", "err", err)
		return err
	}
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local&tls=%s",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.DBName, cfg.TLSMode)
	log.Printf("MySql connector Dsn is %s\n", dsn)
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		slog.Error("Failed to connect to database", "err", err)
		return err
	}
	// 获取底层数据库对象
	sqlDb, err := db.DB()
	if err != nil {
		slog.Error("failed to get database object", "error", err)
		return err
	}

	// 设置数据库连接池参数
	sqlDb.SetMaxOpenConns(cfg.MaxOpenConns)
	sqlDb.SetMaxIdleConns(cfg.MaxIdleConns)
	sqlDb.SetConnMaxLifetime(cfg.MaxLifetime)
	sqlDb.SetConnMaxIdleTime(cfg.MaxIdleTime)

	// Ping 数据库，确认连接
	if err = sqlDb.Ping(); err != nil {
		slog.Error("Failed to ping database", "err", err)
		return err
	} else {
		log.Println("Database connection established")
	}
	Db.GormDb = db
	return nil
}

func (d *database) Init2() error {
	cfg, err := config.LoadConfig("conf/config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local&tls=%s",
		cfg.Database.User, cfg.Database.Password, cfg.Database.Host, cfg.Database.Port, cfg.Database.DBName, cfg.Database.TLSMode)
	fmt.Println(dsn)
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		return err
	}
	Db.GormDb = db
	return nil
}
