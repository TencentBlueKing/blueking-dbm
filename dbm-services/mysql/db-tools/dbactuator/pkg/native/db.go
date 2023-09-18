package native

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql TODO

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// Instance TODO
type Instance struct {
	Host string `json:"host" example:"1.1.1.1"` // 当前实例的主机地址
	Port int    `json:"port" example:"33060"`   // 当前实例的端口
}

// Addr Ins Addr
func (o Instance) Addr() string {
	return fmt.Sprintf("%s:%d", o.Host, o.Port)
}

// InsObject 操作对象参数
// 可以用于操作 mysql or proxy 实例
type InsObject struct {
	Host    string `json:"host"`    // 当前实例的主机地址
	Port    int    `json:"port"`    // 当前实例的端口
	User    string `json:"user"`    // 连接当前实例的User
	Pwd     string `json:"pwd"`     // 连接当前实例的User Pwd
	Socket  string `json:"socket"`  // 连接socket
	Charset string `json:"charset"` // 连接字符集
	Options string `json:"options"` // 其它选项
	// 构造的 mysql client 访问命令
	mysqlCli string
}

func (o InsObject) tcpdsn() string {
	return fmt.Sprintf("%s:%d", o.Host, o.Port)
}

func (o InsObject) proxyAdminTcpDsn() string {
	return fmt.Sprintf("%s:%d", o.Host, GetProxyAdminPort(o.Port))
}

func (o InsObject) spiderAdminTcpDsn() string {
	return fmt.Sprintf("%s:%d", o.Host, o.Port)
}

// GetProxyAdminPort TODO
func GetProxyAdminPort(port int) int {
	return port + cst.ProxyAdminPortInc
}

// Opendb TODO
func Opendb(host, user, pwd, dbName string) (conn *sql.DB, err error) {
	return sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s)/%s", user, pwd, host, dbName))
}

// Conn Connect Tcp/Ip
func (o InsObject) Conn() (*DbWorker, error) {
	if o.Socket != "" {
		return NewDbWorker(DsnBySocket(o.Socket, o.User, o.Pwd))
	} else {
		return NewDbWorker(DsnByTcp(o.tcpdsn(), o.User, o.Pwd))
	}
}

// ConnBySocket Connect Tcp/Ip
func (o InsObject) ConnBySocket() (*DbWorker, error) {
	return NewDbWorker(DsnBySocket(o.Socket, o.User, o.Pwd))
}

// DsnByTcp TODO
func DsnByTcp(host, user, password string) string {
	return fmt.Sprintf("%s:%s@tcp(%s)/?timeout=5s&multiStatements=true", user, password, host)
}

// DsnBySocket TODO
func DsnBySocket(socket, user, password string) string {
	return fmt.Sprintf("%s:%s@unix(%s)/?timeout=5s&multiStatements=true", user, password, socket)
}

// MySQLClientCmd TODO
func (o InsObject) MySQLClientCmd(mysqlClient string) string {
	cmd := fmt.Sprintf(`%s --host=%s --port=%d --user=%s -p%s`, mysqlClient, o.Host, o.Port, o.User, o.Pwd)
	if o.Socket != "" {
		cmd += fmt.Sprintf(" --socket %s", o.Socket)
	}
	if o.Charset != "" {
		cmd += fmt.Sprintf(" --default-character-set=%s", o.Charset)
	}
	if o.Options != "" {
		cmd += " " + o.Options
	}
	o.mysqlCli = cmd
	return cmd
}

// MySQLClientExec 执行 mysql ... -e "sql" 命令
func (o InsObject) MySQLClientExec(mysqlClient, sqlStr string) (string, error) {
	if o.mysqlCli == "" {
		o.mysqlCli = o.MySQLClientCmd(mysqlClient)
	}
	cmd := fmt.Sprintf(`%s -A -Nse "%s"`, o.mysqlCli, sqlStr)
	return mysqlutil.ExecCommandMySQLShell(cmd)
}

// CheckInstanceConnIdle TODO
func (o InsObject) CheckInstanceConnIdle(sysUsers []string, sleepTime time.Duration) error {
	db, err := o.ConnBySocket()
	if err != nil {
		logger.Error("Connect %d failed,Err:%s", o.Port, err.Error())
		return err
	}
	defer db.Db.Close()

	//  检查非系统用户的processlist
	processLists, err := db.ShowApplicationProcesslist(sysUsers)
	if err != nil {
		return fmt.Errorf("获取%d processlist 失败,err:%w", o.Port, err)
	}
	if len(processLists) > 0 {
		return fmt.Errorf("实例%d 残留processlist 连接：%v", o.Port, processLists)
	}

	// 检查show open tables
	openTables, err := db.ShowOpenTables(sleepTime)
	if err != nil {
		return err
	}
	if len(openTables) > 0 {
		return fmt.Errorf("实例%d 存在 open tables:%v", o.Port, openTables)
	}
	return nil
}

// IsEmptyDB  过滤出系统库后，判断是否存在业务db
//
//	@receiver dblist
//	@return bool
func IsEmptyDB(dblist []string) bool {
	var whiteDBs = DBSys
	for _, db := range dblist {
		if !cmutil.HasElem(db, whiteDBs) {
			return false
		}
	}
	return true
}
