package main_loop

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

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

	cc, err := monitor_item_interface.NewConnectionCollect()
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

		if constructor, ok := items_collect.RegisteredItemConstructor()[iName]; ok {
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
