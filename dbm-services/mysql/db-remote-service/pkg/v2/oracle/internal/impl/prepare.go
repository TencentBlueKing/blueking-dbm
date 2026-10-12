package impl

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"strconv"
	"time"

	"github.com/jmoiron/sqlx"
	go_ora "github.com/sijms/go-ora/v2"
)

// Prepare 建立到 Oracle 的连接, 取出一条 conn.
// 使用纯 Go 驱动 go-ora (DRS 以 CGO_ENABLED=0 构建, 不能使用依赖 OCI 的 godror),
// 不依赖 Oracle Instant Client, 支持 11.2 及以上版本.
func Prepare(ctx context.Context, addr, serviceName, user, password string, timeout int) (*sqlx.DB, *sqlx.Conn, error) {
	host, portStr, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, nil, fmt.Errorf("invalid address %s: %w", addr, err)
	}
	port, err := strconv.Atoi(portStr)
	if err != nil {
		return nil, nil, fmt.Errorf("invalid port in address %s: %w", addr, err)
	}

	dsn := go_ora.BuildUrl(host, port, serviceName, user, password, nil)
	safeDSN := fmt.Sprintf("oracle://%s:***@%s:%d/%s", user, host, port, serviceName)

	connCtx, cancel := context.WithTimeout(ctx, time.Duration(timeout)*time.Second)
	defer cancel()

	db, err := sqlx.ConnectContext(connCtx, "oracle", dsn)
	if err != nil {
		slog.Error("v2 oracle failed to connect",
			slog.String("error", err.Error()),
			slog.String("dsn", safeDSN),
			slog.String("addr", addr),
			slog.String("user", user),
		)
		return nil, nil, err
	}
	db.SetMaxOpenConns(1)

	conn, err := db.Connx(ctx)
	if err != nil {
		_ = db.Close()
		return nil, nil, err
	}

	return db, conn, nil
}

// Clean 关闭连接, 释放本地资源.
func Clean(db *sqlx.DB, conn *sqlx.Conn) {
	if conn != nil {
		_ = conn.Close()
	}
	if db != nil {
		_ = db.Close()
	}
}
