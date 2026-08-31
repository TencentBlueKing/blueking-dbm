package update_monitor_config

import (
	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/define/mysql"
	acst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"time"

	"github.com/gofrs/flock"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var name = "update-monitor-config"

type Checker struct {
}

func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	err = checkOutOfDate()
	if err != nil {
		slog.Error("check out of date", slog.String("err", err.Error()))
		return nil, "", err
	}

	// 目前只更新 monitor config
	// item config 还要等等
	switch config.MonitorConfig.MachineType {
	case "mysql_dts_master", "mysql_dts_worker":
		return nil, "", nil
	case "backend", "remote", "single":
		selfInfo, err := c.GetSelfInfoStorage()
		if err != nil {
			return nil, "", err
		}
		slog.Info(name, slog.Any("self info storage", selfInfo))
		err = c.updateConfigFile(selfInfo)
		if err != nil {
			return nil, "", err
		}

	default:
		// spider, proxy 暂时不自动更新
		return nil, "", nil
	}
	return nil, "", nil
}

func checkOutOfDate() (err error) {
	for _, fn := range []string{
		define.DefaultInstanceInfoFileName,
		define.DefaultNginxProxyAddrsFileName,
	} {
		fp := filepath.Join(define.DefaultCommonConfigDir, fn)
		st, e := os.Stat(fp)
		if e != nil {
			errors.Join(err, e)
		}

		mtime := st.ModTime()
		if mtime.Before(time.Now().Add(-24 * time.Hour)) {
			errors.Join(err, fmt.Errorf("%s is out of date", fn))
		}
	}
	return
}

func (c *Checker) updateConfigFile(sii *mysql.StorageInstanceInfo) (err error) {
	configFilePath := viper.GetString("hard-run-config")
	if configFilePath == "" {
		configFilePath = viper.GetString("run-config")
	}
	if configFilePath == "" {
		return errors.New("config file path is empty")
	}

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
	defer func() {
		_ = cf.Close()
	}()

	_, err = cf.WriteString(string(b) + "\n")
	if err != nil {
		slog.Error(name, slog.String("err", err.Error()))
		return err
	}
	slog.Info(name, slog.String("config", string(b)))

	//configFileDir, configFileName := filepath.Split(configFilePath)
	//err = utils.Reschedule(configFileDir, configFileName, "monitor")
	//
	//if err != nil {
	//	slog.Error(name, slog.String("err", err.Error()))
	//	return err
	//}

	return nil
}

func (c *Checker) readInstanceInfoContent() (b []byte, err error) {
	filePath := filepath.Join(
		define.DefaultCommonConfigDir,
		define.DefaultInstanceInfoFileName,
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
	defer func() {
		_ = f.Close()
	}()

	b, err = io.ReadAll(f)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}
	return b, nil
}

func (c *Checker) getSelfInfoProxy() (pii *mysql.ProxyInstanceInfo, err error) {
	b, err := c.readInstanceInfoContent()
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	var piis []mysql.ProxyInstanceInfo
	err = json.Unmarshal(b, &piis)
	if err != nil {
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	idx := slices.IndexFunc(
		piis, func(ele mysql.ProxyInstanceInfo) bool {
			return ele.Ip == config.MonitorConfig.Ip && ele.Port == config.MonitorConfig.Port
		},
	)
	if idx < 0 {
		err := fmt.Errorf("can't find %s:%d in %v", config.MonitorConfig.Ip, config.MonitorConfig.Port, piis)
		slog.Error(
			name,
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	return &piis[idx], nil
}

func (c *Checker) GetSelfInfoStorage() (sii *mysql.StorageInstanceInfo, err error) {
	b, err := c.readInstanceInfoContent()
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

	idx := slices.IndexFunc(
		siis, func(ele mysql.StorageInstanceInfo) bool {
			return ele.Ip == config.MonitorConfig.Ip && ele.Port == config.MonitorConfig.Port
		},
	)
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
