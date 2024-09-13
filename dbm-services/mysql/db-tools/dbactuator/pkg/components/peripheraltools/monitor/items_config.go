package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"path/filepath"
	"slices"
	"strings"

	"golang.org/x/exp/maps"
	"gopkg.in/yaml.v2"
)

func (c *MySQLMonitorComp) GenerateItemsConfig() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		err = generateItemsConfigIns(inst, c.Params.ItemsConfig)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateItemsConfigIns(instance *internal.InstanceInfo, itemsConfig map[string]*config.MonitorItem) (err error) {
	itemList := maps.Values(itemsConfig)
	slices.SortFunc(itemList, func(a, b *config.MonitorItem) int {
		return strings.Compare(a.Name, b.Name)
	})

	b, err := yaml.Marshal(itemList)
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
