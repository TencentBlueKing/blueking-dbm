// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"dbm-services/common/db-event-consumer/pkg/config"
	sinkerPkg "dbm-services/common/db-event-consumer/pkg/sinker"
)

var dumpEffectiveConfig bool

// validateCmd 只做配置校验，不连 kafka、不连 db，可在 CI 里对各环境配置目录跑一遍
var validateCmd = &cobra.Command{
	Use:          "validate",
	Short:        "validate config files and print effective sinkers config",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := config.InitConfig(configFile, enableDefaults); err != nil {
			return err
		}
		if err := sinkerPkg.InitDatasource(); err != nil {
			return err
		}
		// 校验每个入库项引用的 datasource 是否存在
		var missing []string
		for _, sink := range config.SinkerConfigs {
			if _, ok := sinkerPkg.DatasourceMap[sink.Datasource]; !ok {
				missing = append(missing, fmt.Sprintf("%s -> %s", sink.ModelTable, sink.Datasource))
			}
		}
		if len(missing) > 0 {
			msg := fmt.Sprintf("datasource not found: %v", missing)
			if config.MainConfig.OnMissingDatasource == config.OnMissingDatasourceFail {
				return fmt.Errorf("%s", msg)
			}
			_, _ = fmt.Fprintf(os.Stderr, "[WARN] %s (on_missing_datasource=skip, these sinkers will be skipped)\n", msg)
		}
		if dumpEffectiveConfig {
			fmt.Print(config.EffectiveSinkersYaml())
		}
		_, _ = fmt.Fprintf(os.Stderr, "config ok, %d sinkers\n", len(config.SinkerConfigs))
		return nil
	},
}

func init() {
	validateCmd.Flags().BoolVar(&dumpEffectiveConfig, "dump-effective-config", true,
		"print merged sinkers config to stdout")
	rootCmd.AddCommand(validateCmd)
}
