/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package admin

import (
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/migrator"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/version"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var VersionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print Version Information",
	Run: func(cmd *cobra.Command, args []string) {
		version.Print("DBHA Admin Server")
	},
}

var MigrateCmd = &cobra.Command{
	Use:   "migrate",
	Short: "migrate all databases",
	Run: func(cmd *cobra.Command, args []string) {

		viper.SetConfigName("admin")
		viper.SetConfigType("yaml")
		viper.AddConfigPath("./etc")

		logger.Info("use the configuration:%s", ConfigFilePath)

		if ConfigFilePath != "" {
			viper.SetConfigFile(ConfigFilePath)
		}

		if err := viper.ReadInConfig(); err != nil {
			logger.Error("read admin configuration failed, %v", err)
			return
		}

		if err := viper.Unmarshal(&config.Cfg); err != nil {
			logger.Error("unmarshal admin configuration failed, %v", err)
			return
		}

		mig := &migrator.Migrator{}
		if err := mig.InitDbhaData(); err != nil {
			logger.Error("migrate dbhadata failed, %v", err)
		}
	},
}
