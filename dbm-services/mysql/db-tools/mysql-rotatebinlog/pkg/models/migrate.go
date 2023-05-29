package models

import (
	"embed"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/sqlite"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

// Migrations TODO
//
//go:embed migrations/*.sql
var Migrations embed.FS

// DoMigrate 从 go embed 文件系统查找 migrations
func DoMigrate(db *sqlx.DB) error {
	var mig *migrate.Migrate
	srcDrv, err := iofs.New(Migrations, "migrations")
	if err != nil {
		return errors.Wrap(err, "sqlite migrations")
	}
	dbDrv, err := sqlite.WithInstance(db.DB, &sqlite.Config{})
	if err != nil {
		return errors.Wrap(err, "sqlite migrate init dbDriver")
	}
	if mig, err = migrate.NewWithInstance("iofs", srcDrv, "", dbDrv); err != nil {
		return errors.Wrap(err, "sqlite migrate new instance")
	} else {
		return mig.Up()
	}
}

// DoMigrateWithNewConn 指定 sqlite db path. dbFile 所在目录必须是一个合法路径
// no changes: return nil
func DoMigrateWithNewConn(dbFile string) error {
	var mig *migrate.Migrate
	// from embed
	if srcDrv, err := iofs.New(Migrations, "migrations"); err != nil {
		return err
	} else {
		dbURL := fmt.Sprintf("sqlite://%s?query", dbFile)
		mig, err = migrate.NewWithSourceInstance("iofs", srcDrv, dbURL)
		if err != nil {
			return errors.WithMessage(err, "migrate from embed")
		}
		if err = mig.Up(); err == nil || err == migrate.ErrNoChange {
			logger.Info("migrate source from embed success with %v", err)
			return nil
		} else {
			logger.Error("migrate source from embed failed: %s", err.Error())
			return err
		}
	}
}
