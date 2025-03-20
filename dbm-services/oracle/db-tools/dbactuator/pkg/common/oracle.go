// Package common 公共
package common

import (
	oracleClient "database/sql"
	"fmt"
	"time"

	"github.com/godror/godror"
	_ "github.com/godror/godror" // godror oracle 驱动
)

// GetInfoFromOracle 从oracle中获取信息
func GetInfoFromOracle(username string, password string, host string, port string,
	serviceName string, sql string, args ...any) (*oracleClient.DB, *oracleClient.Rows, error) {
	var db *oracleClient.DB
	var err error
	var rows *oracleClient.Rows
	var param godror.ConnectionParams
	param.Username = username
	param.Password = godror.NewPassword(password)
	param.Timezone = time.Local
	param.ConnectString = fmt.Sprintf("%s:%s/%s", host, port, serviceName)
	// 不使用连接池，使用短连接
	param.StandaloneConnection = true
	db = oracleClient.OpenDB(godror.NewConnector(param))
	err = db.Ping()
	if err != nil {
		return db, rows, err
	}
	rows, err = db.Query(sql, args...)
	if err != nil {
		return db, rows, err
	}
	return db, rows, nil
}
