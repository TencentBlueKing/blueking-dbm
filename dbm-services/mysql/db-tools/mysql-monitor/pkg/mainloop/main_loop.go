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
	"fmt"
	"log/slog"
	"math/rand"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/update_monitor_config"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	_ "github.com/go-sql-driver/mysql" // mysql TODO
	"github.com/gofrs/flock"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

// Run TODO
func Run(hardcode bool) error {
	iNames := loadItems(hardcode)

	fl, err := getLocker(iNames)
	if err != nil {
		return err
	}
	defer func() {
		_ = fl.Unlock()
	}()

	cc, err := monitoriteminterface.NewConnectionCollect()
	defer func() {
		if cc != nil {
			cc.Close() // 可以随便调用, 内部已经兼容句柄为 nil 的情况
		}
	}()

	if cc == nil {
		slog.Error("failed to instantiate connection collect", slog.String("err", err.Error()))
		utils.SendMonitorEvent(
			"monitor-internal-error",
			fmt.Sprintf("failed to instantiate connection collect. err: %s", err.Error()),
			nil,
		)
		return err
	}

	if hardcode {
		if err != nil && slices.Index(iNames, "db-up") >= 0 {
			eventSent := false
			for _, h := range []*pkg.MySQLMonitorDBH{cc.MySqlDB, cc.ProxyDB, cc.ProxyAdminDB, cc.CtlDB} {
				if h != nil && h.DB == nil {
					eventSent = true
					utils.SendMonitorEvent(
						"db-up", err.Error(), map[string]interface{}{
							"instance_host": h.Host,
							"instance_port": h.Port,
						},
					)
				}
			}
			if !eventSent {
				utils.SendMonitorEvent("db-up", err.Error(), nil) // 兜底
			}
		}

		return hardcodeRun(iNames)
	}

	// 普通执行时忽略连接错误
	if err != nil {
		return nil
	}
	cc.InitItemOptions() // set item custom options to runner

	return itemsRun(iNames, cc)
}

func hardcodeRun(iNames []string) error {
	slog.Info("main loop hardcode-run")

	if slices.Index(iNames, "update-monitor-config") >= 0 {
		_, msg, err := (&update_monitor_config.Checker{}).Run()
		if err != nil {
			slog.Error(
				"main loop",
				slog.String("error", err.Error()),
			)
			utils.SendMonitorEvent(
				"monitor-internal-error",
				fmt.Sprintf("update-monitor-config failed, %s", err.Error()),
				nil,
			)
		}
		if msg != "" {
			slog.Info("main loop", slog.String("msg", msg))
			utils.SendMonitorEvent("update-monitor-config", msg, nil)
		}
	}

	if slices.Index(iNames, config.HeartBeatName) >= 0 {
		utils.SendMonitorMetrics(config.HeartBeatName, 1, nil)
	}

	slog.Info("main loop hardcode-run finish")
	return nil
}

func itemsRun(iNames []string, cc *monitoriteminterface.ConnectionCollect) error {
	slog.Info("main loop items-run")

	randSleepN := rand.Intn(5)
	slog.Info(
		"run monitor items",
		slog.Int("randSleepN", randSleepN),
	)
	// 每次整体随机休眠 [0:5), 多实例场景时稍微错开
	time.Sleep(time.Duration(randSleepN) * time.Second)

	for _, iName := range iNames {
		itemLogger := slog.New(config.Logger.Handler())
		itemLogger = itemLogger.With("current item", iName)
		slog.SetDefault(itemLogger)

		idx := slices.IndexFunc(
			config.ItemsConfig, func(item *config.MonitorItem) bool {
				return item.Name == iName
			},
		)
		if idx < 0 {
			err := fmt.Errorf("item %s not found in items config", iName)
			slog.Error("run monitor item", slog.String("error", err.Error()))
			utils.SendMonitorEvent(
				"monitor-internal-error",
				fmt.Sprintf("item %s not found in items config", iName),
				nil,
			)
			continue
		}
		itemConfig := config.ItemsConfig[idx]
		if !itemConfig.IsMatchRole() {
			slog.Info("run monitor item role not match, skipped")
			continue
		}

		if constructor, ok := itemscollect.RegisteredItemConstructor()[iName]; ok {
			warnDB, msg, err := constructor(cc).Run()
			var customDim map[string]interface{}
			if warnDB != nil {
				customDim = map[string]interface{}{
					"instance_port": warnDB.Port,
					"instance_host": warnDB.Host,
				}
			}

			if err != nil {
				slog.Error("run monitor item", slog.String("error", err.Error()), slog.String("name", iName))
				utils.SendMonitorEvent(
					"monitor-internal-error",
					fmt.Sprintf("run monitor item %s failed: %s", iName, err.Error()),
					customDim,
				)
				continue
			}

			if msg != "" {
				slog.Info(
					"run monitor items",
					slog.String("msg", msg),
				)
				utils.SendMonitorEvent(iName, msg, customDim)
				continue
			}
			slog.Info("run monitor item pass")
		} else {
			err := errors.Errorf("%s not registered", iName)
			slog.Error("run monitor item", slog.String("error", err.Error()))
			continue
		}
	}

	// 还原 logger
	slog.SetDefault(config.Logger)

	slog.Info("main loop items-run finish")
	return nil
}

func getLocker(iNames []string) (*flock.Flock, error) {
	lockFileName := fmt.Sprintf("%d-%s.lock", config.MonitorConfig.Port, strings.Join(iNames, "."))
	lockFileBasePath := filepath.Join(cst.MySQLMonitorInstallPath, "locks")

	err := os.MkdirAll(lockFileBasePath, os.ModePerm)
	if err != nil {
		slog.Error(
			"main loop",
			slog.String("lock file base dir", lockFileBasePath),
			slog.String("err", err.Error()),
		)
		return nil, errors.WithStack(err)
	}

	lockFilePath := filepath.Join(lockFileBasePath, lockFileName)

	slog.Info("main loop", slog.String("lockFilePath", lockFilePath))

	//goland:noinspection GoResourceLeak
	fl := flock.New(lockFilePath) // 不会 leak

	locked, err := fl.TryLock()
	if err != nil {
		slog.Error(
			"main loop",
			slog.String("error", err.Error()),
		)
		_ = fl.Unlock()
		return nil, errors.WithStack(err)
	}

	if !locked {
		utils.SendMonitorEvent(
			"db-hang",
			fmt.Sprintf("last round %s not finish, db may be hang", strings.Join(iNames, ",")),
			nil,
		)
		_ = fl.Unlock()
		// TryLock 在锁被占用时 err 为 nil，不能用 Wrapf(err, ...)
		return nil, errors.Errorf("main loop lock file %s failed, may be last round not finish", lockFilePath)
	}

	slog.Info("main loop get lock success", slog.String("lockFilePath", lockFilePath))

	return fl, nil
}

func loadItems(hardcode bool) (iNames []string) {
	if hardcode {
		iNames = viper.GetStringSlice("hardcode-items")
	} else {
		iNames = viper.GetStringSlice("run-items")
	}
	slog.Info("main loop", slog.String("items", strings.Join(iNames, ",")))
	config.Logger = config.Logger.With("items", strings.Join(iNames, ","))
	slog.SetDefault(config.Logger)
	return iNames
}
