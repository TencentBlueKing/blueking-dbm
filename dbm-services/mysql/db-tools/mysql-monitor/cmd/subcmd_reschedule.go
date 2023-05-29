package cmd

import (
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

var subCmdReschedule = &cobra.Command{
	Use:   "reschedule",
	Short: "reschedule mysql-crond entry",
	Long:  "reschedule mysql-crond entry",
	RunE: func(cmd *cobra.Command, args []string) error {
		/*
			就只有这个子命令需要这样把配置转换成绝对路径
			因为注册到crond后cwd是其他目录了
		*/
		configPath := viper.GetString("reschedule-config")
		if !filepath.IsAbs(configPath) {
			cwd, err := os.Getwd()
			if err != nil {
				slog.Error("reschedule get config abs path", err)
				return err
			}
			configPath = filepath.Join(cwd, configPath)
		}
		configFileDir, configFileName := filepath.Split(configPath)

		err := config.InitConfig(configPath)
		if err != nil {
			return err
		}
		initLogger(config.MonitorConfig.Log)

		err = config.LoadMonitorItemsConfig()
		if err != nil {
			slog.Error("reschedule load items", err)
			return err
		}

		config.InjectHardCodeItem()

		err = config.WriteMonitorItemsBack()
		if err != nil {
			slog.Error("reschedule write back items", err)
			return err
		}

		manager := ma.NewManager(config.MonitorConfig.ApiUrl)
		entries, err := manager.Entries()
		if err != nil {
			slog.Error("reschedule list entries", err)
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
						"reschedule delete entry", err,
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
			eid, err := manager.CreateOrReplace(
				ma.JobDefine{
					Name:     fmt.Sprintf("mysql-monitor-%d-%s", config.MonitorConfig.Port, k),
					Command:  executable,
					Args:     args,
					Schedule: k,
					Creator:  viper.GetString("staff"),
					Enable:   true,
					WorkDir:  configFileDir,
				}, true,
			)
			if err != nil {
				slog.Error("reschedule add entry", err)
				return err
			}
			slog.Info("reschedule add entry", slog.Int("entry id", eid))
		}

		// 注册 hardcode
		var itemNames []string
		for _, j := range hardCodeItems {
			itemNames = append(itemNames, j.Name)
		}
		args = []string{
			"hardcode-run",
			"--items", strings.Join(itemNames, ","),
			"-c", configPath,
		}
		eid, err := manager.CreateOrReplace(
			ma.JobDefine{
				Name:     fmt.Sprintf("mysql-monitor-%d-hardcode", config.MonitorConfig.Port),
				Command:  executable,
				Args:     args,
				Schedule: config.HardCodeSchedule,
				Creator:  viper.GetString("staff"),
				Enable:   true,
			}, true,
		)
		if err != nil {
			slog.Error("reschedule add hardcode entry", err)
			return err
		}
		slog.Info("reschedule add hardcode entry", slog.Int("entry id", eid))

		return nil
	},
}

func init() {
	subCmdReschedule.PersistentFlags().StringP("config", "c", "", "config file")
	_ = subCmdReschedule.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("reschedule-config", subCmdReschedule.PersistentFlags().Lookup("config"))

	subCmdReschedule.PersistentFlags().StringP("staff", "", "", "staff name")
	_ = subCmdReschedule.MarkPersistentFlagRequired("staff")
	_ = viper.BindPFlag("staff", subCmdReschedule.PersistentFlags().Lookup("staff"))

	rootCmd.AddCommand(subCmdReschedule)
}
