package instance_info_updater

import (
	"dbm-services/common/reverseapi"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"log/slog"
	"math/rand"
	"os"
	"path/filepath"
	"time"

	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"
)

func Register(cj *cron.Cron) {
	id, err := cj.AddFunc(
		"@every 30m",
		func() {
			err := updater()
			if err != nil {
				slog.Error("update instance info job", slog.String("err", err.Error()))
			} else {
				slog.Info("update instance info job finished")
			}
		},
	)
	if err != nil {
		slog.Error("register instance info updater job", slog.String("err", err.Error()))
	} else {
		slog.Info("register instance info updater job success", slog.Int("entry id", int(id)))
	}
}

func updater() error {
	sleepN := time.Second * time.Duration(rand.Intn(120))
	slog.Info("rand sleep", slog.Float64("seconds", sleepN.Seconds()))
	time.Sleep(sleepN)
	slog.Info("rand sleep awake")

	return Updater()
}

func Updater() error {
	rvApi, err := reverseapi.NewReverseApi(int64(*config.RuntimeConfig.BkCloudID))
	if err != nil {
		slog.Error("create reverse api", slog.String("err", err.Error()))
		return err
	}

	slog.Info("call reverse api", slog.Any("runtime config", config.RuntimeConfig))
	info, layer, err := rvApi.MySQL.ListInstanceInfo()
	if err != nil {
		slog.Error("list instance info failed", slog.String("err", err.Error()))
		return errors.Wrap(err, "list instance info failed")
	}
	slog.Info(
		"list instance info",
		slog.Any("info", info),
		slog.String("layer", layer),
	)

	f, err := os.OpenFile(
		filepath.Join(reverseapi.DefaultCommonConfigDir, reverseapi.DefaultInstanceInfoFileName),
		os.O_TRUNC|os.O_CREATE|os.O_WRONLY, 0777,
	)
	if err != nil {
		return errors.Wrap(err, "open instance info file failed")
	}
	defer func() {
		_ = f.Close()
	}()
	slog.Info("update instance info recreate file success")

	if _, err := f.WriteString(string(info) + "\n"); err != nil {
		slog.Error("write instance info failed", slog.String("err", err.Error()))
		return errors.Wrap(err, "write instance info failed")
	}
	slog.Info("update instance info recreate file success")
	return nil
}
