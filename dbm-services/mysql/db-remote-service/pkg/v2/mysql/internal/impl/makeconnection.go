package impl

import (
	"context"
	"fmt"
	"log/slog"
	"net/url"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql

	"github.com/avast/retry-go/v4"
	"github.com/jmoiron/sqlx"
)

// makeConnection 创建数据库连接，处理 default 字符集的特殊逻辑
func makeConnection(ctx context.Context, addr, user, password, timezone, charset string, timeout int, preHookCmds []string, skipSetNames bool) (*sqlx.DB, error) {
	if skipSetNames {
		return connectWithRetry(ctx, addr, user, password, timezone, "", timeout, preHookCmds)
	}

	if charset != "default" {
		return connectWithRetry(ctx, addr, user, password, timezone, charset, timeout, preHookCmds)
	}

	db, err := connectWithRetry(ctx, addr, user, password, timezone, "", timeout, preHookCmds)
	if err != nil {
		return nil, err
	}

	var serverCharset string
	err = db.QueryRowContext(ctx, `SELECT @@character_set_server`).Scan(&serverCharset)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("query server charset failed: %w", err)
	}

	slog.Info("mysql server charset", slog.String("addr", addr), slog.String("charset", serverCharset))
	_, err = db.ExecContext(ctx, fmt.Sprintf("SET NAMES '%s'", serverCharset))
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("set names %s failed: %w", serverCharset, err)
	}

	return db, nil
}

// connectWithRetry 带重试的数据库连接（纯粹的连接逻辑，不处理 default 字符集）
func connectWithRetry(ctx context.Context, addr, user, password, timezone, charset string, timeout int, preHookCmds []string) (db *sqlx.DB, err error) {
	dsn, safeDSN := buildDSN(addr, user, password, timezone, timeout)

	err = retry.Do(
		func() error {
			db, err = sqlx.ConnectContext(ctx, "mysql", dsn)
			if err != nil {
				return err
			}

			for _, cmd := range preHookCmds {
				if _, execErr := db.ExecContext(ctx, cmd); execErr != nil {
					_ = db.Close()
					db = nil
					return execErr
				}
			}

			if charset != "" {
				if _, execErr := db.ExecContext(ctx, fmt.Sprintf("SET NAMES '%s'", charset)); execErr != nil {
					_ = db.Close()
					db = nil
					return execErr
				}
			}

			return nil
		},
		retry.Context(ctx),
		retry.Attempts(3),
		retry.Delay(2*time.Second),
		retry.DelayType(retry.FixedDelay),
	)
	if err != nil {
		slog.Error(
			"v2 mysql failed to connect",
			slog.String("error", err.Error()),
			slog.String("dsn", safeDSN),
			slog.String("addr", addr),
			slog.String("user", user),
		)
		return nil, err
	}

	return db, nil
}

// buildDSN 同时构造真正用于连接的 dsn 和用于日志的 safeDSN (密码字段被 *** 替换).
//
// 任何对外可见的位置 (日志/metric/error message) 都只能用 safeDSN,
// 真实 dsn 仅作为 sqlx.Connect 的入参.
func buildDSN(addr, user, password, timezone string, timeout int) (dsn, safeDSN string) {
	tail := fmt.Sprintf(`@tcp(%s)/?timeout=%ds`, addr, timeout)
	if timezone != "" {
		tail += fmt.Sprintf("&time_zone=%s", url.QueryEscape(fmt.Sprintf(`'%s'`, timezone)))
	}

	dsn = fmt.Sprintf(`%s:%s%s`, user, password, tail)
	safeDSN = fmt.Sprintf(`%s:***%s`, user, tail)
	return dsn, safeDSN
}
