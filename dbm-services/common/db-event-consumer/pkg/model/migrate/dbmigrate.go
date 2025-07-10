package migrate

import (
	"embed"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/mysql"
	"github.com/golang-migrate/migrate/v4/source"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
	"github.com/samber/lo"

	"dbm-services/common/db-event-consumer/pkg/sinker"
)

// Migrations embed migrations sqlfile

//go:embed migrations/*.sql
var fs embed.FS

var mysqlMigrations = map[string]string{
	"00001-init.sql": `CREATE TABLE tb_mysql_backup_result () ENGINE=InnoDB DEFAULT CHARSET=utf8;`,
}

// DoMigrateFromMap  do migrate from embed
func DoMigrateFromMap(dsn sinker.InstanceDsn, migTable string) (err error) {
	var mig *migrate.Migrate
	var d source.Driver
	if d, err = NewMapDriver(mysqlMigrations); err != nil {
		return err
	}
	migVars := map[string]interface{}{
		"multiStatements":   "true",
		"interpolateParams": "true",
	}
	sessionVars := lo.Assign(dsn.SessionVariables, migVars)
	db, err := sinker.GetConn(&dsn, sessionVars)
	if err != nil {
		return errors.WithMessage(err, "migrate table structure")
	}
	defer db.Close()
	driver, err := mysql.WithInstance(db, &mysql.Config{
		MigrationsTable: fmt.Sprintf("migrations_%s", migTable),
	})
	if err != nil {
		return err
	}
	mig, err = migrate.NewWithInstance("", d, dsn.Database, driver)
	if err != nil {
		return errors.WithMessage(err, "migrate from embed")
	}

	defer mig.Close()
	if err = mig.Up(); err != nil {
		if err == migrate.ErrNoChange {
			//logger.Info("migrate source from embed success with", "msg", err.Error())
			return nil
		}
		//logger.Error("migrate source from embed failed", err)
		return err
	}
	//logger.Info("migrate source from embed success")
	return nil
}

// DoMigrateFromEmbed  do migrate from embed
func DoMigrateFromEmbed(dsn sinker.InstanceDsn) (err error) {
	var mig *migrate.Migrate
	var d source.Driver
	if d, err = iofs.New(fs, "migrations"); err != nil {
		return err
	}
	migVars := map[string]interface{}{
		"multiStatements":   "true",
		"interpolateParams": "true",
	}
	sessionVars := lo.Assign(dsn.SessionVariables, migVars)
	db, err := sinker.GetConn(&dsn, sessionVars)
	if err != nil {
		return errors.WithMessage(err, "migrate table structure")
	}
	defer db.Close()
	driver, err := mysql.WithInstance(db, &mysql.Config{
		MigrationsTable: "dbm_migrations",
	})
	if err != nil {
		return err
	}
	mig, err = migrate.NewWithInstance("iofs", d, dsn.Database, driver)
	if err != nil {
		return errors.WithMessage(err, "migrate from embed")
	}

	defer mig.Close()
	if err = mig.Up(); err != nil {
		if err == migrate.ErrNoChange {
			//logger.Info("migrate source from embed success with", "msg", err.Error())
			return nil
		}
		//logger.Error("migrate source from embed failed", err)
		return err
	}
	//logger.Info("migrate source from embed success")
	return nil
}
