package handler

import (
	"fmt"

	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"

	"golang.org/x/exp/slog"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func NewHandler() (*RegisterHandler, error) {
	tz := "loc=UTC&time_zone=%27%2B00%3A00%27" // we use UTC to get and set
	dsn := fmt.Sprintf(
		`%s:%s@tcp(%s)/%s?charset=%s&parseTime=True&%s`,
		config.RuntimeConfig.Dsn.User,
		config.RuntimeConfig.Dsn.Password,
		config.RuntimeConfig.Dsn.Address,
		config.RuntimeConfig.Dsn.Database,
		config.RuntimeConfig.Dsn.Charset,
		tz,
	)

	db, err := gorm.Open(
		mysql.New(
			mysql.Config{
				DSN: dsn,
			},
		),
		&gorm.Config{},
	)
	if err != nil {
		slog.Error("connect db", err)
		return nil, err
	}

	sqlDB, err := db.DB()
	if err != nil {
		slog.Error("get sql db", err)
		return nil, err
	}
	sqlDB.SetMaxOpenConns(config.RuntimeConfig.Dsn.ConnectionPerPartition)
	sqlDB.SetMaxIdleConns(2 * config.RuntimeConfig.Dsn.ConnectionPerPartition)
	sqlDB.SetConnMaxLifetime(0)

	return &RegisterHandler{Db: db, Ready: make(chan bool)}, nil
}
