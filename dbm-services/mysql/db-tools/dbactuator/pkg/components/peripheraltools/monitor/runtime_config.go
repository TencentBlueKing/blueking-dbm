package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"path/filepath"
	"time"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

func (c *MySQLMonitorComp) GenerateRuntimeConfig() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		err = generateRuntimeConfigIns(c.Params, inst, &c.GeneralParam.RuntimeAccountParam)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateRuntimeConfigIns(mmp *MySQLMonitorParam, instance *instanceInfo, rtap *components.RuntimeAccountParam) (err error) {
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
