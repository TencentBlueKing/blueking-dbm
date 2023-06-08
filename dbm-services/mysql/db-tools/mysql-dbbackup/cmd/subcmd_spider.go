package cmd

import (
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/spider"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

func init() {
	// spiderCmd
	spiderCmd.Flags().Bool("schedule", false, "schedule back tasks")
	spiderCmd.Flags().Bool("wait", false, "wait task done when using --schedule")
	_ = viper.BindPFlag("schedule.wait", spiderCmd.Flags().Lookup("wait"))

	spiderCmd.Flags().String("backup-id", "", "overwrite Public.BackupId")
	_ = viper.BindPFlag("Public.BackupId", dumpCmd.Flags().Lookup("backup-id"))

	spiderCmd.Flags().Bool("check", false, "check backup tasks to run")
	spiderCmd.Flags().StringSliceP("config", "c", []string{}, "config files to check, comma separated. "+
		"if not given, will find dbbackup.*.ini. Using with --check")
	spiderCmd.Flags().Bool("run", false, "run dbbackup if --check have tasks")
	_ = viper.BindPFlag("check.run", spiderCmd.Flags().Lookup("run"))

	spiderCmd.MarkFlagsMutuallyExclusive("schedule", "check")
	// spiderCmd.Flags().Bool("addSchedule", false, "add schedule to mysql-crond")
	// spiderCmd.Flags().Bool("delSchedule", false, "del schedule from mysql-crond")
	// spiderCmd.MarkFlagsMutuallyExclusive("addSchedule", "delSchedule")
}

var spiderCmd = &cobra.Command{
	Use:   "spiderbackup",
	Short: "Run spider backup",
	Long:  `Run spider backup task`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		cnfFiles, _ := cmd.Flags().GetStringSlice("config")
		if len(cnfFiles) == 0 {
			if cnfFiles, err = util.FindBackupConfigFiles(""); err != nil {
				return err
			} else if len(cnfFiles) == 0 {
				return errors.New("no dbbackup.*.ini found")
			}
		}
		logger.Log.Infof("using config files: %v", cnfFiles)

		if ok, _ := cmd.Flags().GetBool("schedule"); ok {
			if len(cnfFiles) != 1 {
				return errors.Errorf("--schedule expect one config, but got:%v", cnfFiles)
			}
			var cnf = parsecnf.Cnf{}
			if err := initConfig(cnfFiles[0], &cnf); err != nil {
				return err
			}
			if backupId := viper.GetString("backup-id"); backupId != "" {
				cnf.Public.BackupId = backupId
			}
			err = spider.ScheduleBackup(&cnf.Public)
		} else if ok, _ = cmd.Flags().GetBool("check"); ok {
			cnfObjs, err := batchParseCnfFiles(cnfFiles)
			if err != nil {
				return err
			}
			return spider.RunBackupTasks(cnfObjs)
		} else {
			return errors.New("need --schedule or --check")
		}
		if err != nil {
			logger.Log.Error("Spider backup: Failure")
			return err
		}
		return nil
	},
}

func batchParseCnfFiles(cnfFiles []string) ([]*parsecnf.CnfShared, error) {
	var cnfObjs []*parsecnf.CnfShared
	var backupId = viper.GetString("backup-id")
	for _, cnfFilename := range cnfFiles {
		var cnfObj = parsecnf.Cnf{}
		if err := initConfig(cnfFilename, &cnfObj); err != nil {
			return nil, err
		}
		cnfObj.Public.BackupId = backupId
		cnfObj.Public.SetCnfFileName(cnfFilename)
		cnfObjs = append(cnfObjs, &cnfObj.Public)
	}
	return cnfObjs, nil
}
