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
func makeConnection(ctx context.Context, addr, user, password, timezone, charset string, timeout int) (*sqlx.DB, error) {
	// 如果不是 default 字符集，直接连接
	if charset != "default" {
		return connectWithRetry(ctx, addr, user, password, timezone, charset, timeout)
	}

	// 处理 default 字符集：先建立临时连接获取服务器字符集
	tempDB, err := connectWithRetry(ctx, addr, user, password, timezone, "", timeout)
	if err != nil {
		return nil, err
	}

	// 查询服务器字符集
	var serverCharset string
	err = tempDB.QueryRowContext(ctx, `SELECT @@character_set_server`).Scan(&serverCharset)
	// 无论成功与否，都关闭临时连接
	_ = tempDB.Close()

	if err != nil {
		return nil, fmt.Errorf("query server charset failed: %w", err)
	}

	// 使用实际字符集重新连接
	return connectWithRetry(ctx, addr, user, password, timezone, serverCharset, timeout)
}

// connectWithRetry 带重试的数据库连接（纯粹的连接逻辑，不处理 default 字符集）
func connectWithRetry(ctx context.Context, addr, user, password, timezone, charset string, timeout int) (db *sqlx.DB, err error) {
	dsn, safeDSN := buildDSN(addr, user, password, timezone, charset, timeout)

	err = retry.Do(
		func() error {
			db, err = sqlx.ConnectContext(ctx, "mysql", dsn)
			return err
		},
		retry.Context(ctx),
		retry.Attempts(3),
		retry.Delay(2*time.Second),
		retry.DelayType(retry.FixedDelay),
	)
	if err != nil {
		// 注意: 这里只能打 safeDSN, 真实 dsn 含明文密码绝不能进日志
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
func buildDSN(addr, user, password, timezone, charset string, timeout int) (dsn, safeDSN string) {
	tail := fmt.Sprintf(`@tcp(%s)/?timeout=%ds`, addr, timeout)
	if timezone != "" {
		tail += fmt.Sprintf("&time_zone=%s", url.QueryEscape(fmt.Sprintf(`'%s'`, timezone)))
	}
	if charset != "" {
		tail += fmt.Sprintf("&charset=%s", charset)
	}

	dsn = fmt.Sprintf(`%s:%s%s`, user, password, tail)
	safeDSN = fmt.Sprintf(`%s:***%s`, user, tail)
	return dsn, safeDSN
}
