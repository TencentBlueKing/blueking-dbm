package cmd

import (
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/precheck"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/spf13/cobra"
)

func init() {
	dumpCmd.Flags().String("backup-id", "", "overwrite Public.BackupId")
	dumpCmd.Flags().String("bill-id", "", "overwrite Public.BillId")
	dumpCmd.Flags().String("backup-type", "logical", "overwrite Public.BackupType")
	dumpCmd.Flags().Int("shard-value", -1, "overwrite Public.ShardValue")
	dumpCmd.Flags().String("file-tag", "", "overwrite BackupClient.FileTag")
	_ = viper.BindPFlag("Public.BackupId", dumpCmd.Flags().Lookup("backup-id"))
	_ = viper.BindPFlag("Public.BillId", dumpCmd.Flags().Lookup("bill-id"))
	_ = viper.BindPFlag("Public.BackupType", dumpCmd.Flags().Lookup("backup-type"))
	_ = viper.BindPFlag("Public.ShardValue", dumpCmd.Flags().Lookup("shard-value"))
	_ = viper.BindPFlag("BackupClient.FileTag", dumpCmd.Flags().Lookup("file-tag"))
	// dumpCmd.Flags().SetAnnotation("backup-type", "Public.BackupType", []string{"logical", "physical"})
	dumpCmd.Flags().StringSliceP("config", "c", []string{}, "config files to backup, comma separated. (required)")
	_ = dumpCmd.MarkFlagRequired("config")
}

var dumpCmd = &cobra.Command{
	Use:   "dumpbackup",
	Short: "Run backup",
	Long:  `Run backup using config, include logical and physical`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		cnfFiles, _ := cmd.Flags().GetStringSlice("config")
		if len(cnfFiles) == 0 {
			if cnfFiles, err = filepath.Glob("dbbackup.*.ini"); err != nil {
				return err
			} else if len(cnfFiles) == 0 {
				return errors.New("no dbbackup.*.ini found")
			}
		}
		logger.Log.Infof("using config files: %v", cnfFiles)

		var errList []error
		for _, f := range cnfFiles {
			var cnf = parsecnf.Cnf{}
			if err := initConfig(f, &cnf); err != nil {
				errList = append(errList, errors.WithMessage(err, f))
				logger.Log.Error("Create Dbbackup: fail to parse %d", f)
				continue
			}
			cnf.BackupClient.DoChecksum = true
			cnf.BackupClient.Enable = true
			if cnf.Public.ClusterId == "" {
				cnf.Public.ClusterId = "0"
			}
			err := backupData(&cnf)
			if err != nil {
				// dbareport.ReportBackupStatus("Failure", ConfigResult)
				logger.Log.Error("Create Dbbackup: Failure for %d", f)
				errList = append(errList, errors.WithMessage(err, f))
				continue
			}
		}
		if len(errList) > 0 {
			return errors.Errorf("%v", errList)
		}
		return nil
	},
}

func backupData(cnf *parsecnf.Cnf) error {
	logger.Log.Info("begin backup")

	// validate dumpBackup
	if err := validate.GoValidateStruct(cnf.Public); err != nil {
		return err
	}
	if err := cnf.Public.ParseDataSchemaGrant(); err != nil {
		return err
	}
	cnfPublic := cnf.Public

	DBAReporter, err := dbareport.NewReporter(cnf)
	if err != nil {
		return err
	}

	DBAReporter.ReportBackupStatus("Begin")
	logger.Log.Info("parse config file: end")

	// produce a unique targetname
	var tnameErr error
	common.TargetName, tnameErr = backupexe.GetTargetName(&cnfPublic)
	if tnameErr != nil {
		return tnameErr
	}

	// backup grant info
	if common.BackupGrant {
		logger.Log.Info("backup Grant information: begin")
		if err := backupexe.GrantBackup(&cnfPublic); err != nil {
			logger.Log.Error("Failed to backup Grant information")
			return err
		}
		logger.Log.Info("backup Grant information: end")
	}
	if !common.BackupData && !common.BackupSchema {
		logger.Log.Info("no need to backup data or schema")
		return nil
	}

	if err := precheck.PrecheckBeforeDump(&cnfPublic); err != nil {
		return err
	}

	// long_slow_query
	// check slave status

	// execute backup
	DBAReporter.ReportBackupStatus("Backup")
	exeErr := backupexe.ExecuteBackup(cnf)
	if exeErr != nil {
		return exeErr
	}

	// check the integrity of backup
	integrityErr := util.CheckIntegrity(cnf.Public.BackupType, cnf.Public.BackupDir)
	if integrityErr != nil {
		logger.Log.Error("Failed to check the integrity of backup, error: ", integrityErr)
		return integrityErr
	}

	var baseBackupResult dbareport.BackupResult
	if err := baseBackupResult.BuildBaseBackupResult(cnf, DBAReporter.Uuid); err != nil {
		return err
	}

	// tar and split
	DBAReporter.ReportBackupStatus("Tar")
	tarErr := backupexe.PackageBackupFiles(cnf, &baseBackupResult)
	if tarErr != nil {
		logger.Log.Error("Failed to tar the backup file, error: ", tarErr)
		return tarErr
	}

	// report backup info to dba
	logger.Log.Info("report backup info: begin")
	if err = DBAReporter.ReportBackupStatus("Report"); err != nil {
		return err
	}
	// if err = dbareport.ReportCnf(ConfigResult); err != nil {
	//	return err
	// }
	if err = DBAReporter.ReportBackupResult(baseBackupResult); err != nil {
		logger.Log.Error("failed to report backup result, err: ", err)
		return err
	}
	logger.Log.Info("report backup info: end")
	DBAReporter.ReportBackupStatus("Success")
	logger.Log.Info("Dbbackup Success")
	return nil
}
