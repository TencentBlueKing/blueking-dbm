package computil

import (
	"fmt"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// StartMySQLParam 实例启动参数
type StartMySQLParam struct {
	MediaDir        string // /usr/local/mysql/bin MySQL安装目录
	MyCnfName       string // 必须参数，需要指定启动配置文件
	MySQLUser       string // use for check mysqld start successuly
	MySQLPwd        string // use for check mysqld start successuly
	Socket          string // 如果socket参数存在，优先使用socket去连接mysql探测
	Host            string // 如果socket参数不存在,则使用ip,port 方式去连接探测
	Port            int    // 如果socket参数不存在,则使用ip,port 方式去连接探测
	SkipSlaveFlag   bool   // --skip-slave-start
	SkipGrantTables bool   // --skip-grant-tables
}

// RestartMysqlInstanceNormal TODO
func RestartMysqlInstanceNormal(inst native.InsObject) error {
	mycnf := util.GetMyCnfFileName(inst.Port)
	startParam := StartMySQLParam{
		Host:      inst.Host,
		Port:      inst.Port,
		Socket:    inst.Socket,
		MySQLUser: inst.User,
		MySQLPwd:  inst.Pwd,

		MyCnfName: mycnf,
		MediaDir:  cst.MysqldInstallPath,
	}
	if _, err := startParam.RestartMysqlInstance(); err != nil {
		return err
	}
	return nil
}

// IsInstanceRunning TODO
func IsInstanceRunning(inst native.InsObject) bool {
	mycnf := util.GetMyCnfFileName(inst.Port)
	startParam := StartMySQLParam{
		Host:      inst.Host,
		Port:      inst.Port,
		Socket:    inst.Socket,
		MySQLUser: inst.User,
		MySQLPwd:  inst.Pwd,

		MyCnfName: mycnf,
		MediaDir:  cst.MysqldInstallPath,
	}
	if err := startParam.CheckMysqlProcess(); err != nil {
		return false
	}
	return true
}

// RestartMysqlInstance TODO
func (p *StartMySQLParam) RestartMysqlInstance() (pid int, err error) {
	if err := ShutdownMySQLBySocket2(p.MySQLUser, p.MySQLPwd, p.Socket); err != nil {
		return 0, err
	}
	return p.StartMysqlInstance()
}

// StartMysqlInstance 	启动mysqld
// 如果 MySQLUser 为空则不检查连接性
func (p *StartMySQLParam) StartMysqlInstance() (pid int, err error) {
	var (
		mediaDir  = p.MediaDir
		numaStr   = osutil.GetNumaStr()
		myCnfName = p.MyCnfName
		startCmd  = fmt.Sprintf(
			`ulimit -n 204800; 
cd %s && %s ./bin/mysqld_safe --defaults-file=%s --user=mysql `, mediaDir, numaStr, myCnfName,
		)
	)
	if p.SkipSlaveFlag {
		startCmd += "--skip-slave-start "
	}
	if p.SkipGrantTables {
		startCmd += " --skip-grant-tables "
	}
	startCmd += " &"
	logger.Info(fmt.Sprintf("execute mysqld_safe: [%s]", startCmd))
	pid, err = osutil.RunInBG(false, startCmd)
	if err != nil {
		return
	}
	return pid, util.Retry(
		util.RetryConfig{
			Times:     40,
			DelayTime: 5 * time.Second,
		}, func() error { return p.CheckMysqlProcess() },
	)
}

// CheckMysqlProcess TODO
func (p *StartMySQLParam) CheckMysqlProcess() (err error) {
	if p.MyCnfName == "" {
		p.MyCnfName = util.GetMyCnfFileName(p.Port)
	}
	if p.MediaDir == "" {
		p.MediaDir = cst.MysqldInstallPath
	}
	checkMysqldCmd := fmt.Sprintf("ps -efwww | grep %s|grep 'mysqld_safe '| grep -v grep", p.MyCnfName)
	out, err := osutil.ExecShellCommand(false, checkMysqldCmd)
	if err != nil {
		// 如果是 shell 错误，不必等待 retry? 暂时保持 retry
		errStr := fmt.Sprintf("exec shell error %s", checkMysqldCmd)
		err = errors.WithMessage(err, errStr)
		logger.Error(err.Error())
		return
	}
	regStr := fmt.Sprintf("mysqld_safe\\s+--defaults-file=%s", p.MyCnfName)
	if !regexp.MustCompile(regStr).MatchString(out) {
		logger.Info("regStr[%s] not match result[%s] ", regStr, out)
		return fmt.Errorf("ps grep 不到相关进程，可能没有完全启动请稍等")
	}

	if p.MySQLUser == "" {
		// 不检查连接性
		return nil
	}
	addr := fmt.Sprintf("%s:%d", p.Host, p.Port)
	dsn := native.DsnByTcp(addr, p.MySQLUser, p.MySQLPwd)
	if p.Socket != "" {
		dsn = native.DsnBySocket(p.Socket, p.MySQLUser, p.MySQLPwd)
	}
	// 没有 error 可以认为连接成功
	if _, err = native.NewDbWorker(dsn); err != nil {
		return
	}
	logger.Info("connect %s successfully", addr)
	return err
}

// ShutdownMySQLParam TODO
type ShutdownMySQLParam struct {
	MySQLUser string
	MySQLPwd  string
	Socket    string
}

// ShutdownMySQLBySocket 通过 socket 连接关闭 MySQL，这样的关闭更加可靠。
//  1. 可能还需要考虑 shutdown 超时问题。
//  2. 可能需要通过 expect 方式，避免暴露密码。
func (param ShutdownMySQLParam) ShutdownMySQLBySocket() (err error) {
	shellCMD := fmt.Sprintf("mysqladmin -u%s -p%s -S %s shutdown", param.MySQLUser, param.MySQLPwd, param.Socket)
	output, err := mysqlutil.ExecCommandMySQLShell(shellCMD)
	if err != nil {
		if !strings.Contains(err.Error(), "Can't connect to local MySQL server") {
			logger.Info("shutdown mysql error %s,output:%s. cmd:%s", err.Error(), output, shellCMD)
			return err
		} else {
			logger.Warn("mysqld %s is not running: %s", param.Socket, err.Error())
		}
	}
	return JudgeMysqldShutDown(param.Socket)
}

// ShutdownMySQLBySocket2 通过 socket 连接关闭 MySQL，这样的关闭更加可靠。
//  1. 可能还需要考虑 shutdown 超时问题。
//  2. 可能需要通过 expect 方式，避免暴露密码。
func ShutdownMySQLBySocket2(user, password, socket string) (err error) {
	param := &ShutdownMySQLParam{MySQLUser: user, MySQLPwd: password, Socket: socket}
	return param.ShutdownMySQLBySocket()
}

// ForceShutDownMySQL 强制关闭mysqld
//
//	@receiver param
//	@return err
func (param ShutdownMySQLParam) ForceShutDownMySQL() (err error) {
	shellCMD := fmt.Sprintf("mysqladmin -u%s -p%s -S%s shutdown", param.MySQLUser, param.MySQLPwd, param.Socket)
	output, err := mysqlutil.ExecCommandMySQLShell(shellCMD)
	if err != nil {
		logger.Warn("使用mysqladmin shutdown 失败:%s output:%s", err.Error(), string(output))
		// 如果用 shutdown 执行失败
		// 尝试用 kill -2 去停止mysql
		if err = KillMySQLD(fmt.Sprintf("socket=%s", param.Socket)); err != nil {
			return err
		}
	}
	return JudgeMysqldShutDown(param.Socket)
}

// JudgeMysqldShutDown  err == nil 表示 ps aux 没有发现 mysqld
func JudgeMysqldShutDown(prefix string) (err error) {
	logger.Info("start checking mysqld process .... grep prefix is %s", prefix)
	// 120秒超时
	ot := time.NewTimer(time.Duration(time.Second * 120))
	defer ot.Stop()
	tk := time.NewTicker(2 * time.Second)
	for {
		select {
		case <-ot.C:
			return errors.New("停止MySQL超时")
		case <-tk.C:
			// 不能直接grep mysqld 因为存在 mysqldata
			shellCMD := fmt.Sprintf("ps -efwww | grep %s|grep -E 'mysqld |mysqld_safe'| grep -v grep|wc -l", prefix)
			out, err := osutil.ExecShellCommand(false, shellCMD)
			if err != nil {
				logger.Info("execute %s get an error:%s", shellCMD, err.Error())
				return err
			}
			logger.Info("shell output information is %s", out)
			if strings.TrimSpace(out) == "0" {
				logger.Info("mysql has been exited,success～ ,process count is %s", out)
				return nil
			}
			logger.Warn("mysqld 进程还在，等待进程关闭...")
		}
	}
}

// KillReMindMySQLClient  kill  命令行残留的mysql client 连接
//
//	@receiver regexpStr 寻找mysql client 连接的pid
//	@return error
func KillReMindMySQLClient(regexpStr string) error {
	var err error
	logger.Info("start kill -9 mysql")
	if strings.TrimSpace(regexpStr) == "" {
		return errors.New("grep 参数为空，不允许！！！")
	}
	killComand := fmt.Sprintf(
		"ps -efwww|grep ' %s '|egrep -v mysqld|grep mysql|egrep -v grep |awk '{print $2}'|xargs  kill -9", regexpStr,
	)
	logger.Info(" kill command is %s", killComand)
	_, err = osutil.ExecShellCommand(false, killComand)
	if err != nil {
		logger.Error("execute %s get an error:%s", killComand, err.Error())
	}
	killSocketComand := fmt.Sprintf(
		"ps -efwww|grep '%s'|egrep -v 'mysqld |mysqld_safe'|grep mysql|grep mysql.sock|egrep -v grep |awk '{print $2}'|xargs  kill -9",
		regexpStr,
	)
	logger.Info(" kill command is %s", killSocketComand)
	_, err = osutil.ExecShellCommand(false, killSocketComand)
	if err != nil {
		logger.Error("execute %s get an error:%s", killComand, err.Error())
	}
	return err
}

// KillMySQLD kill -15 mysqld
//
//	@receiver regexpStr: 根据regexpStr grep 进程IDs
//	@return error
func KillMySQLD(regexpStr string) error {
	logger.Info("start kill -15 mysqld")
	if strings.TrimSpace(regexpStr) == "" {
		return errors.New("grep 参数为空，不允许！！！")
	}
	shellCMD := fmt.Sprintf("ps -efwww|grep %s|egrep -v grep |wc -l", regexpStr)
	out, err := osutil.ExecShellCommand(false, shellCMD)
	if err != nil {
		logger.Error("execute %s get an error:%s", shellCMD, err.Error())
		return err
	}
	// 此处不应该返回错误
	if strings.TrimSpace(out) == "0" {
		logger.Info("process has been exit,You Can Consider Mysqld been shutdown")
		return nil
	}
	logger.Info("will kill this %s", out)
	killCmd := fmt.Sprintf("ps -efwww|grep %s|egrep -v grep |awk '{print $2}'|xargs  kill -15", regexpStr)
	logger.Info(" kill command is %s", killCmd)
	kOutput, err := osutil.ExecShellCommand(false, killCmd)
	if err != nil {
		logger.Error("execute %s get an error:%s,output:%s", killCmd, err.Error(), string(kOutput))
		return err
	}
	return nil
}

// GetMysqlSystemDatabases 获取mysql系统库列表
// 小于5.0："mysql"
// 小于5.5："information_schema", "mysql"
// 小于5.7："information_schema", "mysql", "performance_schema"
// 大于5.7："information_schema", "mysql", "performance_schema", "sys"
func GetMysqlSystemDatabases(version string) []string {
	DBs := []string{"information_schema", "mysql", "performance_schema"}

	if mysqlutil.MySQLVersionParse(version) > mysqlutil.MySQLVersionParse("5.7.0") {
		DBs = append(DBs, "sys")
	} else if mysqlutil.MySQLVersionParse(version) < mysqlutil.MySQLVersionParse("5.0.0") {
		DBs = []string{"mysql"}
	} else if mysqlutil.MySQLVersionParse(version) < mysqlutil.MySQLVersionParse("5.5.0") {
		DBs = []string{"information_schema", "mysql"}
	}
	return DBs
}

// GetGcsSystemDatabases 获取mysql系统库列表，包括GCS监控管理库
// 小于5.0："mysql", native.INFODBA_SCHEMA, "test"
// 小于5.5："information_schema", "mysql", native.INFODBA_SCHEMA, "test"
// 小于5.7："information_schema", "mysql", "performance_schema", native.INFODBA_SCHEMA, "test"
// 大于5.7："information_schema", "mysql", "performance_schema", "sys",native.INFODBA_SCHEMA, "test"
func GetGcsSystemDatabases(version string) []string {
	DBs := GetMysqlSystemDatabases(version)
	DBs = append(DBs, native.INFODBA_SCHEMA)
	DBs = append(DBs, native.TEST_DB)
	return DBs
}

// GetGcsSystemDatabasesIgnoreTest TODO
func GetGcsSystemDatabasesIgnoreTest(version string) []string {
	DBs := GetMysqlSystemDatabases(version)
	DBs = append(DBs, native.INFODBA_SCHEMA)
	return DBs
}
