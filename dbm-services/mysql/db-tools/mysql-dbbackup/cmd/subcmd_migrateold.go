// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	errors2 "errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	migrateOldCmd.Flags().StringSliceP("config", "c",
		[]string{}, "config files to backup, comma separated")
	migrateOldCmd.Flags().String("infoFile", "", "info file path to migrate. /data/dbbak/backupinfo/")
}

var migrateOldCmd = &cobra.Command{
	Use:   "migrateold",
	Short: "migrate old backup .info to .index",
	RunE: func(cmd *cobra.Command, args []string) error {
		oldBackupDir := "/home/mysql/dbbackup"
		if !cmutil.FileExists(oldBackupDir) {
			// 老dbbackup不存在
			fmt.Println("dir not exists", oldBackupDir)
			return nil
		}

		if err := logger.InitLog("dbbackup_dump.log"); err != nil {
			return err
		}
		infoFile, _ := cmd.Flags().GetString("infoFile")
		flagFile := filepath.Join(oldBackupDir, "dbbackup-go-migrate.done") // 没有指定 infoFile 时判断 done 文件

		if infoFile != "" || !cmutil.FileExists(flagFile) {
			if err := migrateOld(cmd, args); err != nil {
				return err
			}
			// 完成全量或者指定infoFile migrate
		}
		if infoFile == "" { // 全量
			if cmutil.FileExists(flagFile) {
				// 已经migrate
				fmt.Println("already done", flagFile)
				return nil
			} else if err := os.WriteFile(flagFile, []byte("ok"), 0755); err != nil {
				return errors.WithMessagef(err, "fail to write flag file %s:ok", flagFile)
			}
		}
		return nil
	},
}

// migrateOld 将旧的 .info 格式转换成新的 .index 格式
// 让旧备份兼容回档逻辑
func migrateOld(cmd *cobra.Command, args []string) (errs error) {
	var err error
	cnfFiles, _ := cmd.Flags().GetStringSlice("config")
	if len(cnfFiles) == 0 {
		if cnfFiles, err = filepath.Glob("dbbackup.*.ini"); err != nil {
			return err
		} else if len(cnfFiles) == 0 {
			fmt.Println("no dbbackup.*.ini found, ignore")
			return nil
		}
	}
	fmt.Println("config files", cnfFiles)
	infoFile, _ := cmd.Flags().GetString("infoFile")

	viper.SetConfigType("ini")
	for _, f := range cnfFiles {
		var cnf = config.BackupConfig{}
		viper.SetConfigFile(f)
		if err = viper.ReadInConfig(); err != nil {
			errs = errors2.Join(errs, err)
			continue
		}
		if err = viper.Unmarshal(&cnf); err != nil {
			errs = errors2.Join(errs, err)
			continue
		}
		if cnf.Public.EncryptOpt == nil {
			cnf.Public.EncryptOpt = &cmutil.EncryptOpt{EncryptEnable: false}
		}
		if err = dbareport.InitReporter(cnf.Public.ReportPath); err != nil {
			return err
		}
		var files = []string{infoFile}
		if infoFile == "" {
			infoFilesMath := fmt.Sprintf("/data/dbbak/backupinfo/*%d*.info", cnf.Public.MysqlPort)
			if files, err = filepath.Glob(infoFilesMath); err != nil {
				errs = errors2.Join(errs, err)
				continue
			}
		} else if !strings.Contains(infoFile, "/data/dbbak/backupinfo") {
			errs = errors2.Join(errs, errors.Errorf("infoFile need /data/dbbak/backupinfo, %s", infoFile))
			continue
		}
		for _, infoFilePath := range files {
			if indexFilePath, indexContent, err := backupexe.MigrateInstanceBackupInfo(infoFilePath, &cnf); err != nil {
				errMsg := fmt.Sprintf("failed migrate backup info port %d\n: %s", cnf.Public.MysqlPort, err.Error())
				errs = errors2.Join(errs, errors.New(errMsg))
				continue
			} else {
				fmt.Println("migrate infoFile", infoFilePath)
				cnf.Public.BackupId = indexContent.BackupId
				report, err := dbareport.NewBackupLogReport(&cnf)
				if err != nil {
					errs = errors2.Join(errs, err)
					continue
				}
				if err = report.ReportBackupResult(indexFilePath, false, false); err != nil {
					errs = errors2.Join(errs, err)
				} else {
					fmt.Println("report success", indexFilePath)
				}
			}
		}
	}
	return errs
}
