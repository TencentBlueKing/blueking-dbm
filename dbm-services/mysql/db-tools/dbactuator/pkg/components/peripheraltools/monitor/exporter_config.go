package monitor

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (c *MySQLMonitorComp) GenerateExporterConfig() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		err = generateExporterConfigIns(c.Params, inst, &c.GeneralParam.RuntimeAccountParam)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateExporterConfigIns(mmp *MySQLMonitorParam, instance *internal.InstanceInfo, rtap *components.RuntimeAccountParam) (err error) {
	exporterConfigPath := filepath.Join(
		"/etc",
		fmt.Sprintf("exporter_%d.cnf", instance.Port),
	)

	if mmp.MachineType == "proxy" {
		f, err := os.OpenFile(exporterConfigPath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		defer func() {
			_ = f.Close()
		}()

		proxyContent := fmt.Sprintf(
			"%s:%d,,,%s:%d,%s,%s",
			instance.Ip, instance.Port,
			instance.Ip, native.GetProxyAdminPort(instance.Port),
			rtap.ProxyAdminUser, rtap.ProxyAdminPwd,
		)
		_, err = f.WriteString(proxyContent)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	} else {
		err = util.CreateExporterConf(
			exporterConfigPath,
			instance.Ip,
			instance.Port,
			rtap.MonitorUser,
			rtap.MonitorPwd,
		)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}

	_, err = osutil.ExecShellCommand(
		false,
		fmt.Sprintf("chown mysql %s", exporterConfigPath),
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}
