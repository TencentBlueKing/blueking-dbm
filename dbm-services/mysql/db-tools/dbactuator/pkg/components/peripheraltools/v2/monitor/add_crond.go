package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"path/filepath"
)

func (c *MySQLMonitorComp) AddToCrond() (err error) {
	mysqlMonitor, err := c.tools.Get(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMySQLMonitor, err.Error())
		return err
	}

	for _, ele := range c.Params.PortBkInstanceList {
		configPath := filepath.Join(
			cst.MySQLMonitorInstallPath,
			fmt.Sprintf("monitor-config_%d.yaml", ele.Port),
		)

		err = internal.RegisterCrond(mysqlMonitor, configPath, c.Params.ExecUser)
		if err != nil {
			logger.Error("register %s failed: %s", mysqlMonitor, err.Error())
			return err
		}
	}
	return nil
}
