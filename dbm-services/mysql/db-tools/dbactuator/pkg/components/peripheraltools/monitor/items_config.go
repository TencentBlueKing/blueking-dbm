package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"path/filepath"

	"golang.org/x/exp/maps"
	"gopkg.in/yaml.v2"
)

func (c *MySQLMonitorComp) GenerateItemsConfig() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		err = generateItemsConfigIns(inst)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateItemsConfigIns(instance *instanceInfo) (err error) {
	b, err := yaml.Marshal(maps.Values(instance.ItemsConfig))
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	itemConfigPath := filepath.Join(
		cst.MySQLMonitorInstallPath,
		fmt.Sprintf(`items-config_%d.yaml`, instance.Port),
	)

	return internal.WriteConfig(itemConfigPath, append(b, []byte("\n")...))
}
