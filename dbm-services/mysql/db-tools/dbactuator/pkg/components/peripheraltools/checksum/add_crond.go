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
	mysqlTableChecksum, err := c.tools.Get(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMysqlTableChecksum, err.Error())
		return err
	}

	for _, inst := range c.Params.InstancesInfo {
		configPath := filepath.Join(
			cst.ChecksumInstallPath,
			fmt.Sprintf("checksum_%d.yaml", inst.Port),
		)

		err = internal.RegisterCrond(mysqlTableChecksum, configPath, c.Params.ExecUser)
		if err != nil {
			logger.Error("register %s failed: %s", mysqlTableChecksum, err.Error())
			return err
		}
	}
	return nil
}
