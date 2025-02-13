package nginx_updater

import (
	"dbm-services/common/reverse-api/apis/common"
	rconfig "dbm-services/common/reverse-api/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"log/slog"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
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
				slog.Error("update nginx addrs job", slog.String("err", err.Error()))
			} else {
				slog.Info("update nginx addrs job finished")
			}
		},
	)
	if err != nil {
		slog.Error("register nginx addrs job", slog.String("err", err.Error()))
	} else {
		slog.Info("register nginx addrs job success", slog.Int("entry id", int(id)))
	}
}

func updater() error {
	err := os.MkdirAll(rconfig.CommonConfigDir, 0777)
	if err != nil {
		return errors.Wrap(err, "can't create config directory")
	}

	sleepN := time.Second * time.Duration(rand.Intn(120))
	slog.Info("rand sleep", slog.Float64("seconds", sleepN.Seconds()))
	time.Sleep(sleepN)
	slog.Info("rand sleep awake")

	addrs, err := common.ListNginxAddrs(*config.RuntimeConfig.BkCloudID)
	if err != nil {
		return errors.Wrap(err, "list nginx addrs failed")
	}
	slog.Info("list nginx addrs", slog.String("addrs", strings.Join(addrs, ",")))

	f, err := os.OpenFile(
		filepath.Join(rconfig.CommonConfigDir, rconfig.NginxProxyAddrsFileName),
		os.O_TRUNC|os.O_CREATE|os.O_WRONLY,
		0777,
	)
	if err != nil {
		return errors.Wrap(err, "open nginx addrs failed")
	}
	defer func() {
		_ = f.Close()
	}()
	slog.Info("update nginx addrs recreate addr file success")

	for _, addr := range addrs {
		if _, err := f.WriteString(addr + "\n"); err != nil {
			return errors.Wrap(err, "write nginx addrs failed")
		}
	}
	slog.Info("update nginx addrs write addr file success")

	return nil
}
