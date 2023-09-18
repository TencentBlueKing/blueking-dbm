package repository

import (
	"fmt"
	"time"

	"bk-dbconfig/assets"
	"bk-dbconfig/internal/repository/migratespec"
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
	if d, err := iofs.New(assets.Migrations, "migrations"); err != nil {
		return err
	} else {
		if err = reMigrateConfigPlat(); err != nil {
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
		// 获取当前 migrate version，如果<=2，则要 migrate 敏感信息(step=3)
		var versionLast uint
		if versionLast, _, err = mig.Version(); err == migrate.ErrNilVersion {
			versionLast = 0
		} else if err != nil {
			logger.Warn("fail to get current migrate version")
		}
		logger.Info("current migrate version: %d", versionLast)

		if versionLast < migratespec.SensitiveMigVer-1 {
			if err = mig.Migrate(migratespec.SensitiveMigVer - 1); err == nil || err == migrate.ErrNoChange {
				logger.Info("migrate schema success with %v", err)
			} else {
				return errors.WithMessage(err, "migrate schema")
			}
		}
		// migrate 到最新
		if err = mig.Up(); err == nil || err == migrate.ErrNoChange {
			logger.Info("migrate data from embed success with %v", err)

			if versionLast < migratespec.SensitiveMigVer {
				logger.Info("migrate sensitive info for the first time")
				db := model.InitSelfDB("")
				defer func() {
					dbc, _ := db.DB()
					dbc.Close()
				}()
				if err = migratespec.MigrateSensitive(db); err != nil {
					logger.Errorf("fail to migrate sensitive: %s", err.Error())
					return mig.Migrate(migratespec.SensitiveMigVer - 1)
					//return errors.WithMessage(err, "migrate sensitive")
				}
				logger.Info("migrate sensitive success with %v", err)
			}

			return nil
		} else {
			logger.Errorf("migrate data from embed failed: %s", err.Error())
			logger.Warn("sleep 120s to return. " +
				"you may need ./bkconfigsvr --migrate --migrate-force=VersionNo after you fix it")
			time.Sleep(120 * time.Second)
			return err
		}
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

// reMigrateConfigPlat 重新初始化 平台级默认 配置数据
func reMigrateConfigPlat() error {
	db, err := model.InitSelfDB("multiStatements=true&interpolateParams=true").DB()
	if err != nil {
		return errors.WithMessage(err, "reMigrate connect failed")
	}
	defer db.Close()
	sqlStrs := []string{
		fmt.Sprintf("update schema_migrations set version=%d,dirty=0 where version >%d",
			migratespec.SensitiveMigVer, migratespec.SensitiveMigVer), // step 3 is sensitive mig
		"delete from tb_config_file_def",
		"delete from tb_config_name_def where flag_encrypt!=1 or value_default like '{{%'",
	}

	for i, sql := range sqlStrs {
		if i == 0 {
			if _, err := db.Exec(sql); err != nil {
				// 更新 migrate 元数据失败，退出，同时忽略本次 reMigrate 动作
				return nil
			}
			logger.Warnf("reset migrate to %d", migratespec.SensitiveMigVer)
		} else {
			if _, err = db.Exec(sql); err != nil {
				return errors.WithMessage(err, "reMigrate failed")
			}
		}
	}
	return nil
}
