package cmd

import (
	"fmt"
	"log/slog"
	"strings"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func reschedule(configFileDir, configFileName, staff string) error {
	manager := ma.NewManager(config.MonitorConfig.ApiUrl)
	entries, err := manager.Entries()
	if err != nil {
		slog.Error("reschedule list entries", slog.String("error", err.Error()))
		return err
	}

	for _, entry := range entries {
		if strings.HasPrefix(
			entry.Job.Name,
			fmt.Sprintf("mysql-monitor-%d", config.MonitorConfig.Port),
		) {
			eid, err := manager.Delete(entry.Job.Name, true)
			if err != nil {
				slog.Error(
					"reschedule delete entry",
					slog.String("error", err.Error()),
					slog.String("name", entry.Job.Name),
				)
				return err
			}
			slog.Info(
				"reschedule delete entry",
				slog.String("name", entry.Job.Name),
				slog.Int("ID", eid),
			)
		}
	}

	var hardCodeItems []*config.MonitorItem
	itemGroups := make(map[string][]*config.MonitorItem)
	for _, ele := range config.ItemsConfig {
		// 硬编码监控项先排除掉
		if ele.Name == "db-up" || ele.Name == config.HeartBeatName {
			if ele.IsEnable() {
				hardCodeItems = append(hardCodeItems, ele)
			}
			continue
		}

		if ele.IsEnable() && ele.IsMatchMachineType() && ele.IsMatchRole() {
			var key string

			if ele.Schedule == nil {
				key = config.MonitorConfig.DefaultSchedule
			} else {
				key = *ele.Schedule
			}

			if _, ok := itemGroups[key]; !ok {
				itemGroups[key] = []*config.MonitorItem{}
			}
			itemGroups[key] = append(itemGroups[key], ele)
		}
	}

	for k, v := range itemGroups {
		var itemNames []string
		for _, j := range v {
			itemNames = append(itemNames, j.Name)
		}
		args := []string{
			"run",
			"--items", strings.Join(itemNames, ","),
			"-c", configFileName, // use WorkDir
		}

		jobDefine := ma.JobDefine{
			Name:     fmt.Sprintf("mysql-monitor-%d-%s", config.MonitorConfig.Port, k),
			Command:  executable,
			Args:     args,
			Schedule: k,
			Creator:  staff, //viper.GetString("staff"),
			Enable:   true,
			WorkDir:  configFileDir,
			Overlap:  true,
		}
		slog.Info("reschedule", slog.Any("job define", jobDefine))

		eid, err := manager.CreateOrReplace(jobDefine, true)
		if err != nil {
			slog.Error("reschedule add entry", slog.String("error", err.Error()))
			return err
		}
		slog.Info("reschedule add entry", slog.Int("entry id", eid))
	}

	// 注册 hardcode
	for _, j := range hardCodeItems {
		args := []string{
			"hardcode-run",
			"--items", j.Name, //strings.Join(itemNames, ","),
			"-c", configFileName,
		}

		eid, err := manager.CreateOrReplace(
			ma.JobDefine{
				Name: fmt.Sprintf(
					"mysql-monitor-%d-hardcode-%s", config.MonitorConfig.Port, j.Name),
				Command:  executable,
				Args:     args,
				Schedule: config.HardCodeSchedule,
				Creator:  staff, //viper.GetString("staff"),
				Enable:   true,
				WorkDir:  configFileDir,
			}, true,
		)
		if err != nil {
			slog.Error("reschedule add hardcode entry", slog.String("error", err.Error()))
			return err
		}
		slog.Info("reschedule add hardcode entry", slog.Int("entry id", eid))
	}

	return nil
}
