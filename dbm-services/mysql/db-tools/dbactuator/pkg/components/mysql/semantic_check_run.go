package mysql

import (
	"fmt"
	"os"
	"os/exec"
	"path"
	"regexp"
	"sync"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	ants "github.com/panjf2000/ants/v2"
)

/*
	Prepare:
	1、下发备份表结构命名到目标实例，完成备份表结构
	2、将备份的表结构文件&待语义检查的SQL文件下发到语义检查的机器上
	3、选择一个于目标实例版本一致的语义检查的实例，锁定
	-------------------------------------------------------------
	Doing:
	4、将处理后的表结构导入到临时实例上
	5、导入待检查的SQL文件
	6、分析语义检查的结果
	-------------------------------------------------------------
	Ending:
	7、Clean 语义检查临时实例,并释放
*/

// SemanticCheckComp TODO
type SemanticCheckComp struct {
	GeneralParam             *components.GeneralParam `json:"general"`
	Params                   SenmanticCheckParam      `json:"extend"`
	SenmanticCheckRunTimeCtx `json:"-"`
}

// SenmanticCheckParam TODO
type SenmanticCheckParam struct {
	Host          string             `json:"host"  validate:"required,ip"`                // 语义检查实例的主机地址
	Port          int                `json:"port"  validate:"required,lt=65536,gte=3306"` // 语义检查实例的端口
	SchemaFile    string             `json:"schemafile" validate:"required"`              // 表结构文件
	ExcuteObjects []ExcuteSQLFileObj `json:"execute_objects"`
	// 用于获取目标实例的字符集，默认存储引擎
	RemoteHost string `json:"remote_host"  validate:"required,ip"`                // 获取表结构的源实例IP
	RemotePort int    `json:"remote_port"  validate:"required,lt=65536,gte=3306"` // 获取表结构的源实例Port
}

// SenmanticCheckRunTimeCtx TODO
type SenmanticCheckRunTimeCtx struct {
	dbConn                      *native.DbWorker
	adminUser                   string
	adminPwd                    string
	socket                      string
	version                     string
	remoteDefaultEngineIsTokudb bool
	remoteVersion               string
	remoteCharset               string
	afterdealSchemafile         string // schema sqlfile 处理之后的文件
	taskdir                     string
	schemafilename              string
}

// Precheck  前置检查
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) Precheck() (err error) {
	if !osutil.FileExist(c.Params.SchemaFile) {
		return fmt.Errorf("%s文件不存在", c.Params.SchemaFile)
	}
	for _, o := range c.Params.ExcuteObjects {
		if !osutil.FileExist(path.Join(cst.BK_PKG_INSTALL_PATH, o.SQLFile)) {
			return fmt.Errorf("%s文件不存在", o.SQLFile)
		}
	}
	return nil
}

// Example TODO
func (c *SemanticCheckComp) Example() interface{} {
	comp := SemanticCheckComp{
		Params: SenmanticCheckParam{
			Host:       "1.1.1.1",
			Port:       3306,
			SchemaFile: "db_schema.sql",
			ExcuteObjects: []ExcuteSQLFileObj{
				{
					SQLFile:       "test1.sql",
					IgnoreDbNames: []string{"db9"},
					DbNames:       []string{"db_100*", "db8"},
				},
				{
					SQLFile:       "test2.sql",
					IgnoreDbNames: []string{"db90"},
					DbNames:       []string{"db_200*", "db7"},
				},
			},
			RemoteHost: "2.2.2.2",
			RemotePort: 3306,
		},
	}
	return comp
}

// Init TODO
//
//	@receiver c
//	@receiver uid
//	@return err
func (c *SemanticCheckComp) Init(uid string) (err error) {
	c.taskdir = path.Join(cst.BK_PKG_INSTALL_PATH, fmt.Sprintf("semantic_check_%s", uid))
	if err = os.MkdirAll(c.taskdir, os.ModePerm); err != nil {
		logger.Error("初始化任务目录失败%s:%s", c.taskdir, err.Error())
		return
	}

	c.schemafilename = path.Base(c.Params.SchemaFile)
	// 将表结构文件移动到target dir
	if err = os.Rename(c.Params.SchemaFile, path.Join(c.taskdir, c.schemafilename)); err != nil {
		logger.Error("将表结构文件移动到%s 错误:%s", c.taskdir, err.Error())
		return
	}
	if err = c.initLocalRuntimeCtxParam(); err != nil {
		return
	}
	return c.initRemoteRuntimeCtxParam()
}

// initRemoteRuntimeCtxParam TODO
//
//	initRuntimeCtxParam 初始化运行时参数
//	@receiver c
//	@return err
func (c *SemanticCheckComp) initRemoteRuntimeCtxParam() (err error) {
	remotedbConn, err := native.InsObject{
		Host: c.Params.RemoteHost,
		Port: c.Params.RemotePort,
		User: c.GeneralParam.RuntimeAccountParam.MonitorAccessAllUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.MonitorAccessAllPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %s:%d failed:%s", c.Params.RemoteHost, c.Params.Port, err.Error())
		return err
	}
	defer func() {
		if remotedbConn.Db != nil {
			remotedbConn.Db.Close()
		}
	}()
	if c.remoteCharset, err = remotedbConn.ShowServerCharset(); err != nil {
		logger.Error("获取源实例的字符集失败:%s", err.Error())
		return err
	}
	if c.remoteVersion, err = remotedbConn.SelectVersion(); err != nil {
		logger.Error("获取源实例的Version:%s", err.Error())
		return err
	}
	if c.remoteDefaultEngineIsTokudb, err = remotedbConn.IsSupportTokudb(); err != nil {
		logger.Error("判断源实例是否支持:%s", err.Error())
		return err
	}
	return err
}

func (c *SemanticCheckComp) initLocalRuntimeCtxParam() (err error) {
	c.adminUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.adminPwd = c.GeneralParam.RuntimeAccountParam.AdminPwd
	c.dbConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.adminUser,
		Pwd:  c.adminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	c.socket, err = c.dbConn.ShowSocket()
	if err != nil {
		logger.Warn("获取本实例socket val 失败")
	}
	c.version, err = c.dbConn.SelectVersion()
	if err != nil {
		logger.Error("获取本实例Version失败:%s", err.Error())
		return err
	}
	return nil
}

// dealWithSchemaFile 导入前处理导入文件
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) dealWithSchemaFile() (err error) {
	script := fmt.Sprintf("cat %s ", path.Join(c.taskdir, c.schemafilename))
	if c.remoteDefaultEngineIsTokudb {
		script += ` | sed -e 's/ROW_FORMAT=TOKUDB_ZLIB/ROW_FORMAT=default/'`
	}
	// 将没有包含"CREATE TABLE IF NOT EXISTS"的行做替换（直接替换会导致替换结果出现两次IF NOT EXISTS）
	script += ` | sed '/CREATE TABLE IF NOT EXISTS /! s/^CREATE TABLE /CREATE TABLE IF NOT EXISTS /'`
	engine := "INNODB"
	if c.remoteDefaultEngineIsTokudb {
		engine = "MYISAM"
	}
	switch {
	case regexp.MustCompile(`tspider-3`).MatchString(c.remoteVersion):
		script += ` | sed -e 's/99106 ROW_FORMAT=GCS_DYNAMIC/99104 ROW_FORMAT=DYNAMIC/i'`
		script += ` | sed -e 's/99104 COMPRESSED/99999 COMPRESSED/i'`
		script += ` | sed -e 's/ROW_FORMAT=FIXED//i'`
		script += fmt.Sprintf(" | sed -e 's/ENGINE=SPIDER /ENGINE=%s ROW_FORMAT=DYNAMIC /i'", engine)
		script += " | sed '/^ PARTITION `pt/d' "
		script += fmt.Sprintf(" | sed 's/ENGINE = SPIDER,$/ENGINE = %s) ;/g'", engine)
		script += ` | sed 's/MOD [0-9]*)$/MOD 1)/g'`
	case regexp.MustCompile(`spider`).MatchString(c.remoteVersion):
		script += ` | sed -e 's/99106 ROW_FORMAT=GCS_DYNAMIC/99104 ROW_FORMAT=DYNAMIC/i'`
		script += ` | sed -e 's/99104 COMPRESSED/99999 COMPRESSED/i'`
		script += ` | sed -e 's/ROW_FORMAT=FIXED//i'`
		script += fmt.Sprintf(" | sed -e 's/ENGINE=SPIDER /ENGINE=%s ROW_FORMAT=DYNAMIC /i'", engine)
		script += ` | sed '/^ PARTITION pt/d'`
		script += "| sed '/^ PARTITION `pt/d'"
		script += fmt.Sprintf(" | sed 's/ENGINE = SPIDER,$/ENGINE = %s) \\\\*\\\\/;/g'", engine)
		script += `| sed 's/%[0-9]*)$/\%1)/g'`
	default:
		script += " | sed -e 's/99106 ROW_FORMAT=GCS_DYNAMIC/99104 ROW_FORMAT=DYNAMIC/i'"
		script += " | sed -e 's/99104 COMPRESSED/99999 COMPRESSED/i'"
		script += " | sed -e 's/ROW_FORMAT=FIXED//i'"
		script += " | sed -e 's/ENGINE=SPIDER DEFAULT CHARSET=/ENGINE=INNODB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=/i'"
	}
	logger.Info("导入前预处理命令:%s", script)
	stdOutFileName := path.Join(c.taskdir, c.schemafilename+".new")
	stdOutFile, err := os.OpenFile(stdOutFileName, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.ModePerm)
	if err != nil {
		return fmt.Errorf("open file %s failed, err:%w", stdOutFileName, err)
	}
	defer func() {
		if err := stdOutFile.Close(); err != nil {
			logger.Warn("close file %s failed, err:%s", stdOutFileName, err.Error())
		}
	}()

	stdErrFileName := path.Join(c.taskdir, c.schemafilename+".new.err")
	stdErrFile, err := os.OpenFile(stdErrFileName, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.ModePerm)
	if err != nil {
		return fmt.Errorf("open %s failed, err:%+v", stdErrFileName, err)
	}
	defer func() {
		if err := stdErrFile.Close(); err != nil {
			logger.Warn("close file %s failed, err:%s", stdErrFileName, err.Error())
		}
	}()
	logger.Info(
		"预处理导出的表结构[doing]: 源文件(%s) ==> 预处理后文件(%s), 错误输出(%s)",
		c.Params.SchemaFile,
		stdOutFileName,
		stdErrFileName,
	)
	cmd := exec.Command("/bin/bash", "-c", script)
	cmd.Stdout = stdOutFile
	cmd.Stderr = stdErrFile
	if err := cmd.Run(); err != nil {
		logger.Error("运行预处理失败%s", err.Error())
		return err
	}
	logger.Info(
		"预处理导出的表结构[doing]: 源文件(%s) ==> 预处理后文件(%s), 错误输出(%s)",
		c.Params.SchemaFile,
		stdOutFileName,
		stdErrFileName,
	)
	c.afterdealSchemafile = stdOutFileName
	return nil
}

// LoadSchema 导入远程表结构
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) LoadSchema() (err error) {
	if err = c.dealWithSchemaFile(); err != nil {
		logger.Error("预处理导入文件失败:%s", err.Error())
		return err
	}
	return mysqlutil.ExecuteSqlAtLocal{
		Host:     c.Params.Host,
		Port:     c.Params.Port,
		Charset:  c.remoteCharset,
		Socket:   c.socket,
		User:     c.adminUser,
		Password: c.adminPwd,
	}.ExcuteSqlByMySQLClient(c.afterdealSchemafile, []string{native.TEST_DB})
}

// Run 运行语义检查
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) Run() (err error) {
	if err = c.LoadSchema(); err != nil {
		logger.Error("导入目标实例%s:%d表结构失败", c.Params.RemoteHost, c.Params.RemotePort)
		return err
	}
	e := ExcuteSQLFileComp{
		GeneralParam: c.GeneralParam,
		Params: &ExcuteSQLFileParam{
			Host:          c.Params.Host,
			Ports:         []int{c.Params.Port},
			CharSet:       c.remoteCharset,
			ExcuteObjects: c.Params.ExcuteObjects,
			Force:         false,
		},
		ExcuteSQLFileRunTimeCtx: ExcuteSQLFileRunTimeCtx{},
	}
	if err = e.Init(); err != nil {
		return err
	}
	if err = e.Excute(); err != nil {
		return err
	}
	return nil
}

// Clean  清理并重启语义实例
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) Clean() (err error) {
	logger.Info("开始清除语义检查的实例...")
	if err = c.initLocalRuntimeCtxParam(); err != nil {
		return err
	}
	if err = c.cleandata(); err != nil {
		logger.Warn("清理语义实例失败：%s", err.Error())
		return
	}
	if err = c.restart(); err != nil {
		logger.Error("重启语义实例失败：%s", err.Error())
		return
	}
	logger.Info("清理语义检查实例成功~")
	return
}

// restart TODO
// shutdown 重启语义检查实例
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) restart() (err error) {
	err = computil.ShutdownMySQLParam{
		MySQLUser: c.adminUser,
		MySQLPwd:  c.adminPwd,
		Socket:    c.socket,
	}.ShutdownMySQLBySocket()
	if err != nil {
		logger.Error("关闭实例失败:%s", err.Error())
		return err
	}
	p := &computil.StartMySQLParam{
		MyCnfName: util.GetMyCnfFileName(c.Params.Port),
		MySQLUser: c.adminUser,
		MySQLPwd:  c.adminPwd,
		Socket:    c.socket,
	}
	_, err = p.StartMysqlInstance()
	if err != nil {
		logger.Error("启动实例失败:%s", err.Error())
		return err
	}
	return
}

// cleandata TODO
// DropSenmanticInstanceDatabases 清楚语义实例的数据库
//
//	@receiver c
//	@return err
func (c *SemanticCheckComp) cleandata() (err error) {
	alldbs, err := c.dbConn.ShowDatabases()
	if err != nil {
		logger.Error("清理实例：获取语义检查实例本地实例失败%s", err.Error())
		return err
	}
	testTbls, err := c.dbConn.ShowTables(native.TEST_DB)
	if err != nil {
		logger.Error("清理实例：获取test库内的表失败：%s", err.Error())
		return err
	}
	dbInfobaseTbls, err := c.dbConn.ShowTables(native.INFODBA_SCHEMA)
	if err != nil {
		logger.Error("清理实例：获取 infodba_schema 库内的表失败：%s", err.Error())
		return err
	}

	var wg sync.WaitGroup
	errChan := make(chan error, 1)
	pool, _ := ants.NewPool(100)
	defer pool.Release()

	dropdbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabases(c.version))
	logger.Info("will drop databases is:%v", dropdbs)
	f := func(db string) func() {
		return func() {
			_, err := c.dbConn.Exec(fmt.Sprintf("drop database `%s`;", db))
			if err != nil {
				errChan <- fmt.Errorf("drop database %s,err:%w", db, err)
			}
			wg.Done()
		}
	}
	for _, db := range dropdbs {
		wg.Add(1)
		pool.Submit(f(db))
	}
	type db = string
	type tables = []string
	var specialDbTbls map[db]tables
	specialDbTbls = make(map[string][]string)
	specialDbTbls[native.INFODBA_SCHEMA] = util.FilterOutStringSlice(testTbls, []string{"conn_log", "free_space"})
	specialDbTbls[native.INFODBA_SCHEMA] = util.FilterOutStringSlice(
		dbInfobaseTbls,
		[]string{"QUERY_RESPONSE_TIME", "check_heartbeat", "checksum", "master_slave_heartbeat", "spes_status"},
	)
	ff := func(db, tbl string) func() {
		return func() {
			_, err := c.dbConn.Exec(fmt.Sprintf("drop table if exists `%s`.`%s`;", db, tbl))
			if err != nil {
				errChan <- fmt.Errorf("drop table if exists `%s`.`%s`,err:%w", db, tbl, err)
			}
			wg.Done()
		}
	}
	for db, tbls := range specialDbTbls {
		for _, tbl := range tbls {
			wg.Add(1)
			pool.Submit(ff(db, tbl))
		}
	}
	wg.Wait()
	select {
	case err := <-errChan:
		logger.Error("drop db failed: %s", err.Error())
		return err
	default:
	}
	return nil
}
