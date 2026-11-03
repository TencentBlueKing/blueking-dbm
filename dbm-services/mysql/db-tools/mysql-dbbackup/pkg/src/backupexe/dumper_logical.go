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
	"os/signal"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/mattn/go-shellwords"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// LogicalDumper TODO
type LogicalDumper struct {
	cnf             *config.BackupConfig
	dbbackupHome    string
	backupStartTime time.Time
	backupEndTime   time.Time
}

func (l *LogicalDumper) initConfig(mysqlVerStr string, logBinDisabled bool) error {
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

// buildArgs 生成 mydumper 的命令行参数
func (l *LogicalDumper) buildArgs() ([]string, error) {
	binPath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
	args := []string{
		"-h", l.cnf.Public.MysqlHost,
		"-P", strconv.Itoa(l.cnf.Public.MysqlPort),
		"-u", l.cnf.Public.MysqlUser,
		fmt.Sprintf("--password='%s'", l.cnf.Public.MysqlPasswd),
		"-o", filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName()),
		"--long-query-retry-interval=10",
		fmt.Sprintf("--long-query-retries=%d", l.cnf.LogicalBackup.FlushRetryCount),
		fmt.Sprintf("--chunk-filesize=%d", l.cnf.LogicalBackup.ChunkFilesize),
		fmt.Sprintf("--threads=%d", l.cnf.LogicalBackup.Threads),
		// "--disk-limits=1GB:5GB",
	}
	if ok, _ := MydumperHasOption(binPath, "--default-character-set", "latin1"); ok {
		args = append(args,
			fmt.Sprintf("--set-names=utf8,%s", l.cnf.Public.MysqlCharset),
			fmt.Sprintf("--default-character-set=utf8,%s", l.cnf.Public.MysqlCharset))
	} else {
		// --schema-set-names=utf8 内部定制参数
		args = append(args,
			"--set-names", l.cnf.Public.MysqlCharset)
	}
	if ok, _ := MydumperHasOption(binPath, "--source-data"); ok {
		args = append(args, "--source-data", "--replica-data")
	}
	if !l.cnf.Public.IfBackupData() { // 如果不备份数据，不加 lock 了
		if ok, _ := MydumperHasOption(binPath, "--sync-thread-lock-mode", "NO_LOCK"); ok {
			args = append(args, "--trx-tables=0 --sync-thread-lock-mode=NO_LOCK") //NO_LOCK
		} else {
			// mydumper 废弃的参数没有移除，只是报个 deprecated ERROR (不理解!!)
			// CRITICAL **: --no-locks is deprecated use --sync-thread-lock-mode instead
			args = append(args, "--no-locks") //--trx-tables=0
		}
	} else if *l.cnf.LogicalBackup.TrxConsistencyOnly { // nil is true
		if ok, _ := MydumperHasOption(binPath, "--trx-tables"); ok {
			// --trx-tables 与 --trx-consistency-only 不是等价替换的
			args = append(args, "--trx-tables=0 --sync-thread-lock-mode=FTWRL")
		} else {
			args = append(args, "--trx-consistency-only")
		}
	} else {
		if ok, _ := MydumperHasOption(binPath, "--sync-thread-lock-mode", "NO_LOCK"); ok {
			args = append(args, "--trx-tables=0 --sync-thread-lock-mode=NO_LOCK") //--trx-tables=0
		}
	}

	if l.cnf.Public.KillLongQueryTime > 0 {
		args = append(args, "--kill-long-queries",
			fmt.Sprintf("--long-query-guard=%d", l.cnf.Public.KillLongQueryTime))
	} else {
		if l.cnf.Public.FtwrlWaitTimeout > 0 {
			args = append(args, fmt.Sprintf("--long-query-guard=%d", l.cnf.Public.FtwrlWaitTimeout))
		} else {
			args = append(args, "--long-query-guard=999999") // 不退出
		}
	}
	if l.cnf.Public.AcquireLockWaitTimeout > 0 {
		if ok, _ := MydumperHasOption(binPath, "--lock-wait-timeout", "1"); ok {
			args = append(args, fmt.Sprintf("--lock-wait-timeout=%d", l.cnf.Public.AcquireLockWaitTimeout))
		} else {
			logger.Log.Warn("mydumper has no option. ignore", "--lock-wait-timeout")
		}
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
		return nil, err
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
	if l.cnf.LogicalBackup.ExtraOpt != "" {
		extraArgs, err := shellwords.Parse(l.cnf.LogicalBackup.ExtraOpt)
		if err != nil {
			return nil, errors.Wrapf(err, "parse LogicalBackup.ExtraOpt: %s", l.cnf.LogicalBackup.ExtraOpt)
		}
		args = append(args, extraArgs...)
	}
	return args, nil
}

// Execute excute dumping backup with logical backup tool
func (l *LogicalDumper) Execute(ctx context.Context) error {
	l.backupStartTime = time.Now()
	defer func() {
		l.backupEndTime = time.Now()
	}()
	binPath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
	args, err := l.buildArgs()
	if err != nil {
		return err
	}

	var cmd *exec.Cmd
	cmd = exec.CommandContext(ctx, "sh", "-c", fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	logger.Log.Info("logical dump command: ", cmd.String())

	mydumperLogFile := filepath.Join(logger.GetLogDir(),
		fmt.Sprintf("mydumper_%d_%d.log", l.cnf.Public.MysqlPort, int(time.Now().Weekday())))
	outFile, err := os.OpenFile(mydumperLogFile, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile

	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true,
	}

	if err = cmd.Start(); err != nil {
		return err
	}

	sig := make(chan os.Signal)
	signal.Notify(sig, syscall.SIGHUP, syscall.SIGINT, syscall.SIGTERM, syscall.SIGQUIT) // syscall.SIGKILL
	go func() {
		select {
		case s := <-sig:
			logger.Log.Warnf("dbbackup got signal: %v", s)
			if cmd.Process != nil {
				err := cmd.Process.Kill() // syscall.Kill(-cmd.Process.Pid,syscall.SIGKILL)
				logger.Log.Warnf("kill mydumper %d exit with %v", cmd.Process.Pid, err)
			}
		}
	}()

	err = cmd.Wait()
	if err != nil {
		// mydumper 的错误信息要从头往后看，看最近的日志因为多线程的原因，不准确
		errStrPrefix := fmt.Sprintf("head 5 error from %s", mydumperLogFile)
		errStrDetail, _ := cmutil.NewGrepLines(mydumperLogFile, true, true).
			MatchWords([]string{"ERROR", "CRITICAL", "fatal", "No such file"}, 5)
		if len(errStrDetail) > 0 {
			logger.Log.Info(errStrPrefix)
			logger.Log.Error(errStrDetail)
		} else {
			logger.Log.Warn("can not find more detail error message from ", mydumperLogFile)
		}
		logger.Log.Error("run logical backup failed ", err, l.cnf.Public.MysqlPort)
		return errors.WithMessagef(err, fmt.Sprintf("%s\n%s", errStrPrefix, errStrDetail))
	}
	// check the integrity of backup
	integrityErr := util.CheckIntegrity(&l.cnf.Public)
	if integrityErr != nil {
		logger.Log.Error("Failed to check the integrity of backup, error: ", integrityErr)
		return integrityErr
	}
	if err = l.RewriteInfodbaSchema(); err != nil {
		logger.Log.Warn("rewrite infodba_schema backup files failed, ignore: ", err)
	}
	return nil
}

// infodbaRewriteMaxFileSize infodba_schema 单个 .zst 备份文件超过该大小，不做改写
const infodbaRewriteMaxFileSize = 2 * 1024 * 1024

var (
	// infodba_schema.<table>-schema.sql.zst
	reInfodbaTableSchemaFile = regexp.MustCompile(
		`^` + regexp.QuoteMeta(cst.INFODBA_SCHEMA) + `\.[^.]+-schema\.sql` + regexp.QuoteMeta(cst.ZstdSuffix) + `$`)
	// infodba_schema.<table>.00000.sql.zst
	reInfodbaTableDataFile = regexp.MustCompile(
		`^` + regexp.QuoteMeta(cst.INFODBA_SCHEMA) + `\.[^.]+\.\d+\.sql` + regexp.QuoteMeta(cst.ZstdSuffix) + `$`)

	reCreateTable = regexp.MustCompile(`(?m)^CREATE TABLE (?:IF NOT EXISTS )?`)
	reInsertInto  = regexp.MustCompile(`(?m)^INSERT INTO `)
)

// RewriteInfodbaSchema 改写备份中 infodba_schema 的表结构和数据文件
// 建库语句 mydumper 已经是 CREATE DATABASE /*!32312 IF NOT EXISTS*/，无需改写
// 表结构: CREATE TABLE -> CREATE TABLE IF NOT EXISTS
// 数据: INSERT INTO -> REPLACE INTO
// 只处理 .zst 文件，单个文件超过 infodbaRewriteMaxFileSize 忽略
func (l *LogicalDumper) RewriteInfodbaSchema() error {
	if CmdZstd == "" {
		return errors.New("zstd command is empty")
	}
	backupDir := filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName())
	files, err := filepath.Glob(filepath.Join(backupDir, cst.INFODBA_SCHEMA+".*"+cst.ZstdSuffix))
	if err != nil {
		return errors.WithMessage(err, "glob infodba_schema files")
	}
	var errList []string
	for _, f := range files {
		baseName := filepath.Base(f)
		var re *regexp.Regexp
		var repl []byte
		if reInfodbaTableSchemaFile.MatchString(baseName) {
			re, repl = reCreateTable, []byte("CREATE TABLE IF NOT EXISTS ")
		} else if reInfodbaTableDataFile.MatchString(baseName) {
			re, repl = reInsertInto, []byte("REPLACE INTO ")
		} else {
			continue
		}
		fi, err := os.Stat(f)
		if err != nil {
			errList = append(errList, err.Error())
			continue
		}
		if !fi.Mode().IsRegular() {
			continue
		}
		if fi.Size() > infodbaRewriteMaxFileSize {
			logger.Log.Warnf("skip rewrite %s, file size %d > %d", f, fi.Size(), infodbaRewriteMaxFileSize)
			continue
		}
		changed, err := rewriteZstdSqlFile(f, re, repl)
		if err != nil {
			logger.Log.Warnf("rewrite %s failed: %s", f, err.Error())
			errList = append(errList, err.Error())
			continue
		}
		if changed {
			logger.Log.Infof("rewrite %s success", f)
		}
	}
	if len(errList) > 0 {
		return errors.New(strings.Join(errList, "; "))
	}
	return nil
}

// rewriteZstdSqlFile 解压 zstFile，按 re 替换为 repl，重新压缩后原子替换原文件
// 内容无变化时不改写，返回 false
func rewriteZstdSqlFile(zstFile string, re *regexp.Regexp, repl []byte) (bool, error) {
	content, errBytes, err := cmutil.ExecCommandReturnBytes(false, "", CmdZstd, "-d", "-c", zstFile)
	if err != nil {
		return false, errors.WithMessagef(err, "decompress %s: %s", zstFile, string(errBytes))
	}
	newContent := re.ReplaceAllLiteral(content, repl)
	if bytes.Equal(content, newContent) {
		return false, nil
	}

	// gozstd 解压要求文件以 .zst 结尾；临时文件名不匹配 infodba_schema.* 表文件规则
	tmpFile := strings.TrimSuffix(zstFile, cst.ZstdSuffix) + ".rewrite_tmp" + cst.ZstdSuffix
	defer func() {
		_ = os.Remove(tmpFile)
	}()
	var stderr bytes.Buffer
	cmd := exec.Command(CmdZstd, "-q", "-f", "-o", tmpFile)
	cmd.Stdin = bytes.NewReader(newContent)
	cmd.Stderr = &stderr
	if err = cmd.Run(); err != nil {
		return false, errors.WithMessagef(err, "compress %s: %s", tmpFile, stderr.String())
	}
	// 校验重新压缩的文件
	verifyContent, errBytes, err := cmutil.ExecCommandReturnBytes(false, "", CmdZstd, "-d", "-c", tmpFile)
	if err != nil {
		return false, errors.WithMessagef(err, "verify %s: %s", tmpFile, string(errBytes))
	}
	if !bytes.Equal(verifyContent, newContent) {
		return false, errors.Errorf("verify %s: content mismatch", tmpFile)
	}
	if err = os.Rename(tmpFile, zstFile); err != nil {
		return false, errors.WithMessagef(err, "rename %s to %s", tmpFile, zstFile)
	}
	return true, nil
}

// PrepareBackupMetaInfo prepare the backup result of Logical Backup
// mydumper 备份完成后，解析 metadata 文件
func (l *LogicalDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error {
	metaFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "metadata")
	metadata, err := parseMydumperMetadataV2(metaFileName)
	if err != nil {
		return errors.WithMessage(err, "parse mydumper metadata")
	}
	logger.Log.Infof("metadata file:%+v", metadata)
	metaInfo.BackupBeginTime, err = time.ParseInLocation(cst.MydumperTimeLayout, metadata.DumpStarted, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupBeginTime %s", metadata.DumpStarted)
	}
	metaInfo.BackupEndTime, err = time.ParseInLocation(cst.MydumperTimeLayout, metadata.DumpFinished, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupEndTime %s", metadata.DumpFinished)
	}
	metaInfo.BackupConsistentTime = metaInfo.BackupBeginTime // 逻辑备份开始时间认为是一致性位点时间
	metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
		BinlogFile: metadata.MasterStatus["source_log_file"],
		BinlogPos:  metadata.MasterStatus["source_log_pos"],
		Gtid:       metadata.MasterStatus["executed_gtid_set"],
		MasterHost: cnf.Public.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: cast.ToInt(cnf.Public.MysqlPort),
	}
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave && metadata.SlaveStatus["relay_master_log_file"] != "" {
		metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.SlaveStatus["relay_master_log_file"],
			BinlogPos:  metadata.SlaveStatus["exec_master_log_pos"],
			Gtid:       metadata.SlaveStatus["executed_gtid_set"],
			MasterHost: metadata.SlaveStatus["master_host"],
			MasterPort: cast.ToInt(metadata.SlaveStatus["master_port"]),
		}
	}
	metaInfo.JudgeBackupMethod(cnf)
	metaInfo.JudgeLogicalFilter(cnf)
	return nil
}

// MydumperHasOption check mydumper has --xxx or not
// example: ./mydumper --help --lock-wait-timeout 1
func MydumperHasOption(bin string, option ...string) (bool, error) {
	// --help 在前/后 无所谓
	cmdArgs := []string{bin, "--help"}
	cmdArgs = append(cmdArgs, option...)
	_, cmdStderr, err := cmutil.ExecCommand(false, "", cmdArgs[0], cmdArgs[1:]...)
	if err == nil {
		return true, nil
	}
	if strings.Contains(cmdStderr, "Unknown option") {
		return false, nil
	}
	return false, err
}
