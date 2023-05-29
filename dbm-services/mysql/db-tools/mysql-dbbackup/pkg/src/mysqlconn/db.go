package mysqlconn

import (
	"context"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/spf13/cast"
)

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

// DbWorker TODO
type DbWorker struct {
	Dsn     string
	Db      *sqlx.DB
	instObj *InsObject
}

// Conn Connect Tcp/Ip
func (o InsObject) Conn() (*DbWorker, error) {
	if o.Socket != "" {
		return NewDbWorker(DsnBySocket(o.Socket, o.User, o.Pwd))
	} else {
		return NewDbWorker(DsnByTcp(fmt.Sprintf("%s:%d", o.Host, o.Port), o.User, o.Pwd))
	}
}

// DsnByTcp TODO
func DsnByTcp(address, user, password string) string {
	return fmt.Sprintf("%s:%s@tcp(%s)/?timeout=5s&multiStatements=true", user, password, address)
}

// DsnBySocket TODO
func DsnBySocket(socket, user, password string) string {
	return fmt.Sprintf("%s:%s@unix(%s)/?timeout=5s&multiStatements=true", user, password, socket)
}

// NewDbWorker TODO
func NewDbWorker(dsn string) (*DbWorker, error) {
	var err error
	dbw := &DbWorker{
		Dsn: dsn,
	}
	dbw.Db, err = sqlx.Open("mysql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	// check connect with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := dbw.Db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping context failed, err:%w", err)
	}
	if err := dbw.Db.Ping(); err != nil {
		return nil, err
	}
	return dbw, nil
}

// NewDbWorkerNoPing mysql-proxy supports very few queries, which do not include PINGs
// In this case, we do not ping after a connection is built,
// and let the function caller to decide if the connection is healthy
func NewDbWorkerNoPing(host, user, password string) (*DbWorker, error) {
	var err error
	dbw := &DbWorker{
		Dsn: fmt.Sprintf("%s:%s@tcp(%s)/?timeout=5s&multiStatements=false", user, password, host),
	}
	dbw.Db, err = sqlx.Open("mysql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	return dbw, nil
}

// Close connection
func (h *DbWorker) Close() {
	if h.Db != nil {
		if err := h.Db.Close(); err != nil {
			// logger.Warn("close db handler failed, err:%s", err.Error())
		}
	}
}

// GetOneValue connection
func (h *DbWorker) GetOneValue(query string) (string, error) {
	var v interface{}
	err := h.Db.QueryRow(query).Scan(&v)
	return cast.ToString(v), err
}
