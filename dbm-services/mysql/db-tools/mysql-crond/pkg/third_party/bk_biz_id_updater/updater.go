package bk_biz_id_updater

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"errors"
	"log/slog"
	"os"

	"github.com/robfig/cron/v3"
	"gopkg.in/yaml.v2"
)

func Register(cj *cron.Cron) {
	id, err := cj.AddFunc(
		"@every 10m",
		func() {
			err := Updater()
			if err != nil {
				slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
			} else {
				slog.Info("bk_biz_id updater job finished")
			}
		},
	)
	if err != nil {
		slog.Error("register bk_biz_id updater job", slog.String("err", err.Error()))
	} else {
		slog.Info("register bk_biz_id updater job success", slog.Int("entry id", int(id)))
	}
}

func Updater() error {
	bkBizId, err := pkg.GetBkBizId()
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}

	content, err := os.ReadFile(config.RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return err
	}

	err = yaml.Unmarshal(content, &config.JobsConfig)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return err
	}

	config.JobsConfig.BkBizId = bkBizId

	content, err = yaml.Marshal(config.JobsConfig)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return err
	}

	err = os.WriteFile(config.RuntimeConfig.JobsConfigFile, content, 0644)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return err
	}
	return nil
}
