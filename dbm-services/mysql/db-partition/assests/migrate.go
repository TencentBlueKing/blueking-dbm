package assests

import (
	"database/sql"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/service"
	"embed"
	"fmt"
	"log/slog"

	"github.com/golang-migrate/migrate/v4"
	migrateMySQL "github.com/golang-migrate/migrate/v4/database/mysql"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
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
		// 使用 DSN 格式建立连接，避免密码中的特殊字符（如 %、@）在 URL 格式中被错误解析
		dsn := fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/%s?charset=utf8&parseTime=true&loc=Local&multiStatements=true&interpolateParams=true",
			viper.GetString("db.user"),
			viper.GetString("db.password"),
			viper.GetString("db.host"),
			viper.GetInt("db.port"),
			viper.GetString("db.name"),
		)
		sqlDB, err := sql.Open("mysql", dsn)
		if err != nil {
			return errors.WithMessage(err, "open db for migrate")
		}
		dbDriver, err := migrateMySQL.WithInstance(sqlDB, &migrateMySQL.Config{})
		if err != nil {
			sqlDB.Close()
			return errors.WithMessage(err, "create migrate db driver")
		}
		mig, err = migrate.NewWithInstance("iofs", d, "mysql", dbDriver)
		if err != nil {
			sqlDB.Close()
			return errors.WithMessage(err, "migrate from embed")
		}
		defer mig.Close()
		err = mig.Up()
		if err == nil {
			slog.Info("migrate source from embed success")
		} else if err == migrate.ErrNoChange {
			slog.Info("migrate source from embed success with", "msg", err.Error())
		} else {
			slog.Error("migrate source from embed failed", err)
			return err
		}
		// 版本4添加了字段，需要在migrate后填充字段值
		version, dirty, errInner := mig.Version()
		if errInner == nil && version == 5 && dirty == false {
			err = PaddingDbAppAbbr()
			if err != nil {
				return fmt.Errorf("padding db_app_abbr for partition config error after migration version 5")
			}
		}
		return nil
	}
}

// PaddingDbAppAbbr 填充migrate version 4 新增的db_app_abbr、bk_biz_name字段
func PaddingDbAppAbbr() error {
	bizs, err := service.ListBizs()
	if err != nil {
		return fmt.Errorf("从dbm list_bizs获取业务列表失败: %s", err.Error())
	}
	tx := model.DB.Self.Begin()
	// 对于已存在的分区配置，根据bk_biz_id更新其db_app_abbr、bk_biz_name字段
	for _, biz := range bizs {
		errInner := tx.Exec(fmt.Sprintf("update %s set db_app_abbr='%s',bk_biz_name='%s' where "+
			"db_app_abbr='' and bk_biz_id=%d", service.MysqlPartitionConfig,
			biz.EnglishName, biz.Name, biz.BkBizId)).Error
		if errInner != nil {
			tx.Rollback()
			return errInner
		}
		errInner = tx.Exec(fmt.Sprintf("update %s set db_app_abbr='%s',bk_biz_name='%s' where "+
			"db_app_abbr='' and bk_biz_id=%d", service.SpiderPartitionConfig,
			biz.EnglishName, biz.Name, biz.BkBizId)).Error
		if errInner != nil {
			tx.Rollback()
			return errInner
		}
	}
	tx.Commit()
	return nil
}
