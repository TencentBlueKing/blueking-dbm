// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/precheck"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/spf13/cobra"
)

func init() {
	dumpCmd.Flags().String("backup-id", "", "overwrite Public.BackupId")
	dumpCmd.Flags().String("bill-id", "", "overwrite Public.BillId")
	dumpCmd.Flags().String("backup-type", cst.BackupLogical, "overwrite Public.BackupType")
	dumpCmd.Flags().Int("shard-value", -1, "overwrite Public.ShardValue")
	dumpCmd.Flags().String("file-tag", "", "overwrite BackupClient.FileTag")
	_ = viper.BindPFlag("Public.BackupId", dumpCmd.Flags().Lookup("backup-id"))
	_ = viper.BindPFlag("Public.BillId", dumpCmd.Flags().Lookup("bill-id"))
	_ = viper.BindPFlag("Public.BackupType", dumpCmd.Flags().Lookup("backup-type"))
	_ = viper.BindPFlag("Public.ShardValue", dumpCmd.Flags().Lookup("shard-value"))
	_ = viper.BindPFlag("BackupClient.FileTag", dumpCmd.Flags().Lookup("file-tag"))

	//dumpCmd.Flags().SetAnnotation("backup-type", "Public.BackupType", []string{"logical", "physical"})

	dumpCmd.Flags().StringSliceP("config", "c",
		[]string{}, "config files to backup, comma separated. (required)")
	_ = dumpCmd.MarkFlagRequired("config")
}

var dumpCmd = &cobra.Command{
	Use:   "dumpbackup",
	Short: "Run backup",
	Long:  `Run backup using config, include logical and physical`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		if err = logger.InitLog("dbbackup_dump.log"); err != nil {
			return err
		}
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
			var cnf = config.BackupConfig{}
			if err := initConfig(f, &cnf); err != nil {
				errList = append(errList, errors.WithMessage(err, f))
				logger.Log.Error("Create Dbbackup: fail to parse ", f)
				continue
			}
			//cnf.BackupClient.DoChecksum = true
			//cnf.BackupClient.Enable = true

			err := backupData(&cnf)
			if err != nil {
				logger.Log.Error("Create Dbbackup: Failure for ", f)
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

func backupData(cnf *config.BackupConfig) (err error) {
	logger.Log.Info("Dbbackup begin")
	// validate dumpBackup
	if err = validate.GoValidateStruct(cnf.Public, false, false); err != nil {
		return err
	}
	if cnf.Public.EncryptOpt == nil {
		cnf.Public.EncryptOpt = &cmutil.EncryptOpt{EncryptEnable: false}
	}
	encOpt := cnf.Public.EncryptOpt
	if encOpt.EncryptEnable {
		if encOpt.EncryptCmd == "xbcrypt" {
			encOpt.EncryptCmd = filepath.Join(backupexe.ExecuteHome, "bin/xbcrypt")
		}
		if err := encOpt.Init(); err != nil {
			return errors.Wrap(err, "fail to init crypt tool")
		}
		cnf.Public.EncryptOpt = encOpt
	}
	cnfPublic := cnf.Public

	logReport, err := dbareport.NewBackupLogReport(cnf)
	if err != nil {
		return err
	}
	// 初始化 reportLogger，后续可通过 dbareport.Report 来调用
	if err = dbareport.InitReporter(cnf.Public.ResultReportPath); err != nil {
		return err
	}
	err = logReport.ReportBackupStatus("Begin")
	if err != nil {
		logger.Log.Error("report begin failed: ", err)
		return err
	}
	logger.Log.Info("parse config file: end")
	if cnf.Public.DataSchemaGrant == cst.BackupNone {
		logger.Log.Info("backup nothing, exit")
		return nil
	}
	// backup grant info
	if cnf.Public.IfBackupGrant() {
		logger.Log.Info("backup Grant information: begin")
		if err := backupexe.GrantBackup(&cnfPublic); err != nil {
			logger.Log.Error("Failed to backup Grant information")
			return err
		}
		logger.Log.Info("backup Grant information: end")
	}
	if !cnf.Public.IfBackupData() && !cnf.Public.IfBackupSchema() {
		logger.Log.Info("no need to backup data or schema")
		return nil
	}

	if err := precheck.BeforeDump(&cnfPublic); err != nil {
		return err
	}

	// long_slow_query
	// check slave status

	// execute backup
	err = logReport.ReportBackupStatus("Backup")
	if err != nil {
		logger.Log.Error("report backup failed: ", err)
		return err
	}

	// ExecuteBackup 执行备份后，返回备份元数据信息
	metaInfo, exeErr := backupexe.ExecuteBackup(cnf)
	if exeErr != nil {
		return exeErr
	}

	// check the integrity of backup
	integrityErr := util.CheckIntegrity(&cnf.Public)
	if integrityErr != nil {
		logger.Log.Error("Failed to check the integrity of backup, error: ", integrityErr)
		return integrityErr
	}

	// tar and split
	err = logReport.ReportBackupStatus("Tar")
	if err != nil {
		logger.Log.Error("report tar failed: ", err)
		return err
	}
	// collect IndexContent info
	if err = logReport.BuildMetaInfo(&cnf.Public, metaInfo); err != nil {
		return err
	}

	// PackageBackupFiles 会把打包后的文件信息，更新到 metaInfo
	tarErr := backupexe.PackageBackupFiles(cnf, metaInfo)
	if tarErr != nil {
		logger.Log.Error("Failed to tar the backup file, error: ", tarErr)
		return tarErr
	}

	// report backup info to dba
	logger.Log.Info("report backup info: begin")
	if err = logReport.ReportBackupStatus("Report"); err != nil {
		return err
	}
	// run backup_client
	if err = logReport.ReportBackupResult(metaInfo); err != nil {
		logger.Log.Error("failed to report backup result, err: ", err)
		return err
	}
	logger.Log.Info("report backup info: end")

	err = logReport.ReportBackupStatus("Success")
	if err != nil {
		logger.Log.Error("report success failed: ", err)
		return err
	}
	logger.Log.Info("Dbbackup Success")
	return nil
}
