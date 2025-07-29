package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"path/filepath"
)

func AddCrond(ports []int) (err error) {
	tl, err := tools.NewToolSetWithPick(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	mysqlMonitor, err := tl.Get(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMySQLMonitor, err.Error())
		return err
	}

	for _, port := range ports {
		configPath := filepath.Join(
			cst.MySQLMonitorInstallPath,
			fmt.Sprintf("monitor-config_%d.yaml", port),
		)

		err = internal.RegisterCrond(mysqlMonitor, configPath, "system")
		if err != nil {
			logger.Error("register %s failed: %s", mysqlMonitor, err.Error())
			return err
		}
	}
	return nil
}
