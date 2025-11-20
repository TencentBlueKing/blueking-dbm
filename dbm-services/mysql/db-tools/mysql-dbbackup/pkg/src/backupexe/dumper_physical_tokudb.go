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
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalTokudbDumper physical tokudb dumper
type PhysicalTokudbDumper struct {
	cnf              *config.BackupConfig
	backupLogfile    string
	dbbackupHome     string
	flushWaitTimeout int
	mysqlVersion     string
	isOfficial       bool
	tokudbCmd        string
	storageEngine    string
	mysqlRole        string
	backupStartTime  time.Time
	backupEndTime    time.Time
	backupTargetPath string

	slaveStatus *mysqlcomm.SlaveStatus
}

// buildArgs construct the instruction parameters for data recovery.
func (p *PhysicalTokudbDumper) buildArgs() []string {
	// p.backupTargetPath is initialized in initConfig
	args := []string{
		fmt.Sprintf("-u%s", p.cnf.Public.MysqlUser),
		fmt.Sprintf("-p%s", p.cnf.Public.MysqlPasswd),
		fmt.Sprintf("-h%s", p.cnf.Public.MysqlHost),
		fmt.Sprintf("-P%d", p.cnf.Public.MysqlPort),
		fmt.Sprintf("--flush-wait-timeout=%d", p.flushWaitTimeout),
	}
	if strings.ToLower(p.cnf.Public.MysqlRole) == cst.RoleSlave {
		args = append(args, "--dump-slave")
	}
	args = append(args, fmt.Sprintf("%s", p.backupTargetPath))
	return args
}

// initConfig init config
func (p *PhysicalTokudbDumper) initConfig(mysqlVersion string, logBinDisabled bool) error {
	if p.cnf == nil {
		return errors.New("tokudb physical dumper config missed")
	}
	if p.flushWaitTimeout == 0 {
		p.flushWaitTimeout = 30
	}
	cmdPath, err := os.Executable()
	if err != nil {
		return err
	}

	p.dbbackupHome = filepath.Dir(cmdPath)

	// connect to the mysql and obtain the base information
	db, err := mysqlconn.InitConn(&p.cnf.Public)
	if err != nil {
		logger.Log.Errorf("can not connect to the mysql, host:%s, port:%d, errmsg:%s",
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	p.mysqlVersion, p.isOfficial = util.VersionParser(mysqlVersion)
	p.storageEngine, err = mysqlconn.GetStorageEngine(db)
	if err != nil {
		logger.Log.Errorf("can not get the storage engine from the mysql, host:%s, port:%d, errmsg:%s",
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
		return err
	}
	// keep the storage engine name is lower
	p.storageEngine = strings.ToLower(p.storageEngine)
	p.mysqlRole = strings.ToLower(p.cnf.Public.MysqlRole)

	// if the current node is slave, obtain the master ip and port
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		p.slaveStatus, err = mysqlconn.ShowMysqlSlaveStatus(db)
		if err != nil {
			logger.Log.Errorf("can not get the master host and port from the mysql, host:%s, port:%d, errmsg:%s",
				p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
			return err
		}
	}

	p.backupTargetPath = filepath.Join(p.cnf.Public.BackupDir, p.cnf.Public.TargetName())
	p.tokudbCmd = filepath.Join("bin", cst.ToolTokudbBackup)
	BackupTool = cst.ToolTokudbBackup
	return nil
}

// Execute Perform data recovery operations.
func (p *PhysicalTokudbDumper) Execute(ctx context.Context) error {
	// the storage engine must be tokudb
	if p.storageEngine != cst.StorageEngineTokudb {
		err := fmt.Errorf("unsupported engine:%s, host:%s, port:%d", p.storageEngine,
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort)
		logger.Log.Error(err)
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.tokudbCmd)
	args := p.buildArgs()
	if p.cnf.BackupToRemote.EnableRemote {
		return errors.Errorf("remote backup not support tokudb")
	}
	// perform the dump operation
	var cmd *exec.Cmd
	backupCmd := fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " "))
	cmd = exec.CommandContext(ctx, "sh", "-c", backupCmd)

	// create a dumper log file to store the log of the dumper command
	p.backupLogfile = fmt.Sprintf("dumper_%s_%d_%d.log",
		p.storageEngine, p.cnf.Public.MysqlPort, int(time.Now().Weekday()))
	p.backupLogfile = filepath.Join(p.dbbackupHome, "logs", p.backupLogfile)

	// pre-created dump log file
	outFile, err := os.Create(p.backupLogfile)

	if err != nil {
		logger.Log.Errorf("can not create the dumper log file, file name:%s, errmsg:%s", p.backupLogfile, err)
		return err
	}

	defer func() {
		_ = outFile.Close()
	}()

	// redirect standard output and error messages to a file
	cmd.Stdout = outFile
	cmd.Stderr = outFile

	// perform the dump command
	p.backupStartTime = cmutil.TimeToSecondPrecision(time.Now())
	defer func() {
		p.backupEndTime = cmutil.TimeToSecondPrecision(time.Now())
	}()
	err = cmd.Run()
	if err != nil {
		logger.Log.Errorf("can not run the tokudb physical dumper command:%s, engine:%s, errmsg:%s",
			mysqlcomm.RemoveMysqlCommandPassword(backupCmd), p.storageEngine, err)
		// 异常退出需要恢复原始的 slave status 信息
		if p.slaveStatus != nil && p.slaveStatus.SlaveSqlRunning == "Yes" {
			db2, err2 := mysqlconn.InitConn(&p.cnf.Public)
			if err2 != nil {
				logger.Log.Errorf("failed to connect mysql, host:%s, port:%d, errmsg:%s",
					p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err2)
				return err2
			}
			defer func() {
				_ = db2.Close()
			}()
			err2 = mysqlconn.StartSlaveThreads(true, true, db2)
			logger.Log.Warnf("after backup failed: start slave with %v", err2)
		}
		return err
	}

	logger.Log.Infof("dump tokudb success, command:%s", cmd.String())
	return nil
}

// PrepareBackupMetaInfo generate the metadata of database backup
func (p *PhysicalTokudbDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error {
	// parse the binlog position
	binlogInfoFileName := filepath.Join(p.backupTargetPath, "xtrabackup_binlog_info")
	slaveInfoFileName := filepath.Join(p.backupTargetPath, "xtrabackup_slave_info")
	tmpFileName := filepath.Join(p.backupTargetPath, "tmp_dbbackup_go.txt")

	// obtain the qpress command path
	exepath, err := os.Executable()
	if err != nil {
		return err
	}
	exepath = filepath.Dir(exepath)

	// parse the binlog
	masterStatus, err := parseXtraBinlogInfo("", binlogInfoFileName, tmpFileName)
	if err != nil {
		logger.Log.Errorf("do not parse xtrabackup binlog file, file name:%s, errmsg:%s",
			slaveInfoFileName, err)
		return err
	}

	// save the master node status
	metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
	metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
	metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort

	// parse the information of the master node
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		slaveStatus, err := parseXtraSlaveInfo("", slaveInfoFileName, tmpFileName)

		if err != nil {
			logger.Log.Errorf("do not parse xtrabackup slave information, xtrabackup file:%s, errmsg:%s",
				slaveInfoFileName, err)
			return err
		}
		if metaInfo.BinlogInfo.ShowSlaveStatus == nil {
			metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{}
		}
		metaInfo.BinlogInfo.ShowSlaveStatus.BinlogFile = slaveStatus.BinlogFile
		metaInfo.BinlogInfo.ShowSlaveStatus.BinlogPos = slaveStatus.BinlogPos
		if p.slaveStatus != nil {
			if p.slaveStatus.MasterHost != "" {
				metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = p.slaveStatus.MasterHost
			}
			if p.slaveStatus.MasterPort != 0 {
				metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = p.slaveStatus.MasterPort
			}
		}
	}

	// parse xtrabackup_info
	if fileTokudbBegin, err := os.ReadFile(filepath.Join(p.backupTargetPath, "TOKUDB.BEGIN")); err == nil {
		metaInfo.BackupBeginTime, _ = time.ParseInLocation("20060102_150405",
			strings.TrimSpace(string(fileTokudbBegin)), time.Local)
	} else {
		metaInfo.BackupBeginTime = p.backupStartTime
	}
	if fileTokudbEnd, err := os.ReadFile(filepath.Join(p.backupTargetPath, "TOKUDB.END")); err == nil {
		metaInfo.BackupEndTime, _ = time.ParseInLocation("20060102_150405",
			strings.TrimSpace(string(fileTokudbEnd)), time.Local)
	} else {
		metaInfo.BackupEndTime = p.backupEndTime
	}
	metaInfo.BackupConsistentTime = metaInfo.BackupEndTime

	// teh mark indicating whether the update is a full backup or not
	metaInfo.JudgeBackupMethod(cnf)
	if err = os.Remove(tmpFileName); err != nil {
		logger.Log.Errorf("do not delete the tmp file, file name:%s, errmsg:%s", tmpFileName, err)
		return err
	}

	return nil
}
