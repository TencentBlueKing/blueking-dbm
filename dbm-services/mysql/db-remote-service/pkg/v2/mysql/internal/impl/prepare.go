package impl

import (
	"context"

	_ "github.com/go-sql-driver/mysql" // mysql

	"github.com/jmoiron/sqlx"
)

// Prepare 建立到 addr 的连接, 取出一条 conn 并查出 server 端的 connection_id.
//
// ctx 一路透传到 sqlx.ConnectContext / db.Connx / SELECT CONNECTION_ID(),
// 调用方 (HTTP handler) cancel 时, 这里所有阻塞操作立刻退出, 不会浪费 RTT.
//
// 返回值约定:
//   - 成功: db, conn, connID 都非空, 调用方需要在用完后调用 Clean
//   - 失败: 全部为 nil/0, Prepare 内部已经清理了任何中间产物, 调用方不需要再调 Clean
func Prepare(ctx context.Context, addr, user, password, timezone, charset string, timeout int, preHookCmds []string, skipSetNames bool) (*sqlx.DB, *sqlx.Conn, int64, error) {
	db, err := makeConnection(ctx, addr, user, password, timezone, charset, timeout, preHookCmds, skipSetNames)
	if err != nil {
		return nil, nil, 0, err
	}

	conn, err := db.Connx(ctx)
	if err != nil {
		_ = db.Close()
		return nil, nil, 0, err
	}

	var connId int64
	err = conn.GetContext(ctx, &connId, `SELECT CONNECTION_ID()`)
	if err != nil {
		_ = conn.Close()
		_ = db.Close()
		return nil, nil, 0, err
	}

	return db, conn, connId, nil
}
