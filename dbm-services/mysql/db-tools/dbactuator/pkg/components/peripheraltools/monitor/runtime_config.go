package monitor

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
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
	for _, inst := range c.Params.InstancesInfo {
		err = generateRuntimeConfigIns(c.Params, inst, &c.GeneralParam.RuntimeAccountParam)
		if err != nil {
			return err
		}

		if c.Params.MachineType == "backend" {
			err = createUserListBackupTable(inst, &c.GeneralParam.RuntimeAccountParam)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func createUserListBackupTable(instance *internal.InstanceInfo, rtap *components.RuntimeAccountParam) (err error) {
	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf("%s:%s@tcp(%s:%d)/",
			rtap.MonitorUser, rtap.MonitorPwd,
			instance.Ip, instance.Port,
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

func generateRuntimeConfigIns(mmp *MySQLMonitorParam, instance *internal.InstanceInfo, rtap *components.RuntimeAccountParam) (err error) {
	if instance.BkInstanceId <= 0 {
		err = errors.Errorf(
			"%s:%d invalid bk_instance_id: %d",
			instance.Ip,
			instance.Port,
			instance.BkInstanceId,
		)
		logger.Error(err.Error())
		return err
	}

	logDir := filepath.Join(cst.MySQLMonitorInstallPath, "logs")

	ac, err := authByMachineType(mmp.MachineType, rtap)
	if err != nil {
		return err
	}

	cfg := config.Config{
		BkBizId:      instance.BkBizId,
		Ip:           instance.Ip,
		Port:         instance.Port,
		BkInstanceId: instance.BkInstanceId,
		ImmuteDomain: instance.ImmuteDomain,
		MachineType:  mmp.MachineType,
		Role:         &instance.Role,
		BkCloudID:    &mmp.BkCloudId,
		DBModuleID:   &instance.DBModuleId,
		Log: &config.LogConfig{
			Console:    false,
			LogFileDir: &logDir,
			Debug:      false,
			Source:     true,
			Json:       true,
		},
		ItemsConfigFile: filepath.Join(
			cst.MySQLMonitorInstallPath,
			fmt.Sprintf("items-config_%d.yaml", instance.Port),
		),
		Auth:            *ac,
		ApiUrl:          mmp.ApiUrl,
		DBASysDbs:       mmp.SystemDbs,
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
			fmt.Sprintf("monitor-config_%d.yaml", instance.Port)),
	)

	return internal.WriteConfig(cfgFilePath, b)
}

func authByMachineType(machineType string, rtap *components.RuntimeAccountParam) (ac *config.AuthCollect, err error) {
	switch machineType {
	case "proxy":
		ac = &config.AuthCollect{
			Proxy: &config.ConnectAuth{
				User:     rtap.MonitorAccessAllUser,
				Password: rtap.MonitorAccessAllPwd,
			},
			ProxyAdmin: &config.ConnectAuth{
				User:     rtap.ProxyAdminUser,
				Password: rtap.ProxyAdminPwd,
			},
		}
	case "backend", "single", "remote", "spider":
		ac = &config.AuthCollect{
			Mysql: &config.ConnectAuth{
				User:     rtap.MonitorUser,
				Password: rtap.MonitorPwd,
			},
		}
	default:
		err = errors.Errorf("not support machine type: %s", machineType)
		logger.Error(err.Error())
		return nil, err
	}
	return ac, nil
}
