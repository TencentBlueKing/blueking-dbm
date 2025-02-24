package monitor

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"path/filepath"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

func (c *MySQLMonitorComp) GenerateRuntimeConfig() (err error) {
	for _, ele := range c.Params.PortBkInstanceList {
		err = c.generateRuntimeConfigIns(ele.Port, ele.BkInstanceId)
		if err != nil {
			return err
		}

		if c.Params.MachineType == "backend" {
			err = c.createUserListBackupTable(ele.Port)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func (c *MySQLMonitorComp) createUserListBackupTable(port int) (err error) {
	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf("%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.MonitorUser, c.GeneralParam.RuntimeAccountParam.MonitorPwd,
			c.Params.IP, port,
		))
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	_, err = db.ExecContext(
		context.Background(),
		`CREATE TABLE IF NOT EXISTS infodba_schema.proxy_user_list(
					proxy_ip varchar(32) NOT NULL,
					username varchar(64) NOT NULL,
					host varchar(32) NOT NULL,
					create_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
					PRIMARY KEY (proxy_ip, username, host),
					KEY IDX_USERNAME_HOST(username, host, create_at),
					KEY IDX_HOST(host, create_at),
					KEY IDX_IP_HOST(proxy_ip, host, create_at)
				) ENGINE=InnoDB;`,
	)
	if err != nil {
		return err
	}
	return nil
}

func (c *MySQLMonitorComp) generateRuntimeConfigIns(port int, bkInstanceId int64) (err error) {
	logDir := filepath.Join(cst.MySQLMonitorInstallPath, "logs")

	ac, err := c.authByMachineType()
	if err != nil {
		return err
	}

	if bkInstanceId <= 0 {
		err = errors.Errorf(
			"%s:%d invalid bk_instance_id: %d",
			c.Params.IP, port, bkInstanceId,
		)
		logger.Error(err.Error())
		return err
	}

	cfg := config.Config{
		BkBizId:      c.Params.BKBizId,
		Ip:           c.Params.IP,
		Port:         port,
		BkInstanceId: bkInstanceId,
		ImmuteDomain: c.Params.ImmuteDomain,
		MachineType:  c.Params.MachineType,
		Role:         &c.Params.Role,
		BkCloudID:    &c.Params.BkCloudId,
		DBModuleID:   &c.Params.DBModuleId,
		Log: &config.LogConfig{
			Console:    false,
			LogFileDir: &logDir,
			Debug:      false,
			Source:     true,
			Json:       true,
		},
		ItemsConfigFile: filepath.Join(
			cst.MySQLMonitorInstallPath,
			fmt.Sprintf("items-config_%d.yaml", port),
		),
		Auth:            *ac,
		ApiUrl:          c.Params.ApiUrl,
		DBASysDbs:       c.Params.SystemDbs,
		InteractTimeout: 5 * time.Second,
		DefaultSchedule: "@every 1m",
	}

	b, err := yaml.Marshal(cfg)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	cfgFilePath := filepath.Join(
		filepath.Join(cst.MySQLMonitorInstallPath,
			fmt.Sprintf("monitor-config_%d.yaml", port)),
	)

	err = internal.WriteConfig(cfgFilePath, b)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	//}
	return nil
}

func (c *MySQLMonitorComp) authByMachineType() (ac *config.AuthCollect, err error) {
	switch c.Params.MachineType {
	case "proxy":
		ac = &config.AuthCollect{
			Proxy: &config.ConnectAuth{
				User:     c.GeneralParam.RuntimeAccountParam.MonitorAccessAllUser,
				Password: c.GeneralParam.RuntimeAccountParam.MonitorAccessAllPwd,
			},
			ProxyAdmin: &config.ConnectAuth{
				User:     c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
				Password: c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
			},
		}
	case "backend", "single", "remote", "spider":
		ac = &config.AuthCollect{
			Mysql: &config.ConnectAuth{
				User:     c.GeneralParam.RuntimeAccountParam.MonitorUser,
				Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
			},
		}
	default:
		err = errors.Errorf("not support machine type: %s", c.Params.MachineType)
		logger.Error(err.Error())
		return nil, err
	}
	return ac, nil
}
