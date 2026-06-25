package kafka

import (
	"bufio"
	"os"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/common/go-pubpkg/logger"
)

// CheckBrokerConfigsComp checks which config keys are present in server.properties
type CheckBrokerConfigsComp struct {
	GeneralParam *components.GeneralParam
	Params       *CheckBrokerConfigsParams
}

// CheckBrokerConfigsParams input parameters
type CheckBrokerConfigsParams struct {
	ConfigsToCheck []string `json:"configs_to_check"`
}

// CheckBrokerConfigsResult output written to <ctx>
type CheckBrokerConfigsResult struct {
	MissingConfigs []string `json:"missing_configs"`
}

// Init 初始化组件
func (c *CheckBrokerConfigsComp) Init() (err error) {
	logger.Info("CheckBrokerConfigsComp Init")
	return nil
}

// CheckBrokerConfigs reads server.properties and reports which keys from ConfigsToCheck are absent
func (c *CheckBrokerConfigsComp) CheckBrokerConfigs() (err error) {
	present := make(map[string]bool)

	f, err := os.Open(cst.KafkaConfigFile)
	if err != nil {
		logger.Error("open %s failed: %v", cst.KafkaConfigFile, err)
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if idx := strings.Index(line, "="); idx > 0 {
			key := strings.TrimSpace(line[:idx])
			present[key] = true
		}
	}
	if err = scanner.Err(); err != nil {
		logger.Error("scan %s failed: %v", cst.KafkaConfigFile, err)
		return err
	}

	var missing []string
	for _, key := range c.Params.ConfigsToCheck {
		if !present[key] {
			missing = append(missing, key)
		}
	}
	if missing == nil {
		missing = []string{}
	}

	result := CheckBrokerConfigsResult{MissingConfigs: missing}
	logger.Info("missing configs: %v", missing)
	return components.PrintOutputCtx(result)
}
