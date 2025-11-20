package rotate

import (
	"fmt"
	"os"
	"path/filepath"

	gyaml "github.com/ghodss/yaml"
	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// RemoveConfig 删除某个 binlog 实例的 rotate 配置
func (c *RotateBinlogComp) RemoveConfig(ports []int) (err error) {
	// remove file server.<port>.yaml
	for _, port := range ports {
		serverConfigFile := filepath.Join(filepath.Dir(c.Config), fmt.Sprintf("server.%d.yaml", port))
		if cmutil.FileExists(serverConfigFile) {
			logger.Info("remove config file %s", serverConfigFile)
			if err = os.Remove(serverConfigFile); err != nil {
				return err
			}
		}
	}

	// remove server from main config if possible
	if c.ConfigObj, err = ReadMainConfig(c.Config); err != nil {
		logger.Warn("remove ReadMainConfig %s with err=%s", c.Config, err.Error())
	}
	if c.ConfigObj == nil {
		return nil
	}
	newServers := make([]*ServerObj, 0)
	for _, binlogInst := range c.ConfigObj.Servers {
		if !lo.Contains(ports, binlogInst.Port) {
			newServers = append(newServers, binlogInst)
		}
	}
	if len(newServers) == len(c.ConfigObj.Servers) {
		// no change
		return nil
	} else {
		c.ConfigObj.Servers = newServers
	}

	yamlData, err := gyaml.Marshal(c.ConfigObj) // use json tag
	if err != nil {
		return err
	}
	cfgFile := c.Config // viper.ConfigFileUsed()
	if err = cmutil.FileExistsErr(cfgFile); err != nil {
		return err
	}
	if err := os.WriteFile(cfgFile, yamlData, 0644); err != nil {
		return err
	}
	return nil
}
