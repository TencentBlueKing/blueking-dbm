package checksum

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"path/filepath"
)

func (c *MySQLChecksumComp) AddToCrond() (err error) {
	return AddCrond(c.Params.Ports)
}

func AddCrond(ports []int) (err error) {
	tl, err := tools.NewToolSetWithPick(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	mysqlTableChecksum, err := tl.Get(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMysqlTableChecksum, err.Error())
		return err
	}

	for _, port := range ports {
		configPath := filepath.Join(
			cst.ChecksumInstallPath,
			fmt.Sprintf("checksum_%d.yaml", port),
		)

		err = internal.RegisterCrond(mysqlTableChecksum, configPath, "system")
		if err != nil {
			logger.Error("register %s failed: %s", mysqlTableChecksum, err.Error())
			return err
		}
	}

	return nil
}
