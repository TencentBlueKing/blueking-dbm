package assests

import (
	"embed"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/mysql" // mysql TODO
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

//go:embed migrations/*.sql
var fs embed.FS

// DoMigrateFromEmbed 先尝试从 go embed 文件系统查找 migrations
// no changes: return nil
func DoMigrateFromEmbed() error {
	var mig *migrate.Migrate
	if d, err := iofs.New(fs, "migrations"); err != nil {
		return err
	} else {
		dbURL := fmt.Sprintf(
			"mysql://%s:%s@tcp(%s:%d)/%s?charset=%s&parseTime=true&loc=Local&multiStatements=true&interpolateParams=true",
			viper.GetString("db.user"),
			viper.GetString("db.password"),
			viper.GetString("db.host"),
			viper.GetInt("db.port"),
			viper.GetString("db.name"),
			"utf8",
		)
		mig, err = migrate.NewWithSourceInstance("iofs", d, dbURL)
		if err != nil {
			return errors.WithMessage(err, "migrate from embed")
		}
		defer mig.Close()
		err = mig.Up()
		if err == nil {
			slog.Info("migrate source from embed success")
			return nil
		} else if err == migrate.ErrNoChange {
			slog.Info("migrate source from embed success with", "msg", err.Error())
			return nil
		} else {
			slog.Error("migrate source from embed failed", err)
			return err
		}
	}
}
