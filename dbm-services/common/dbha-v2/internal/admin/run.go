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
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var config Configuration

// Run run admin service
func Run(cmd *cobra.Command, args []string) error {

	viper.SetConfigName("admin")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")

	if ConfigFilePath != "" {
		viper.SetConfigFile(ConfigFilePath)
	}

	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	if err := viper.Unmarshal(&config); err != nil {
		return err
	}

	logCfg := logger.Config{
		FileName:   config.Log.Path,
		LogLevel:   logger.Level(config.Log.Level),
		MaxSizeMB:  config.Log.FileSizeMB,
		MaxBackups: config.Log.FileCount,
	}

	log := logger.NewZapLogger(logCfg)
	logger.SetLogger(log)

	logger.Debug("admin configuration:%v", config)
	return nil
}
