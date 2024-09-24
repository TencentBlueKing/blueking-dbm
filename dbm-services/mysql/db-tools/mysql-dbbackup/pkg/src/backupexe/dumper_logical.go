/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package backupexe

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// LogicalDumper TODO
type LogicalDumper struct {
	cnf             *config.BackupConfig
	dbbackupHome    string
	backupStartTime time.Time
	backupEndTime   time.Time
}

func (l *LogicalDumper) initConfig(mysqlVerStr string) error {
	if l.cnf == nil {
		return errors.New("logical dumper params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}
	BackupTool = cst.ToolMydumper
	return nil
}

// Execute excute dumping backup with logical backup tool
func (l *LogicalDumper) Execute(enableTimeOut bool) error {
	l.backupStartTime = time.Now()
	defer func() {
		l.backupEndTime = time.Now()
	}()
	binPath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
	args := []string{
		"-h", l.cnf.Public.MysqlHost,
		"-P", strconv.Itoa(l.cnf.Public.MysqlPort),
		"-u", l.cnf.Public.MysqlUser,
		"-p", l.cnf.Public.MysqlPasswd,
		"-o", filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName()),
		fmt.Sprintf("--long-query-retries=%d", l.cnf.LogicalBackup.FlushRetryCount),
		fmt.Sprintf("--set-names=%s", l.cnf.Public.MysqlCharset),
		fmt.Sprintf("--chunk-filesize=%d", l.cnf.LogicalBackup.ChunkFilesize),
		fmt.Sprintf("--threads=%d", l.cnf.LogicalBackup.Threads),
		"--trx-consistency-only",
		"--long-query-retry-interval=10",
		// "--disk-limits=1GB:5GB",
	}

	if !l.cnf.LogicalBackup.DisableCompress {
		args = append(args, "--compress")
	}
	if l.cnf.LogicalBackup.DefaultsFile != "" {
		args = append(args, []string{
			fmt.Sprintf("--defaults-file=%s", l.cnf.LogicalBackup.DefaultsFile),
		}...)
	}
	if tableFilter, err := l.cnf.LogicalBackup.BuildArgsTableFilterForMydumper(); err != nil {
		return err
	} else {
		args = append(args, tableFilter...)
	}

	if l.cnf.Public.DataSchemaGrant == "" {
		if l.cnf.LogicalBackup.NoData {
			args = append(args, "--no-data")
		}
		if l.cnf.LogicalBackup.NoSchemas {
			args = append(args, "--no-schemas")
		}
		if l.cnf.LogicalBackup.Events {
			args = append(args, "--events")
		}
		if l.cnf.LogicalBackup.Routines {
			args = append(args, "--routines")
		}
		if l.cnf.LogicalBackup.Triggers {
			args = append(args, "--triggers")
		}
		if l.cnf.LogicalBackup.InsertMode == "replace" {
			args = append(args, "--replace")
		} else if l.cnf.LogicalBackup.InsertMode == "insert_ignore" {
			args = append(args, "--insert-ignore")
		}
	} else {
		if l.cnf.Public.IfBackupSchema() && !l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--no-data", "--events", "--routines", "--triggers",
			}...)
		} else if !l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--no-schemas", "--no-views",
			}...)
		} else if l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--events", "--routines", "--triggers",
			}...)
		}
	}
	// ToDo extropt

	var cmd *exec.Cmd
	if enableTimeOut {
		timeDiffUnix, err := GetMaxRunningTime(l.cnf.Public.BackupTimeOut)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUnix))*time.Second)
		defer cancel()

		cmd = exec.CommandContext(ctx,
			"sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	} else {
		cmd = exec.Command("sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	}

	logger.Log.Info("logical dump command: ", cmd.String())

	outFile, err := os.Create(
		filepath.Join(logger.GetLogDir(),
			fmt.Sprintf("mydumper_%d_%d.log", l.cnf.Public.MysqlPort, int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	//cmd.Stderr = outFile
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run logical backup failed: ", err, stderr.String())
		return errors.WithMessage(err, stderr.String())
	}
	return nil
}

// PrepareBackupMetaInfo prepare the backup result of Logical Backup
// mydumper 备份完成后，解析 metadata 文件
func (l *LogicalDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	var metaInfo = dbareport.IndexContent{BinlogInfo: dbareport.BinlogStatusInfo{}}
	metaFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "metadata")
	metadata, err := parseMydumperMetadata(metaFileName)
	if err != nil {
		return nil, errors.WithMessage(err, "parse mydumper metadata")
	}
	logger.Log.Infof("metadata file:%+v", metadata)
	metaInfo.BackupBeginTime, err = time.ParseInLocation(cst.MydumperTimeLayout, metadata.DumpStarted, time.Local)
	if err != nil {
		return nil, errors.Wrapf(err, "parse BackupBeginTime %s", metadata.DumpStarted)
	}
	metaInfo.BackupEndTime, err = time.ParseInLocation(cst.MydumperTimeLayout, metadata.DumpFinished, time.Local)
	if err != nil {
		return nil, errors.Wrapf(err, "parse BackupEndTime %s", metadata.DumpFinished)
	}
	metaInfo.BackupConsistentTime = metaInfo.BackupBeginTime // 逻辑备份开始时间认为是一致性位点时间
	metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
		BinlogFile: metadata.MasterStatus["File"],
		BinlogPos:  metadata.MasterStatus["Position"],
		Gtid:       metadata.MasterStatus["Executed_Gtid_Set"],
		MasterHost: cnf.Public.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: cast.ToInt(cnf.Public.MysqlPort),
	}
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave {
		metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.SlaveStatus["Relay_Master_Log_File"],
			BinlogPos:  metadata.SlaveStatus["Exec_Master_Log_Pos"],
			Gtid:       metadata.SlaveStatus["Executed_Gtid_Set"],
			MasterHost: metadata.SlaveStatus["Master_Host"],
			MasterPort: cast.ToInt(metadata.SlaveStatus["Master_Port"]),
		}
	}
	metaInfo.JudgeIsFullBackup(&cnf.Public)
	return &metaInfo, nil
}
