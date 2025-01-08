// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package mainloop 主循环
package mainloop

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"log/slog"
	"path/filepath"
	"slices"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	_ "github.com/go-sql-driver/mysql" // mysql TODO
	"github.com/juju/fslock"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

// Run TODO
func Run(hardcode bool) error {
	var iNames []string
	if hardcode {
		iNames = viper.GetStringSlice("hardcode-items")
	} else {
		iNames = viper.GetStringSlice("run-items")
	}
	slog.Info("main loop", slog.String("items", strings.Join(iNames, ",")))
	slog.Info("main loop", slog.Bool("hardcode", hardcode))

	lockFileName := fmt.Sprintf("%d-%s.lock", config.MonitorConfig.Port, strings.Join(iNames, "."))
	lockFilePath := filepath.Join(cst.MySQLMonitorInstallPath, lockFileName)

	slog.Info("main loop", slog.String("lockFilePath", lockFilePath))
	lk := fslock.New(lockFilePath)
	err := lk.TryLock()
	if err != nil {
		slog.Error("main loop",
			slog.String("error", err.Error()))
		utils.SendMonitorEvent(
			"db-hang",
			fmt.Sprintf("last round %s not finish, db may be hang", strings.Join(iNames, ",")),
		)
		return errors.Wrapf(err, "main loop lock file %s failed, may be last round not finish", lockFilePath)
	}
	defer func() {
		_ = lk.Unlock()
	}()
	slog.Info("main loop get lock success", slog.String("lockFilePath", lockFilePath))

	if hardcode && slices.Index(iNames, config.HeartBeatName) >= 0 {
		utils.SendMonitorMetrics(config.HeartBeatName, 1, nil)
	}

	cc, err := monitoriteminterface.NewConnectionCollect()
	if err != nil {
		if hardcode && slices.Index(iNames, "db-up") >= 0 {
			utils.SendMonitorEvent("db-up", err.Error())
		}
		return nil
	}
	defer func() {
		cc.Close()
	}()

	slog.Debug("make connection collect", slog.Any("connection collect", cc))

	if hardcode {
		return nil
	}

	for _, iName := range iNames {

		if constructor, ok := itemscollect.RegisteredItemConstructor()[iName]; ok {
			msg, err := constructor(cc).Run()
			if err != nil {
				slog.Error("run monitor item", slog.String("error", err.Error()), slog.String("name", iName))
				utils.SendMonitorEvent(
					"monitor-internal-error",
					fmt.Sprintf("run monitor item %s failed: %s", iName, err.Error()),
				)
				continue
			}

			if msg != "" {
				slog.Info(
					"run monitor items",
					slog.String("name", iName),
					slog.String("msg", msg),
				)
				utils.SendMonitorEvent(iName, msg)
				continue
			}

			slog.Info("run monitor item pass", slog.String("name", iName))

		} else {
			err := errors.Errorf("%s not registered", iName)
			slog.Error("run monitor item", slog.String("error", err.Error()))
			continue
		}
	}
	return nil
}
