package checksum

import (
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"

	"gopkg.in/yaml.v2"
)

func (c *MySQLChecksumComp) GenerateRuntimeConfig() (err error) {
	for _, port := range c.Params.Ports {
		logger.Info("generating runtime config on %v", port)
		err = c.generateRuntimeConfigIns(port)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *MySQLChecksumComp) generateRuntimeConfigIns(port int) (err error) {
	logDir := filepath.Join(cst.ChecksumInstallPath, "logs")

	var ignoreDbs []string
	ignoreDbs = append(ignoreDbs, c.Params.SystemDbs...)
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%s%%`, c.Params.StageDBHeader))
	ignoreDbs = append(ignoreDbs, `bak_%`) // gcs/scr truncate header
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%%%s`, c.Params.RollbackDBTail))

	cfg := NewRuntimeConfig(
		c.Params.BkBizId, c.Params.ClusterId, port,
		c.Params.Role, c.Params.Schedule, c.Params.ImmuteDomain, c.Params.IP,
		c.GeneralParam.RuntimeAccountParam.MonitorUser, c.GeneralParam.RuntimeAccountParam.MonitorPwd,
		c.Params.ApiUrl, logDir, 2, c.tools,
	)
	cfg.SetFilter(nil, ignoreDbs, nil, nil)

	b, err := yaml.Marshal(&cfg)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info(string(b))

	cfgFilePath := filepath.Join(cst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", port))
	logger.Info(cfgFilePath)

	return internal.WriteConfig(cfgFilePath, b)
}
