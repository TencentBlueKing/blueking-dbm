package cmd

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/spider"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

var spiderCmd = &cobra.Command{
	Use:   "spiderbackup",
	Short: "Run spider backup",
	Long:  `Run spider backup task`,
}

func init() {

	// spiderbackup schedule
	spiderScheduleCmd.Flags().Bool("wait", false, "wait task done")
	_ = viper.BindPFlag("schedule.wait", spiderScheduleCmd.Flags().Lookup("wait"))
	spiderScheduleCmd.Flags().String("backup-id", "", "overwrite Public.BackupId")
	spiderScheduleCmd.Flags().StringSliceP("config", "c", []string{},
		"spider dbbackup ini file. If not given, will auto-detect dbbackup.*.ini to determine spider dbbackup ini")

	// spiderbackup check
	spiderCheckCmd.Flags().StringSliceP("config", "c", []string{},
		"config files to check, comma separated. if not given, will find dbbackup.*.ini. Using with --check")
	spiderCheckCmd.Flags().Bool("run", false, "run dbbackup if --check have tasks")
	_ = viper.BindPFlag("check.run", spiderCheckCmd.Flags().Lookup("run"))

	// spiderbackup query
	spiderQueryCmd.Flags().StringSlice("BackupStatus", []string{}, "BackupStatus filter, comma separated")
	spiderQueryCmd.Flags().String("BackupId", "", "BackupId filter")
	// format 只允许 json,table
	formatOpt, _ := cmutil.NewPflagEnum("format", "table", []string{"table", "json"})
	spiderQueryCmd.Flags().Var(formatOpt, formatOpt.Name(),
		fmt.Sprintf("output format, allowed %v", formatOpt.Choices()))
	_ = formatOpt.SetChoices(spiderQueryCmd.Flags())
	_ = viper.BindPFlag("query.format", spiderQueryCmd.Flags().Lookup("format"))

	//spiderCmd.MarkFlagsMutuallyExclusive("schedule", "check", "query")
	//spiderCmd.MarkFlagRequired("config)

	spiderCmd.AddCommand(spiderScheduleCmd)
	spiderCmd.AddCommand(spiderCheckCmd)
	spiderCmd.AddCommand(spiderQueryCmd)
}

func findSpiderBackupConfigFile(cnfFiles []string) (string, error) {
	if len(cnfFiles) == 1 {
		return cnfFiles[0], nil
	} else if len(cnfFiles) != 2 {
		return "", errors.New("unable to determine spider dbbackup ini ")
	} else {
		var ports []int
		for _, cf := range cnfFiles {
			var port int
			if ps := strings.Split(filepath.Base(cf), "."); len(ps) != 3 {
				logger.Log.Warn("invalid backup config file name %s", cf)
			} else {
				port = cast.ToInt(ps[1])
			}
			if port != 0 {
				ports = append(ports, port)
			} else {
				return "", errors.Errorf("invalid backup config file name %s", cf)
			}
		}
		sort.Ints(ports)
		spiderPort := ports[0]
		tdbctlPortExpect := mysqlcomm.GetTdbctlPortBySpider(spiderPort)
		if ports[1] != tdbctlPortExpect {
			return "", errors.Errorf("tdbctl port expect %d but got %d", tdbctlPortExpect, ports[1])
		}
		// expect dbbackup.*.ini
		configFile := fmt.Sprintf("dbbackup.%d.ini", spiderPort)
		logger.Log.Infof("found spider dbbackup ini: %s", configFile)
		return configFile, nil
	}
}

var spiderScheduleCmd = &cobra.Command{
	Use:   "schedule",
	Short: "spiderbackup schedule",
	Long:  `Start spider global backup. Will initialize backup tasks using one backup-id, only run on spider master`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := logger.InitLog("dbbackup_spider.log"); err != nil {
			return err
		}
		// 本地应该有 spider 和 tdbctl 2 个 backup ini, 自动找到 spider port
		// 如果只有一个 backup ini，则认为它就是 spider port
		cnfFiles, err := spiderCmdHandleConfig(cmd)
		if err != nil {
			return err
		}
		configFile, err := findSpiderBackupConfigFile(cnfFiles)
		if err != nil {
			return err
		}
		var cnf = config.BackupConfig{}
		if err := initConfig(configFile, &cnf); err != nil {
			return err
		}
		cnf.Public.BackupId, _ = cmd.Flags().GetString("backup-id")
		err = spider.ScheduleBackup(&cnf.Public)
		if err != nil {
			logger.Log.Error("Spider Schedule: Failure")
			return err
		}
		return nil
	},
}

var spiderCheckCmd = &cobra.Command{
	Use:   "check",
	Short: "spiderbackup check",
	Long:  `Check or run backup todo tasks`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := logger.InitLog("dbbackup_spider.log"); err != nil {
			return err
		}
		cnfFiles, err := spiderCmdHandleConfig(cmd)
		if err != nil {
			return err
		}
		publicConfigs, err := batchParseCnfFiles(cnfFiles)
		if err != nil {
			return err
		}
		err = spider.RunBackupTasks(publicConfigs)
		if err != nil {
			logger.Log.Error("Spider Check: Failure")
			return err
		}
		return nil
	},
}

var spiderQueryCmd = &cobra.Command{
	Use:   "query",
	Short: "spiderbackup query",
	Long:  `Query spider backup task status, only run on spider master`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := logger.InitLog("dbbackup_spider.log"); err != nil {
			return err
		}
		cnfFiles, err := spiderCmdHandleConfig(cmd)
		if err != nil {
			return err
		}
		configFile, err := findSpiderBackupConfigFile(cnfFiles)
		if err != nil {
			return err
		}
		var cnf = config.BackupConfig{}
		if err := initConfig(configFile, &cnf); err != nil {
			return err
		}
		cnf.Public.BackupId, _ = cmd.Flags().GetString("BackupId")
		backupStatus, _ := cmd.Flags().GetStringSlice("BackupStatus")
		err = spider.QueryBackup(&cnf.Public, backupStatus)
		if err != nil {
			logger.Log.Error("Spider Query: Failure")
			return err
		}
		return nil
	},
}

func spiderCmdHandleConfig(cmd *cobra.Command) (cnfFiles []string, err error) {
	cnfFiles, _ = cmd.Flags().GetStringSlice("config")
	if len(cnfFiles) == 0 {
		if cnfFiles, err = util.FindBackupConfigFiles(""); err != nil {
			return nil, err
		} else if len(cnfFiles) == 0 {
			return nil, errors.New("no dbbackup.*.ini found")
		}
	}
	logger.Log.Infof("using config files: %v", cnfFiles)
	return cnfFiles, nil
}

func batchParseCnfFiles(cnfFiles []string) ([]*config.Public, error) {
	var publicConfigs []*config.Public
	var backupId = viper.GetString("backup-id")
	for _, cnfFilename := range cnfFiles {
		var backupConfig = config.BackupConfig{}
		if err := initConfig(cnfFilename, &backupConfig); err != nil {
			return nil, err
		}
		backupConfig.Public.BackupId = backupId
		backupConfig.Public.SetCnfFileName(cnfFilename)
		publicConfigs = append(publicConfigs, &backupConfig.Public)
	}
	return publicConfigs, nil
}
