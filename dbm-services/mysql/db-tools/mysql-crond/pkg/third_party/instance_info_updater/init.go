package instance_info_updater

import (
	"log/slog"
	"math/rand"
	"os"
	"path/filepath"
	"time"

	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/pkg/core"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/gofrs/flock"
	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"
)

func Register(cj *cron.Cron) {
	id, err := cj.AddFunc(
		"@every 10m",
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
	slog.Info("call reverse api", slog.Any("runtime config", config.RuntimeConfig))
	return DoUpdate(int64(*config.RuntimeConfig.BkCloudID))
}

func DoUpdate(bkCloudId int64) error {
	lkfp := filepath.Join(cst.MySQLCrondInstallPath, "instance-info-updater.lock")
	fl := flock.New(lkfp)
	defer func() {
		_ = fl.Unlock()
	}()

	err := fl.Lock()
	if err != nil {
		slog.Error("lock failed", slog.String("err", err.Error()))
		return err
	}

	apiCore, err := core.NewCore(bkCloudId, core.DefaultRetryOpts...)
	if err != nil {
		slog.Error("create api core", slog.String("err", err.Error()))
		return err
	}

	info, layer, err := reversemysqlapi.ListInstanceInfo(apiCore)
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
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultInstanceInfoFileName),
		os.O_TRUNC|os.O_CREATE|os.O_WRONLY, 0777,
	)
	if err != nil {
		return errors.Wrap(err, "open instance info file failed")
	}
	defer func() {
		_ = f.Close()
	}()

	if _, err := f.WriteString(string(info) + "\n"); err != nil {
		slog.Error("write instance info failed", slog.String("err", err.Error()))
		return errors.Wrap(err, "write instance info failed")
	}
	return nil
}
