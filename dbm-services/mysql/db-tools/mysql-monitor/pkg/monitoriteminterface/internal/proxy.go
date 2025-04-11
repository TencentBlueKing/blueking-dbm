package internal

import (
	mrapi "dbm-services/common/reverse-api/apis/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"errors"

	"github.com/go-sql-driver/mysql"
	"github.com/gofrs/flock"
	"github.com/jmoiron/sqlx"
)

func ConnectProxy() (pdb *sqlx.DB, padb *sqlx.DB, err error) {
	// 服务端口连接失败做重启尝试
	pdb, err = connectProxy()
	if err != nil {
		if (config.MonitorConfig.AutoRestartInstance != nil &&
			*config.MonitorConfig.AutoRestartInstance) &&
			(strings.Contains(err.Error(), "invalid connection") ||
				strings.Contains(err.Error(), "connection refused")) {
			slog.Info("connect proxy service port failed try to reboot", slog.String("err", err.Error()))
			return retryAndRestartProxy()
		}
		slog.Error(
			"connect proxy failed skip reboot",
			slog.String("err", err.Error()),
		)
		return nil, nil, err
	}

	// 管理端口连接失败只告警
	padb, err = connectProxyAdmin()
	return pdb, padb, err

}

// 第一次连接失败进入排他重试阶段
// 先尝试重连, 失败则拉起进场, 再尝试连接
// 为了防止不同周期的监控同时操作, 这里按端口文件锁排他
func retryAndRestartProxy() (pdb *sqlx.DB, padb *sqlx.DB, err error) {
	fl, err := addExLock()
	if err != nil {
		return nil, nil, err
	}

	defer func() {
		_ = fl.Unlock()
		slog.Info("reboot proxy unlock")
	}()

	// 获得锁后, 首先尝试一次重连
	pdb, padb, err = connectPair()
	if err == nil {
		slog.Info("retry connect proxy success")
		return pdb, padb, nil
	}
	slog.Info("retry connect proxy failed, need reboot")

	running, err := confirmSelfIsRunning()
	if err != nil {
		return nil, nil, err
	}
	if !running {
		err = errors.New("self isn't running, skip reboot")
		slog.Error("reboot proxy", slog.String("err", err.Error()))
		return nil, nil, err
	}

	_ = proxyutil.KillDownProxy(config.MonitorConfig.Port)
	slog.Info("reboot proxy kill success")

	p := proxyutil.StartProxyParam{
		InstallPath:    cst.ProxyInstallPath,
		ProxyCnf:       util.GetProxyCnfName(config.MonitorConfig.Port),
		Host:           config.MonitorConfig.Ip,
		Port:           config.MonitorConfig.Port,
		ProxyAdminUser: config.MonitorConfig.Auth.ProxyAdmin.User,
		ProxyAdminPwd:  config.MonitorConfig.Auth.ProxyAdmin.Password,
	}

	err = p.StartAsMySQL(config.MonitorConfig.Port)
	if err != nil {
		slog.Warn(
			"reboot proxy",
			slog.Int("port", config.MonitorConfig.Port),
			slog.String("error", err.Error()),
		)
		return nil, nil, err
	}

	slog.Info("reboot proxy", slog.Int("port", config.MonitorConfig.Port))

	time.Sleep(3 * time.Second)

	slog.Info("retry connect after reboot proxy")

	pdb, padb, err = connectPair()
	if err != nil {
		slog.Error(
			"connect proxy after reboot",
			slog.String("err", err.Error()),
		)
		return nil, nil, err
	}

	slog.Info("connect proxy after reboot success")
	return pdb, padb, nil
}

func connectProxy() (db *sqlx.DB, err error) {
	db, err = connectDB(
		config.MonitorConfig.Ip,
		config.MonitorConfig.Port,
		config.MonitorConfig.Auth.Proxy,
		false,
		false,
	)
	if err != nil {
		slog.Error(
			"connect proxy",
			slog.String("error", err.Error()),
			slog.String("ip", config.MonitorConfig.Ip),
			slog.Int("port", config.MonitorConfig.Port),
		)
		return nil, err
	}

	return db, nil
}

func connectProxyAdmin() (db *sqlx.DB, err error) {
	adminPort := config.MonitorConfig.Port + 1000
	db, err = connectDB(
		config.MonitorConfig.Ip,
		adminPort,
		config.MonitorConfig.Auth.ProxyAdmin,
		false,
		true,
	)
	if err != nil {
		var merr *mysql.MySQLError
		if errors.As(err, &merr) {
			if merr.Number == 1105 {
				// 连接 proxy 管理端肯定在这里返回
				return db, nil //pdb, padb, nil
			}
		}
		slog.Error(
			"connect proxy admin",
			slog.String("error", err.Error()),
			slog.String("ip", config.MonitorConfig.Ip),
			slog.Int("port", adminPort),
		)
		return nil, err
	}
	return db, nil
}

func connectPair() (pdb *sqlx.DB, padb *sqlx.DB, err error) {
	pdb, e := connectProxy()
	if e != nil {
		err = errors.Join(err, e)
	}
	padb, e = connectProxyAdmin()
	if e != nil {
		err = errors.Join(err, e)
	}
	return pdb, padb, err
}

func addExLock() (fl *flock.Flock, err error) {
	lockFileName := fmt.Sprintf(
		"proxy-retry-restart-%d.lock",
		config.MonitorConfig.Port,
	)
	lockFileBasePath := filepath.Join(cst.MySQLMonitorInstallPath, "locks")
	err = os.MkdirAll(lockFileBasePath, os.ModePerm)
	if err != nil {
		slog.Error(
			"reboot proxy create lock file",
			slog.String("err", err.Error()),
			slog.String("path", lockFileBasePath),
		)
		return nil, err
	}
	lockFilePath := filepath.Join(lockFileBasePath, lockFileName)
	fl = flock.New(lockFilePath)

	slog.Info(
		"reboot proxy try to lock",
		slog.String("path", lockFilePath),
	)
	// 这里用排它锁, 当获得锁时, 要么自己来重启, 要么别人重启完了
	err = fl.Lock()
	if err != nil {
		slog.Error(
			"reboot proxy try to lock",
			slog.String("err", err.Error()))
		return nil, err
	}

	slog.Info("reboot proxy try to lock success")
	return fl, nil
}

func confirmSelfIsRunning() (bool, error) {
	info, layer, err := mrapi.ListInstanceInfo(*config.MonitorConfig.BkCloudID, config.MonitorConfig.Port)
	if err != nil {
		slog.Info("query instance info", slog.String("error", err.Error()))
		return false, err
	}
	slog.Info(
		"query instance info",
		slog.Any("instances raw info", info),
		slog.Any("layer", layer),
	)
	var pinfos []mrapi.ProxyInstanceInfo
	err = json.Unmarshal(info, &pinfos)
	if err != nil {
		slog.Info("query instance info unmarshal failed", slog.String("error", err.Error()))
		return false, err
	}

	idx := slices.IndexFunc(pinfos, func(item mrapi.ProxyInstanceInfo) bool {
		return item.Port == config.MonitorConfig.Port
	})
	if idx < 0 {
		err = fmt.Errorf("instance [%d] not found", config.MonitorConfig.Port)
		slog.Info("query instance info", slog.String("error", err.Error()))
		return false, err
	}

	pinfo := pinfos[idx]
	slog.Info(
		"query instance info",
		slog.Any("instance info", pinfo),
	)

	return pinfo.Status == "running" && pinfo.Phase == "online", nil
}
