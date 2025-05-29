// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	errs "errors"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	uploadCmd.Flags().String("backup-index-file", "", "read backup info from this index file")
	uploadCmd.Flags().String("backup-target-dir", "", "backup target dir that has exported before")
	uploadCmd.Flags().StringSliceP("config", "c",
		[]string{}, "config files to backup, comma separated. (required)")
	_ = uploadCmd.MarkFlagRequired("config")
	_ = uploadCmd.MarkFlagRequired("backup-index-file")
}

var uploadCmd = &cobra.Command{
	Use:          "tar-upload",
	Short:        "Run tar and upload only",
	Long:         `Run backup using config, include logical and physical`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql:mysql", cst.DbbackupGoInstallPath)
		}()
		if err = tarAndUpload(cmd, args); err != nil {
			return err
		}
		return nil
	},
}

func tarAndUpload(cmd *cobra.Command, args []string) (err error) {
	if err = logger.InitLog("dbbackup_tar.log"); err != nil {
		return err
	}
	cnfFiles, _ := cmd.Flags().GetStringSlice("config") // PersistentFlags global flags
	if len(cnfFiles) == 0 {
		if cnfFiles, err = filepath.Glob("dbbackup.*.ini"); err != nil {
			return err
		} else if len(cnfFiles) == 0 {
			return errors.New("no dbbackup.*.ini found")
		}
	}
	logger.Log.Infof("using config files: %v", cnfFiles)

	f := cnfFiles[0]
	var errList error
	config.SetDefaults()
	var cnf = config.BackupConfig{}
	if err := initConfig(f, &cnf, logger.Log); err != nil {
		errList = errs.Join(errList, errors.WithMessagef(err, "init failed for %d", cnf.Public.MysqlPort))
		logger.Log.Error("Create Dbbackup: fail to parse ", f)
	}
	indexFilePath, _ := cmd.Flags().GetString("backup-index-file")
	return tarBackupData(indexFilePath, &cnf)
}

func tarBackupData(indexFilePath string, cnf *config.BackupConfig) (err error) {
	// validate dumpBackup
	if err = validate.GoValidateStructTag(cnf.Public, "ini"); err != nil {
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

	logReport, err := dbareport.NewBackupLogReport(cnf)
	if err != nil {
		return err
	}
	// 初始化 reportLogger，后续可通过 dbareport.Report 来调用
	if err = dbareport.InitReporter(cnf.Public.ReportPath); err != nil {
		return err
	}

	if err = backupTarAndUpload(cnf, indexFilePath, logReport); err != nil {
		return err
	}
	logger.Log.Infof("Dbbackup tar-upload for %d", cnf.Public.MysqlPort)
	return nil
}
