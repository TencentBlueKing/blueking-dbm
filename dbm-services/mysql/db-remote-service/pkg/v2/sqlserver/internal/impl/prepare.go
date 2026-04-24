package impl

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	_ "github.com/denisenkom/go-mssqldb"

	"github.com/jmoiron/sqlx"
)

// Prepare 建立到 SQLServer 的连接, 取出一条 conn.
//
// SQLServer 不需要 timezone / charset, DSN 固定连 master 库.
//
// 关于 @@SPID:
//
//	v1 的 rpc_core/execute_cmds_on_addr.go:72 有一段 CONNECTION_ID() 逻辑,
//	但那段代码只在 db.DriverName() == "mysql" 时执行, SQLServer 走不到,
//	所以 v1 的 SQLServer 从未获取过 session id, 也从未在超时时 KILL 过后端 session.
//
//	SQLServer 对应的能力是 SELECT @@SPID + KILL <spid>, 但这属于 v1 未验证过的新功能.
//	在没有充分测试之前不启用, 避免引入未知风险.
//	如果将来需要超时 KILL, 取消下面 @@SPID 相关注释即可.
//
// 返回值约定:
//   - 成功: db, conn 非空, 调用方需要在用完后调用 Clean
//   - 失败: 全部为 nil, 内部已清理中间产物
func Prepare(ctx context.Context, addr, user, password string, timeout int) (*sqlx.DB, *sqlx.Conn, error) {
	host := strings.Split(addr, ":")[0]
	port := strings.Split(addr, ":")[1]

	dsn := fmt.Sprintf(
		"server=%s;port=%s;user id=%s;password=%s;database=master;encrypt=disable",
		host, port, user, password,
	)
	safeDSN := fmt.Sprintf(
		"server=%s;port=%s;user id=%s;password=***;database=master;encrypt=disable",
		host, port, user,
	)

	connCtx, cancel := context.WithTimeout(ctx, time.Duration(timeout)*time.Second)
	defer cancel()

	db, err := sqlx.ConnectContext(connCtx, "sqlserver", dsn)
	if err != nil {
		slog.Error("v2 sqlserver failed to connect",
			slog.String("error", err.Error()),
			slog.String("dsn", safeDSN),
			slog.String("addr", addr),
			slog.String("user", user),
		)
		return nil, nil, err
	}

	conn, err := db.Connx(ctx)
	if err != nil {
		_ = db.Close()
		return nil, nil, err
	}

	// 如果将来需要 spid 用于超时 KILL, 取消以下注释并修改返回值:
	// var spid int64
	// err = conn.GetContext(ctx, &spid, `SELECT @@SPID`)
	// if err != nil {
	// 	_ = conn.Close()
	// 	_ = db.Close()
	// 	return nil, nil, err
	// }

	return db, conn, nil
}

// Clean 关闭连接, 释放本地资源.
//
// v1 的 rpc_core/execute_cmds_on_addr.go 里 SQLServer 的清理只有 db.Close() + conn.Close(),
// 没有 KILL session 的逻辑 (connId 永远为 0). v2 保持一致, 只做 Close.
//
// 如果将来需要 KILL session, 可以加上 spid 参数:
//
//	func Clean(db *sqlx.DB, conn *sqlx.Conn, spid int64) {
//	    if spid > 0 && db != nil {
//	        _, _ = db.Exec(fmt.Sprintf("KILL %d", spid))
//	    }
//	    ...
//	}
func Clean(db *sqlx.DB, conn *sqlx.Conn) {
	if conn != nil {
		_ = conn.Close()
	}
	if db != nil {
		_ = db.Close()
	}
}
