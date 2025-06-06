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

package probe

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/google/uuid"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// Run run probe
func Run(cmd *cobra.Command, args []string) error {

	viper.SetConfigName("probe")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")

	if ConfigFilePath != "" {
		viper.SetConfigFile(ConfigFilePath)
	}

	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	if err := viper.Unmarshal(&config.Cfg); err != nil {
		return err
	}

	logCfg := logger.Config{
		FileName:   config.Cfg.Log.Path,
		LogLevel:   logger.Level(config.Cfg.Log.Level),
		MaxSizeMB:  config.Cfg.Log.FileSizeMB,
		MaxBackups: config.Cfg.Log.FileCount,
	}

	log := logger.NewZapLogger(logCfg)
	logger.SetLogger(log)

	clientId := uuid.New()
	p := &Probe{ClientId: clientId.String()}
	ctx := context.Background()
	return p.Run(ctx)
}
