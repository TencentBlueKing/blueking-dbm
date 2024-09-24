// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"fmt"
	"math"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
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
	dumpCmd.Flags().String("backup-type", cst.BackupTypeAuto, "overwrite Public.BackupType")
	_ = viper.BindPFlag("Public.BackupType", dumpCmd.Flags().Lookup("backup-type"))

	dumpCmd.PersistentFlags().String("backup-id", "", "overwrite Public.BackupId")
	dumpCmd.PersistentFlags().String("bill-id", "", "overwrite Public.BillId")
	dumpCmd.PersistentFlags().Int("shard-value", -1, "overwrite Public.ShardValue")
	dumpCmd.PersistentFlags().Bool("nocheck-diskspace", false, "overwrite Public.NoCheckDiskSpace")
	dumpCmd.PersistentFlags().Bool("backup-client", false, "enable backup-client, overwrite BackupClient.Enable")
	dumpCmd.PersistentFlags().String("backup-file-tag", "", "overwrite BackupClient.FileTag")
	_ = viper.BindPFlag("Public.BackupId", dumpCmd.PersistentFlags().Lookup("backup-id"))
	_ = viper.BindPFlag("Public.BillId", dumpCmd.PersistentFlags().Lookup("bill-id"))
	_ = viper.BindPFlag("Public.ShardValue", dumpCmd.PersistentFlags().Lookup("shard-value"))
	_ = viper.BindPFlag("Public.NoCheckDiskSpace", dumpCmd.PersistentFlags().Lookup("nocheck-diskspace"))
	_ = viper.BindPFlag("BackupClient.Enable", dumpCmd.PersistentFlags().Lookup("backup-client"))
	_ = viper.BindPFlag("BackupClient.FileTag", dumpCmd.PersistentFlags().Lookup("backup-file-tag"))

	dumpCmd.PersistentFlags().String("data-schema-grant", "", "all|schema|data|grant, overwrite Public.DataSchemaGrant")
	dumpCmd.PersistentFlags().String("backup-dir", "/data/dbbak", "backup root path to save, overwrite Public.BackupDir")
	dumpCmd.PersistentFlags().String("cluster-domain", "", "cluster domain to report, overwrite Public.ClusterAddress")
	viper.BindPFlag("Public.DataSchemaGrant", dumpCmd.PersistentFlags().Lookup("data-schema-grant"))
	viper.BindPFlag("Public.BackupDir", dumpCmd.PersistentFlags().Lookup("backup-dir"))
	viper.BindPFlag("Public.ClusterAddress", dumpCmd.PersistentFlags().Lookup("cluster-domain"))
	//dumpCmd.PersistentFlags().SetAnnotation("backup-type", "Public.BackupType", []string{"logical", "physical"})

	// Connection Options
	dumpCmd.PersistentFlags().StringP("host", "h", "", "The host to connect to, overwrite Public.MysqlHost")
	dumpCmd.PersistentFlags().IntP("port", "P", 3306, "TCP/IP port to connect to, overwrite Public.MysqlPort")
	dumpCmd.PersistentFlags().StringP("user", "u", "", "Username with the necessary privileges, "+
		"overwrite Public.MysqlUser")
	dumpCmd.PersistentFlags().StringP("password", "p", "", "User password, overwrite Public.MysqlPasswd")
	viper.BindPFlag("Public.MysqlHost", dumpCmd.PersistentFlags().Lookup("host"))
	viper.BindPFlag("Public.MysqlPort", dumpCmd.PersistentFlags().Lookup("port"))
	viper.BindPFlag("Public.MysqlUser", dumpCmd.PersistentFlags().Lookup("user"))
	viper.BindPFlag("Public.MysqlPasswd", dumpCmd.PersistentFlags().Lookup("password"))

	dumpCmd.PersistentFlags().StringSliceP("config", "c",
		[]string{}, "config files to backup, comma separated. (required)")
	_ = dumpCmd.MarkFlagRequired("config")

	dumpCmd.AddCommand(dumpLogicalCmd)
}

var dumpCmd = &cobra.Command{
	Use:          "dumpbackup",
	Short:        "Run backup",
	Long:         `Run backup using config, include logical and physical`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", cst.DbbackupGoInstallPath)
		}()
		if err = dumpExecute(cmd, args); err != nil {
			logger.Log.Error("dumpbackup failed", err.Error())
			manager := ma.NewManager(cst.MysqlCrondUrl)
			body := struct {
				Name      string
				Content   string
				Dimension map[string]interface{}
			}{}
			body.Name = "dbbackup-by-host"
			body.Content = fmt.Sprintf("run dbbackup failed %s", err.Error())
			if sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension); sendErr != nil {
				logger.Log.Error("SendEvent failed", sendErr.Error())
			}
			return err
		}
		return nil
	},
}

func dumpExecute(cmd *cobra.Command, args []string) (err error) {
	manager := ma.NewManager(cst.MysqlCrondUrl)
	body := struct {
		Name      string
		Content   string
		Dimension map[string]interface{}
	}{}
	body.Name = "dbbackup"
	//body.Content = fmt.Sprintf("%s。单据号：%s", "分区任务执行失败", e.Params.Ticket)
	body.Dimension = make(map[string]interface{})
	if err = logger.InitLog("dbbackup_dump.log"); err != nil {
		return err
	}
	cnfFiles, _ := cmd.PersistentFlags().GetStringSlice("config") // PersistentFlags global flags
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
		config.SetDefaults()
		var cnf = config.BackupConfig{}
		if err := initConfig(f, &cnf); err != nil {
			errList = append(errList, errors.WithMessage(err, f))
			logger.Log.Error("Create Dbbackup: fail to parse ", f)
			continue
		}
		// 如果本机是 master 且设置了 master 限速，则覆盖默认限速
		if cnf.Public.IOLimitMasterFactor > 0.0001 && cnf.Public.MysqlRole == cst.RoleMaster {
			cnf.Public.IOLimitMBPerSec = int(math.Max(10,
				cnf.Public.IOLimitMasterFactor*float64(cnf.Public.IOLimitMBPerSec)))
			cnf.PhysicalBackup.Throttle = int(math.Max(1,
				cnf.Public.IOLimitMasterFactor*float64(cnf.PhysicalBackup.Throttle)))
		}

		err := backupData(&cnf)
		if err != nil {
			logger.Log.Error("Create Dbbackup: Failure for ", f)
			errList = append(errList, errors.WithMessage(err, f))
			body.Dimension["bk_biz_id"] = cnf.Public.BkBizId
			body.Dimension["cluster_domain"] = cnf.Public.ClusterAddress
			body.Dimension["instance"] = fmt.Sprintf("%s:%d", cnf.Public.MysqlHost, cnf.Public.MysqlPort)
			body.Content = fmt.Sprintf("run dbbackup failed for %s", f)
			if sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension); sendErr != nil {
				logger.Log.Error("SendEvent failed for ", f, sendErr.Error())
			}
			continue
		}
	}
	if len(errList) > 0 {
		return errors.Errorf("%v", errList)
	}
	return nil
}

func backupData(cnf *config.BackupConfig) (err error) {
	logger.Log.Infof("Dbbackup begin for %d", cnf.Public.MysqlPort)
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
	if err = dbareport.InitReporter(cnf.Public.ReportPath); err != nil {
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
	if err := precheck.BeforeDump(cnf); err != nil {
		return err
	}

	// 备份权限 backup priv info
	if cnf.Public.IfBackupGrant() {
		logger.Log.Infof("backup grant for %d: begin", cnf.Public.MysqlPort)
		if err := backupexe.BackupGrant(&cnfPublic); err != nil {
			logger.Log.Error("Failed to backup Grant information")
			return err
		}
		logger.Log.Info("backup Grant information: end")
	}
	if !cnf.Public.IfBackupData() && !cnf.Public.IfBackupSchema() {
		logger.Log.Info("no need to backup data or schema")
		return nil
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
	indexFilePath, tarErr := backupexe.PackageBackupFiles(cnf, metaInfo)
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
	fmt.Printf("backup_index_file:%s\n", indexFilePath)
	if err = logReport.ReportBackupResult(indexFilePath, true, true); err != nil {
		logger.Log.Error("failed to report backup result, err: ", err)
		return err
	}
	logger.Log.Info("report backup info: end")

	err = logReport.ReportBackupStatus("Success")
	if err != nil {
		logger.Log.Error("report success failed: ", err)
		return err
	}
	logger.Log.Infof("Dbbackup Success for %d", cnf.Public.MysqlPort)
	return nil
}
