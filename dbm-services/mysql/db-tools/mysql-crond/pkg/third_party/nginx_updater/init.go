package nginx_updater

import (
	"dbm-services/common/reverse-api/apis/common"
	rconfig "dbm-services/common/reverse-api/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"log/slog"
	"os"
	"path/filepath"

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

	addrs, err := common.ListNginxAddrs(*config.RuntimeConfig.BkCloudID)
	if err != nil {
		return errors.Wrap(err, "list nginx addrs failed")
	}

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

	for _, addr := range addrs {
		if _, err := f.WriteString(addr + "\n"); err != nil {
			return errors.Wrap(err, "write nginx addrs failed")
		}
	}

	return nil
}
