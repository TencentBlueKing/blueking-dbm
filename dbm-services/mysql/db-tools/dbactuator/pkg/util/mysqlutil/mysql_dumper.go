/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil

import (
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

var dumpCompleteReg = regexp.MustCompile("Dump completed on")

// Dumper TODO
type Dumper interface {
	Dump() error
}

// MySQLDumpOption TODO
type MySQLDumpOption struct {
	/* 	DumpSchema   bool
	   	DumpData     bool */
	NoData        bool
	AddDropTable  bool // 默认 false 代表添加 --skip-add-drop-table 选项
	NeedUseDb     bool
	NoCreateDb    bool
	NoCreateTb    bool
	DumpRoutine   bool // 默认 false 代表添加不导出存储过程,True导出存储过程
	DumpTrigger   bool // 默认 false 代表添加不导出触发器
	DumpEvent     bool // 默认 false 导出 event
	GtidPurgedOff bool // --set-gtid-purged=OFF
}

type runtimectx struct {
	maxConcurrency        int
	maxResourceUsePercent int
}

// MySQLDumper TODO
type MySQLDumper struct {
	MySQLDumpOption
	DumpDir      string // 备份到哪个目录
	DbBackupUser string
	DbBackupPwd  string
	Ip           string
	Port         int
	Charset      string
	DumpCmdFile  string // mysqldump 的绝对路径
	DbNames      []string
	IsMaster     bool
	// Todo
	// SelfDefineArgs []string  ...
	// Precheck ...
	runtimectx
}

// MySQLDumperTogether TODO
type MySQLDumperTogether struct {
	MySQLDumper
	OutputfileName string
	UseTMySQLDump  bool // 是否使用的是自研的mysqldump,一般介质在备份目录下
	TDBCTLDump     bool // 中控专有参数
}

// checkDumpComplete  检查导出结果是否Ok
//
//	@receiver file  导出SQL文件的绝对路径
//	@return err
func checkDumpComplete(file string) (err error) {
	// 倒着读取10行
	res, err := util.ReverseRead(file, 10)
	if err != nil {
		return err
	}
	for _, l := range res {
		// 如果匹配到了，表示备份的文件oK
		if dumpCompleteReg.MatchString(l) {
			return nil
		}
	}
	return fmt.Errorf("备份文件没有匹配到Dump completed on")
}

// init 初始化运行时参数
//
//	@receiver m
func (m *MySQLDumper) init() {
	m.maxConcurrency = runtime.NumCPU() / 2
	m.maxResourceUsePercent = 50
	if m.IsMaster || m.maxConcurrency == 0 {
		// 如果是在Master Dump的话不允许开启并发
		m.maxConcurrency = 1
	}
}

// Dump Together 后面指定的 db 名字空格分隔，例如 --databases db1 db2 > just_one_file.sql
//
//	@receiver m
//	@return err
func (m *MySQLDumperTogether) Dump() (err error) {
	m.init()
	outputFile := path.Join(m.DumpDir, m.OutputfileName)
	errFile := path.Join(m.DumpDir, m.OutputfileName+".err")
	dumpOption := ""
	if m.UseTMySQLDump {
		dumpOption = m.getTMySQLDumpOption()
	}
	dumpCmd := m.getDumpCmd(strings.Join(m.DbNames, " "), outputFile, errFile, dumpOption)
	logger.Info("mysqldump cmd:%s", ClearSensitiveInformation(dumpCmd))
	output, err := osutil.StandardShellCommand(false, dumpCmd)
	if err != nil {
		return fmt.Errorf("execte %s get an error:%s,%w", dumpCmd, output, err)
	}
	if err := checkDumpComplete(outputFile); err != nil {
		logger.Error("checkDumpComplete failed %s", err.Error())
		return err
	}
	return
}

// Dump OneByOne 按照每个db 分别导出不同的文件，可控制并发
//
//	@receiver m
//	@return err
func (m *MySQLDumper) Dump() (err error) {
	m.init()
	var wg sync.WaitGroup
	var errs []error
	errChan := make(chan error, 1)
	concurrencyControl := make(chan struct{}, m.maxConcurrency)
	logger.Info("mysqldump data:%+v", *m)
	go func() {
		for err := range errChan {
			logger.Error("dump db failed: %s", err.Error())
			errs = append(errs, err)
		}
	}()
	for _, db := range m.DbNames {
		wg.Add(1)
		concurrencyControl <- struct{}{}
		go func(db string) {
			defer func() {
				wg.Done()
				<-concurrencyControl
			}()
			outputFile := path.Join(m.DumpDir, fmt.Sprintf("%s.sql", db))
			errFile := path.Join(m.DumpDir, fmt.Sprintf("%s.err", db))
			dumpCmd := m.getDumpCmd(db, outputFile, errFile, "")
			logger.Info("mysqldump cmd:%s", RemovePassword(dumpCmd))
			output, err := osutil.StandardShellCommand(false, dumpCmd)
			if err != nil {
				errContent, _ := os.ReadFile(errFile)
				errChan <- fmt.Errorf("execte %s get an error:%s,%w\n errfile content:%s", dumpCmd, output, err,
					string(errContent))
				return
			}
			if err := checkDumpComplete(outputFile); err != nil {
				errContent, _ := os.ReadFile(errFile)
				errChan <- fmt.Errorf("%w\n errfile content:%s", err, string(errContent))
				return
			}
		}(db)
	}
	wg.Wait()
	close(errChan)
	return errors.Join(errs...)
}

/*
mysqldump 参数说明：
-B --databases ：后面指定的 db 名字空格分隔，例如 --databases db1 db2 >> aaa.sql

-d, --no-data：不导出 row information，也就是不导出行数据。 只导出 schema 的时候比较常用，例如： --databases testdb -d > testdb_d.sql 。
需要注意的是带上 -B，sql 文件里面就会多上 create database 相关语句：
CREATE DATABASE testdb ...
USE `testdb`;
--skip-add-drop-table：导出的时候不带上  DROP TABLE IF EXISTS table_name;
 提示：默认是--add-drop-table (Add a DROP TABLE before each create)
这个一般建议带上这个选项， 不然很容易由于dump 没有用好，导致drop了正确的 table 。
*/

// getDumpCmd TODO
/*
mysqldump --skip-add-drop-table -d testdb > testdb.sql

DumpSchema 功能概述：
1. 一个 DB 一个 schema 文件
2. 文件名 DumpDir/$dump_file.$old_db_name.$SUBJOB_ID
3. $mysqldump_file
-h$SOURCE_IP
-P $SOURCE_PORT
-u$dbbackup_user
-p$dbbackup_pass $dump_schema_opt
--skip-foreign-key-check
--skip-opt
--create-option
--single-transaction
-q
--no-autocommit
--default-character-set=$charset_server
-R $create_db_opt $old_db_name
>/data/dbbak/$dump_file.$old_db_name 2>/data/dbbak/$dump_file.$old_db_name.$SUBJOB_ID.err;
*/
func (m *MySQLDumper) getDumpCmd(dbName, outputFile, errFile, dumpOption string) (dumpCmd string) {
	if m.NoData {
		dumpOption += " -d "
	}
	if m.AddDropTable {
		dumpOption += " --add-drop-table "
	} else {
		dumpOption += "--skip-add-drop-table"
	}
	if m.NeedUseDb {
		dumpOption += " -B "
	}
	if m.NoCreateDb {
		dumpOption += " -n "
	}
	if m.NoCreateTb {
		dumpOption += " -t "
	}
	if m.DumpRoutine {
		dumpOption += " -R "
	}
	if m.DumpTrigger {
		dumpOption += " --triggers "
	} else {
		dumpOption += " --skip-triggers "
	}
	if m.DumpEvent {
		dumpOption += " --events"
	}
	if m.GtidPurgedOff {
		dumpOption += " --set-gtid-purged=OFF"
	}
	dumpCmd = fmt.Sprintf(
		`%s 
		-h%s 
		-P%d 
		-u%s 
		-p%s 
		--skip-opt 
		--create-options  
		--single-transaction  
		--max-allowed-packet=1G  
		-q 
		--no-autocommit 
		--default-character-set=%s %s %s > %s 2>%s`,
		m.DumpCmdFile,
		m.Ip,
		m.Port,
		m.DbBackupUser,
		m.DbBackupPwd,
		m.Charset,
		dumpOption,
		dbName,
		outputFile,
		errFile,
	)
	return strings.ReplaceAll(dumpCmd, "\n", " ")
}

// getTMySQLDumpOption  自研mysqldump
//
//	@receiver m
//	@return dumpCmd
func (m *MySQLDumper) getTMySQLDumpOption() (dumpOption string) {
	return fmt.Sprintf(
		`
	--ignore-show-create-table-error
	--skip-foreign-key-check
	--max-concurrency=%d 
	--max-resource-use-percent=%d
	`, m.maxConcurrency, m.maxResourceUsePercent,
	)
}

func (m *MySQLDumper) getTDBCTLDumpOption() (dumpOption string) {
	// 默认false 即不带有SET tc_admin=0
	// 如果不需要下发spider，可添加此参数
	return " --print-tc-admin-info "
}

// MyDumper Options mydumper options
type MyDumper struct {
	Options MyDumperOptions
	Host    string
	Port    int
	User    string
	Pwd     string
	Charset string
	DumpDir string // 备份到哪个目录
	BinPath string // mydumper 的绝对路径
}

// MyDumperOptions TODO
type MyDumperOptions struct {
	NoData    bool
	Threads   int
	UseStream bool
	Regex     string
}

// buildCommand TODO
func (m *MyDumper) buildCommand() (command string) {
	command = fmt.Sprintf(`%s -h %s -P %d -u %s -p '%s' --set-names=%s`, m.BinPath, m.Host,
		m.Port, m.User, m.Pwd, m.Charset)
	if m.Options.UseStream {
		command += " --stream "
	} else {
		command += fmt.Sprintf(" -o %s ", m.DumpDir)
	}
	command += " --events --routines --triggers --verbose=2 "
	command += " --trx-consistency-only --long-query-retry-interval=10 "
	if m.Options.NoData {
		command += " --no-data "
	}
	if m.Options.Threads > 0 {
		command += fmt.Sprintf(" --threads=%d ", m.Options.Threads)
	}
	if cmutil.IsNotEmpty(m.Options.Regex) {
		command += fmt.Sprintf(` -x '%s'`, m.Options.Regex)
	}
	//logger.Info("mydumper command: %s", command)
	return
}

// MyLoader Options myloader options
type MyLoader struct {
	Options     MyLoaderOptions
	Host        string
	Port        int
	User        string
	Pwd         string
	Charset     string
	BinPath     string
	LoadDataDir string
}

// MyLoaderOptions TODO
type MyLoaderOptions struct {
	NoData         bool
	UseStream      bool
	Threads        int
	DefaultsFile   string
	OverWriteTable bool // Drop tables if they already exist
}

func (m *MyLoader) buildCommand() (command string) {
	command = fmt.Sprintf(`%s -h %s -P %d -u %s -p '%s' --set-names=%s `, m.BinPath, m.Host,
		m.Port, m.User, m.Pwd, m.Charset)
	command += " --enable-binlog --verbose=2 "
	if m.Options.UseStream {
		command += " --stream "
	} else {
		command += fmt.Sprintf(" -d %s ", m.LoadDataDir)
	}
	if m.Options.Threads > 0 {
		command += fmt.Sprintf(" --threads=%d ", m.Options.Threads)
	}
	if cmutil.IsNotEmpty(m.Options.DefaultsFile) {
		command += fmt.Sprintf(" --defaults-file=%s ", m.Options.DefaultsFile)
	}
	if m.Options.NoData {
		command += " --no-data "
	}
	if m.Options.OverWriteTable {
		command += " -o "
	}
	return
}

// Loader do myloader load data
func (m *MyLoader) Loader() (err error) {
	m.BinPath = filepath.Join(cst.DbbackupGoInstallPath, "bin/myloader")
	if err = setEnv(); err != nil {
		logger.Error("set env failed %s", err.Error())
		return
	}
	var stderr string
	stderr, err = osutil.StandardShellCommand(false, m.buildCommand())
	if err != nil {
		logger.Error("stderr %s", stderr)
		return fmt.Errorf("stderr:%s,err:%w", stderr, err)
	}
	return nil
}

// Dumper do mydumper dump data
func (m *MyDumper) Dumper() (err error) {
	m.BinPath = filepath.Join(cst.DbbackupGoInstallPath, "bin/mydumper")
	if err = setEnv(); err != nil {
		logger.Error("set env failed %s", err.Error())
		return
	}
	var stderr string
	stderr, err = osutil.StandardShellCommand(false, m.buildCommand())
	if err != nil {
		logger.Error("stderr %s", stderr)
		return fmt.Errorf("stderr:%s,err:%w", stderr, err)
	}
	return nil
}

// MyStreamDumpLoad  stream dumper loader
type MyStreamDumpLoad struct {
	Dumper *MyDumper
	Loader *MyLoader
}

func (s *MyStreamDumpLoad) buildCommand() (command string) {
	s.Dumper.Options.UseStream = true
	dumpCmd := s.Dumper.buildCommand()
	loadCmd := s.Loader.buildCommand()
	return fmt.Sprintf("%s|%s", dumpCmd, loadCmd)
}

// setEnv mydumper or myloader lib path
func setEnv() (err error) {
	var libPath []string
	libPath = append(libPath, filepath.Join(cst.DbbackupGoInstallPath, "lib/libmydumper"))
	oldLibs := strings.Split(os.Getenv("LD_LIBRARY_PATH"), ":")
	oldLibs = append(oldLibs, libPath...)
	return os.Setenv("LD_LIBRARY_PATH", strings.Join(oldLibs, ":"))
}

// Run Command Run
func (s *MyStreamDumpLoad) Run() (err error) {
	if err = setEnv(); err != nil {
		logger.Error("set env failed %s", err.Error())
		return
	}
	s.Dumper.BinPath = filepath.Join(cst.DbbackupGoInstallPath, "bin/mydumper")
	s.Loader.BinPath = filepath.Join(cst.DbbackupGoInstallPath, "bin/myloader")
	var stderr string
	command := s.buildCommand()
	logger.Info("the stream dump load command is %s", command)
	stderr, err = osutil.StandardShellCommand(false, command)
	if err != nil {
		logger.Error("stderr %s", stderr)
		return fmt.Errorf("stderr:%s,err:%w", stderr, err)
	}
	return nil
}
