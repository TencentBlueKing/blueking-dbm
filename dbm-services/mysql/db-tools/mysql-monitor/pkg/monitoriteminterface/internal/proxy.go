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
	"time"

	"errors"

	"github.com/go-sql-driver/mysql"
	"github.com/gofrs/flock"
	"github.com/jmoiron/sqlx"
)

func ConnectProxy() (pdb *sqlx.DB, padb *sqlx.DB, err error) {
	pdb, padb, err = connectPair()

	if err != nil {
		return retryAndRestartProxy()
	}

	return pdb, padb, err
}

// 第一次连接失败进入排他重试阶段
// 先尝试重连, 失败则拉起进场, 再尝试连接
// 为了防止不同周期的监控同时操作, 这里按端口文件锁排他
func retryAndRestartProxy() (pdb *sqlx.DB, padb *sqlx.DB, err error) {
	lockFileName := fmt.Sprintf(
		"proxy-retry-restart-%d.lock",
		config.MonitorConfig.Port,
	)
	lockFileBasePath := filepath.Join(cst.MySQLMonitorInstallPath, "locks")
	err = os.MkdirAll(lockFileBasePath, os.ModePerm)
	if err != nil {
		slog.Error(
			"retry restart proxy",
			slog.String("err", err.Error()),
			slog.Int("port", config.MonitorConfig.Port),
		)
		return nil, nil, err
	}
	lockFilePath := filepath.Join(lockFileBasePath, lockFileName)
	fl := flock.New(lockFilePath)

	slog.Info("retry restart proxy begin wait lock")
	err = fl.Lock()

	if err != nil {
		slog.Error(
			"retry restart proxy",
			slog.String("err", err.Error()))
		return nil, nil, err
	}
	defer func() {
		//_ = lk.Unlock()
		_ = fl.Unlock()
		slog.Info("unlock file")
	}()

	slog.Info("retry restart proxy get lock success")

	pdb, padb, err = connectPair()
	if err == nil {
		slog.Info("retry restart proxy connect success")
		return pdb, padb, nil
	}
	slog.Info("retry restart proxy connect failed", slog.String("error", err.Error()))

	// 反向查询实例状态
	info, layer, err := mrapi.ListInstanceInfo(*config.MonitorConfig.BkCloudID, config.MonitorConfig.Port)
	if err != nil {
		slog.Info("retry restart proxy call reverse api", slog.String("error", err.Error()))
		return nil, nil, err
	}
	slog.Info(
		"retry restart proxy",
		slog.Any("instances raw info", info),
		slog.Any("layer", layer),
	)
	var pinfos []mrapi.ProxyInstanceInfo
	err = json.Unmarshal(info, &pinfos)
	if err != nil {
		slog.Info("retry restart proxy unmarshal failed", slog.String("error", err.Error()))
		return nil, nil, err
	}

	idx := slices.IndexFunc(pinfos, func(item mrapi.ProxyInstanceInfo) bool {
		return item.Port == config.MonitorConfig.Port
	})
	if idx < 0 {
		err = fmt.Errorf("instance [%d] not found", config.MonitorConfig.Port)
		slog.Info("retry restart proxy", slog.String("error", err.Error()))
		return nil, nil, err
	}

	pinfo := pinfos[idx]
	slog.Info(
		"retry restart proxy",
		slog.Any("instance info", pinfo),
	)

	if pinfo.Status != "running" {
		slog.Error(
			"retry restart proxy skip restart",
			slog.String("status", pinfo.Status))
		return nil, nil, errors.New("proxy instance is not running")
	}

	_ = proxyutil.KillDownProxy(config.MonitorConfig.Port)
	slog.Info("retry restart proxy kill success")

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
			"restart proxy",
			slog.Int("port", config.MonitorConfig.Port),
			slog.String("error", err.Error()),
		)
		return nil, nil, err
	}

	slog.Info("restart proxy", slog.Int("port", config.MonitorConfig.Port))

	time.Sleep(1 * time.Second)

	slog.Info("retry connect after restart proxy")

	return connectPair()
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
