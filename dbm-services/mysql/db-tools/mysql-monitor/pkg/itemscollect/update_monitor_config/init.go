package update_monitor_config

import (
	"dbm-services/common/reverseapi"
	"dbm-services/common/reverseapi/define/mysql"
	acst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"slices"

	"github.com/gofrs/flock"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var name = "update-monitor-config"

type Checker struct {
}

func (c *Checker) Run() (msg string, err error) {
	sii, err := c.getSelfInfo()
	if err != nil {
		return "", err
	}
	slog.Info(name, slog.Any("sii", sii))

	err = c.updateConfigFile(sii)
	if err != nil {
		return "", err
	}

	return "", nil
}

func (c *Checker) updateConfigFile(sii *mysql.StorageInstanceInfo) (err error) {
	configFilePath := viper.GetString("hard-run-config")
	if !filepath.IsAbs(configFilePath) {
		cwd, err := os.Getwd()
		if err != nil {
			slog.Error(name, slog.String("err", err.Error()))
			return err
		}

		configFilePath = filepath.Join(cwd, configFilePath)
	}

	lockFileName := fmt.Sprintf("%s.lock", filepath.Base(configFilePath))

	lockFileBasePath := filepath.Join(acst.MySQLMonitorInstallPath, "locks")
	err = os.MkdirAll(lockFileBasePath, os.ModePerm)
	if err != nil {
		slog.Error(
			name,
			slog.String("dir", lockFileBasePath),
			slog.String("err", err.Error()),
		)
		return err
	}
	lockFilePath := filepath.Join(lockFileBasePath, lockFileName)
	fl := flock.New(lockFilePath)

	// 排他锁
	err = fl.Lock()
	if err != nil {
		slog.Error(
			name,
			slog.String("dir", lockFilePath),
			slog.String("err", err.Error()),
		)
		return err
	}
	defer func() {
		_ = fl.Unlock()
	}()
	slog.Info(
		name,
		slog.String("lock", lockFilePath),
	)

	slog.Info(name, slog.Any("monitor config before", config.MonitorConfig))
	config.MonitorConfig.Role = &sii.InstanceInnerRole
	slog.Info(name, slog.Any("monitor config after", config.MonitorConfig))
	//config.MonitorConfig.ImmuteDomain = sii.ImmuteDomain

	b, err := yaml.Marshal(config.MonitorConfig)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
			slog.Any("config", config.MonitorConfig),
		)
		return err
	}

	cf, err := os.OpenFile(configFilePath, os.O_TRUNC|os.O_RDWR|os.O_CREATE, os.ModePerm)
	if err != nil {
		slog.Error(name, slog.String("err", err.Error()))
		return err
	}

	_, err = cf.WriteString(string(b) + "\n")
	if err != nil {
		slog.Error(name, slog.String("err", err.Error()))
		return err
	}
	slog.Info(name, slog.String("config", string(b)))
	return nil
}

func (c *Checker) getSelfInfo() (sii *mysql.StorageInstanceInfo, err error) {
	filePath := filepath.Join(
		reverseapi.DefaultCommonConfigDir,
		reverseapi.DefaultNginxProxyAddrsFileName,
	)
	f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
			slog.String("filePath", filePath),
		)
		return nil, err
	}

	b, err := io.ReadAll(f)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	var siis []mysql.StorageInstanceInfo
	err = json.Unmarshal(b, &siis)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	idx := slices.IndexFunc(siis, func(ele mysql.StorageInstanceInfo) bool {
		return ele.Ip == config.MonitorConfig.Ip && ele.Port == config.MonitorConfig.Port
	})
	if idx < 0 {
		err := fmt.Errorf("can't find %s:%d in %v", config.MonitorConfig.Ip, config.MonitorConfig.Port, siis)
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	return &siis[idx], nil
}

func (c *Checker) Name() string {
	return name
}
