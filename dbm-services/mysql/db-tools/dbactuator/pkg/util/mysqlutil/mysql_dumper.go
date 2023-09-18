package mysqlutil

import (
	"fmt"
	"path"
	"regexp"
	"runtime"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/panjf2000/ants/v2"
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
	NoData       bool
	AddDropTable bool // 默认 false 代表添加 --skip-add-drop-table 选项
	NeedUseDb    bool
	NoCreateDb   bool
	NoCreateTb   bool
	DumpRoutine  bool // 默认 false 代表添加不导出存储过程,True导出存储过程
	DumpTrigger  bool // 默认 false 代表添加不导出触发器
	DumpEvent    bool // 默认 false 导出 event

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
	logger.Info("mysqldump cmd:%s", RemovePassword(dumpCmd))
	output, err := osutil.ExecShellCommand(false, dumpCmd)
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
	var wg sync.WaitGroup
	var errs []string
	m.init()
	errChan := make(chan error, 1)
	logger.Info("mysqldump data:%+v", *m)
	pool, _ := ants.NewPool(m.maxConcurrency)
	defer pool.Release()
	f := func(db string) func() {
		return func() {
			outputFile := path.Join(m.DumpDir, fmt.Sprintf("%s.sql", db))
			errFile := path.Join(m.DumpDir, fmt.Sprintf("%s.err", db))
			dumpCmd := m.getDumpCmd(db, outputFile, errFile, "")
			logger.Info("mysqldump cmd:%s", RemovePassword(dumpCmd))
			output, err := osutil.ExecShellCommand(false, dumpCmd)
			if err != nil {
				errChan <- fmt.Errorf("execte %s get an error:%s,%w", dumpCmd, output, err)
				wg.Done()
				return
			}
			if err := checkDumpComplete(outputFile); err != nil {
				errChan <- err
				wg.Done()
				return
			}
			wg.Done()
		}
	}

	for _, db := range m.DbNames {
		wg.Add(1)
		pool.Submit(f(db))
	}
	go func() {
		for err := range errChan {
			logger.Error("dump db failed: %s", err.Error())
			errs = append(errs, err.Error())
		}
	}()
	wg.Wait()
	close(errChan)
	if len(errs) > 0 {
		return fmt.Errorf("Errrors: %s", strings.Join(errs, "\n"))
	}
	return err
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
