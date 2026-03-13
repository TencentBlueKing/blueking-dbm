package repository

import (
	"fmt"

	"bk-dbconfig/assets"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/core/logger"

	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/mysql"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
)

// DoMigrateFromEmbed 先尝试从 go embed 文件系统查找 migrations
// no changes: return nil
func DoMigrateFromEmbed() error {
	var mig *migrate.Migrate
	// from embed
	d, err := iofs.New(assets.Migrations, "migrations")
	if err != nil {
		return err
	}
	dbURL := fmt.Sprintf(
		"mysql://%s:%s@tcp(%s)/%s?charset=%s&parseTime=true&loc=Local&multiStatements=true&interpolateParams=true",
		config.GetString("db.username"),
		config.GetString("db.password"),
		config.GetString("db.addr"),
		config.GetString("db.name"),
		"utf8",
	)
	mig, err = migrate.NewWithSourceInstance("iofs", d, dbURL)
	if err != nil {
		return errors.WithMessage(err, "migrate from embed")
	}
	defer mig.Close()
	// 获取当前 migrate version，如果<=7，则要 migrate 敏感信息(step=8)
	var versionLast uint
	if versionLast, _, err = mig.Version(); err == migrate.ErrNilVersion {
		versionLast = 0
	} else if err != nil {
		logger.Warn("fail to get current migrate version")
	}
	logger.Info("current migrate version: %d", versionLast)

	// migrate 到最新
	if err = mig.Up(); err == nil || err == migrate.ErrNoChange {
		logger.Info("migrate data from embed success with %v", err)
		return nil
	} else {
		logger.Errorf("migrate data from embed failed: %s", err.Error())
		return err
	}
}

// DoMigrateFromSource 根据指定的 source 进行 db migrate
func DoMigrateFromSource() error {
	db, err := model.InitSelfDB("multiStatements=true&interpolateParams=true").DB()
	if err != nil {
		return err
	}
	defer db.Close()
	var mig *migrate.Migrate
	driver, err := mysql.WithInstance(db, &mysql.Config{})
	if err != nil {
		return err
	}
	source := config.GetString("migrate.source")
	if source == "" {
		return errors.New("db migrate need source_url")
	}
	// from config migrate.source
	if mig, err = migrate.NewWithDatabaseInstance(source, config.GetString("db.name"), driver); err != nil {
		return err
	} else {
		forceVersion := config.GetInt("migrate.force")
		if forceVersion != 0 {
			return mig.Force(forceVersion)
		}
		return mig.Up()
	}
}
