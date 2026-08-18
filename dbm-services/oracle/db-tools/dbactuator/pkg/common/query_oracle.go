// Package common 公共
package common

import (
	"database/sql"
	"fmt"

	"github.com/godror/godror"
	_ "github.com/godror/godror" // godror oracle 驱动
)

// oracleDriverName godror 驱动注册名
const oracleDriverName = "godror"

// OpenOracleAsSysdba 以 sysdba 身份打开本地 Oracle 连接（OS 认证，等价 sqlplus / as sysdba）。
func OpenOracleAsSysdba() (*sql.DB, error) {
	var param godror.ConnectionParams
	// OS 认证：不指定用户名/密码，走本地 bequeath/IPC 通道
	param.Username = ""
	param.ConnectString = ""
	// 关键三件套：外部认证 + sysdba 权限 + 独立连接（不走连接池）
	param.ExternalAuth = true
	param.IsSysDBA = true
	param.StandaloneConnection = true

	db := sql.OpenDB(godror.NewConnector(param))
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping 失败(sysdba os auth): %v", err)
	}
	return db, nil
}

// OpenOracle 使用普通账号打开远程 Oracle 连接。
func OpenOracle(user, password, host, port, service string) (*sql.DB, error) {
	dsn := fmt.Sprintf(`user="%s" password="%s" connectString="%s:%s/%s"`,
		user, password, host, port, service)
	return OpenOracleWithDSN(dsn)
}

// OpenOracleWithDSN 使用指定 DSN 打开连接并 Ping 一次。
func OpenOracleWithDSN(dsn string) (*sql.DB, error) {
	db, err := sql.Open(oracleDriverName, dsn)
	if err != nil {
		return nil, fmt.Errorf("sql.Open 失败: %v", err)
	}
	if err = db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping 失败: %v", err)
	}
	return db, nil
}

// QueryOracle 通用查询执行器：
//   - query：待执行的 SQL 语句
//   - scanRow：单行回调，负责调用 rows.Scan(...) 并把结果放入调用方自己的容器
//   - args：SQL 中的绑定参数（对应 :1、:2 等占位符）
//
// 该函数只负责"执行 + 遍历 + 错误处理"，具体如何映射列到业务结构由 scanRow 决定，
// 因此可以复用到任意行数、任意列结构的查询。
func QueryOracle(db *sql.DB, query string, scanRow func(rows *sql.Rows) error, args ...any) error {
	if db == nil {
		return fmt.Errorf("db 为空")
	}
	if scanRow == nil {
		return fmt.Errorf("scanRow 回调为空")
	}
	rows, err := db.Query(query, args...)
	if err != nil {
		return fmt.Errorf("执行查询失败: %v", err)
	}
	defer rows.Close()
	for rows.Next() {
		if err = scanRow(rows); err != nil {
			return fmt.Errorf("处理行失败: %v", err)
		}
	}
	if err = rows.Err(); err != nil {
		return fmt.Errorf("遍历结果失败: %v", err)
	}
	return nil
}
