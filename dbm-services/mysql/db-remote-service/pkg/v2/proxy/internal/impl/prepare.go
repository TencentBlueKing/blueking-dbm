package impl

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	_ "github.com/go-sql-driver/mysql"

	"github.com/avast/retry-go/v4"
	"github.com/jmoiron/sqlx"
)

// Prepare 建立到 proxy 的连接并取出一条 conn.
//
// proxy 不支持 timezone / charset / CONNECTION_ID，DSN 只有 timeout。
func Prepare(ctx context.Context, addr, user, password string, timeout int) (*sqlx.DB, *sqlx.Conn, error) {
	dsn := fmt.Sprintf(`%s:%s@tcp(%s)/?timeout=%ds`, user, password, addr, timeout)
	safeDSN := fmt.Sprintf(`%s:***@tcp(%s)/?timeout=%ds`, user, addr, timeout)

	var db *sqlx.DB
	err := retry.Do(
		func() error {
			var e error
			db, e = sqlx.ConnectContext(ctx, "mysql", dsn)
			return e
		},
		retry.Context(ctx),
		retry.Attempts(3),
		retry.Delay(2*time.Second),
		retry.DelayType(retry.FixedDelay),
	)
	if err != nil {
		slog.Error(
			"v2 proxy failed to connect",
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

	return db, conn, nil
}

// Clean 关闭连接。proxy 没有 CONNECTION_ID，不需要 KILL。
func Clean(db *sqlx.DB, conn *sqlx.Conn) {
	if conn != nil {
		_ = conn.Close()
	}
	if db != nil {
		_ = db.Close()
	}
}
