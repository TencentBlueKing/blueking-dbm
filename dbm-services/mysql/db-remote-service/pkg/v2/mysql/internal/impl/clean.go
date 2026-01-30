package impl

import (
	"context"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

func Clean(db *sqlx.DB, conn *sqlx.Conn, connId int64) {
	if connId != 0 && db != nil {
		// 为 KILL 操作设置超时，避免长时间阻塞
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_, _ = db.ExecContext(ctx, fmt.Sprintf(`KILL %d`, connId))
	}

	if conn != nil {
		_ = conn.Close()
	}

	if db != nil {
		_ = db.Close()
	}
}
