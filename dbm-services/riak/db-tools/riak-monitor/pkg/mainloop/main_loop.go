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
	"strings"

	"dbm-services/riak/db-tools/riak-monitor/pkg/config"
	"dbm-services/riak/db-tools/riak-monitor/pkg/itemscollect"
	"dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"

	_ "github.com/go-sql-driver/mysql" // mysql TODO
	"github.com/pkg/errors"
	"github.com/spf13/viper"
	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
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

	if hardcode && slices.Index(iNames, config.HeartBeatName) >= 0 {
		utils.SendMonitorMetrics(config.HeartBeatName, 1, nil)
	}

	cc, err := monitoriteminterface.NewConnectionCollect()
	if err != nil {
		if hardcode && slices.Index(iNames, "riak-db-up") >= 0 {
			utils.SendMonitorEvent("riak-db-up", err.Error())
		}
		return nil
	}

	if hardcode {
		return nil
	}

	for _, iName := range iNames {

		if constructor, ok := itemscollect.RegisteredItemConstructor()[iName]; ok {
			msg, err := constructor(cc).Run()
			if err != nil {
				slog.Error("run monitor item", err, slog.String("name", iName))
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
			slog.Error("run monitor item", err)
			continue
		}
	}
	return nil
}
