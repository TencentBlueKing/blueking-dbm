package checksum

import (
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"

	"gopkg.in/yaml.v2"
)

func (c *MySQLChecksumComp) GenerateRuntimeConfig() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		logger.Info("generating runtime config on %v", inst)
		err = generateRuntimeConfigIns(c.Params, inst, &c.GeneralParam.RuntimeAccountParam, c.tools)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateRuntimeConfigIns(mcp *MySQLChecksumParam, instance *instanceInfo, rtap *components.RuntimeAccountParam, tl *tools.ToolSet) (err error) {
	logDir := filepath.Join(cst.ChecksumInstallPath, "logs")

	var ignoreDbs []string
	ignoreDbs = append(ignoreDbs, mcp.SystemDbs...)
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%s%%`, mcp.StageDBHeader))
	ignoreDbs = append(ignoreDbs, `bak_%`) // gcs/scr truncate header
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%%%s`, mcp.RollbackDBTail))

	cfg := NewRuntimeConfig(
		instance.BkBizId, instance.ClusterId, instance.Port,
		instance.Role, instance.Schedule, instance.ImmuteDomain, instance.Ip,
		rtap.MonitorUser, rtap.MonitorPwd, mcp.ApiUrl, logDir, 2, tl)
	cfg.SetFilter(nil, ignoreDbs, nil, nil)

	b, err := yaml.Marshal(&cfg)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info(string(b))

	cfgFilePath := filepath.Join(cst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", instance.Port))
	logger.Info(cfgFilePath)

	return internal.WriteConfig(cfgFilePath, b)
}
