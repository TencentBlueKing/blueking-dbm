package safesql

import (
	"context"
	"database/sql"
)

// StdPool 标准库连接池抽象。
// *sql.DB 直接满足; *sqlx.DB 因为内嵌 *sql.DB 也满足, 所以不用 sqlx 的调用方
// 可以只依赖这一组 Std* 入口。
type StdPool interface {
	Conn(ctx context.Context) (*sql.Conn, error)
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
}

func stdAcquire(
	ctx context.Context, pool StdPool, query string, o *options,
) (*session, *sql.Conn, error) {
	conn, err := pool.Conn(ctx)
	if err != nil {
		return nil, nil, err
	}

	s, err := newSession(ctx, pool, conn, query, o)
	if err != nil {
		return nil, nil, err
	}
	return s, conn, nil
}

// StdWithConn 最通用入口: 在一条独占连接上执行 fn, ctx 取消时顺带 KILL 服务端语句。
// fn 内部必须使用传入的 conn 和 ctx; 不要把 conn 泄漏到 fn 之外。
func StdWithConn(
	ctx context.Context, pool StdPool, name string,
	fn func(ctx context.Context, conn *sql.Conn) error,
	opts ...Option,
) error {
	s, conn, err := stdAcquire(ctx, pool, name, buildOptions(opts))
	if err != nil {
		return err
	}
	defer s.release()

	return fn(ctx, conn)
}

// StdExecContext 等价于 db.ExecContext, 额外保证 ctx 取消时服务端语句被 KILL
func StdExecContext(
	ctx context.Context, pool StdPool, query string, args ...interface{},
) (sql.Result, error) {
	return StdExecContextWithOptions(ctx, pool, nil, query, args...)
}

// StdExecContextWithOptions 带可选配置的 StdExecContext
func StdExecContextWithOptions(
	ctx context.Context, pool StdPool, opts []Option, query string, args ...interface{},
) (sql.Result, error) {
	var res sql.Result
	err := StdWithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sql.Conn) error {
			var e error
			res, e = conn.ExecContext(ctx, query, args...)
			return e
		},
		opts...,
	)
	return res, err
}

// StdScanRowContext 等价于 db.QueryRowContext(...).Scan(dest...), 额外保证 ctx 取消时 KILL。
// 无结果时返回 sql.ErrNoRows。
func StdScanRowContext(
	ctx context.Context, pool StdPool, query string, args []interface{}, dest ...interface{},
) error {
	return StdScanRowContextWithOptions(ctx, pool, nil, query, args, dest...)
}

// StdScanRowContextWithOptions 带可选配置的 StdScanRowContext
func StdScanRowContextWithOptions(
	ctx context.Context, pool StdPool, opts []Option,
	query string, args []interface{}, dest ...interface{},
) error {
	return StdWithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sql.Conn) error {
			return conn.QueryRowContext(ctx, query, args...).Scan(dest...)
		},
		opts...,
	)
}

// StdMapScanRowContext 取第一行并以 map 返回 ([]byte 已转成 string),
// 适合 SHOW SLAVE STATUS / SHOW GLOBAL STATUS 这类列不固定的语句。
// 无结果时返回空 map 且 err 为 nil。
func StdMapScanRowContext(
	ctx context.Context, pool StdPool, query string, args ...interface{},
) (map[string]interface{}, error) {
	return StdMapScanRowContextWithOptions(ctx, pool, nil, query, args...)
}

// StdMapScanRowContextWithOptions 带可选配置的 StdMapScanRowContext
func StdMapScanRowContextWithOptions(
	ctx context.Context, pool StdPool, opts []Option, query string, args ...interface{},
) (map[string]interface{}, error) {
	var res map[string]interface{}
	err := StdWithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sql.Conn) error {
			rows, err := conn.QueryContext(ctx, query, args...)
			if err != nil {
				return err
			}
			defer func() {
				_ = rows.Close()
			}()

			res, err = mapScanRow(rows)
			return err
		},
		opts...,
	)
	if err != nil {
		return nil, err
	}
	return res, nil
}

// StdRows 包装 *sql.Rows, Close 时顺带归还独占连接并停止 watcher。
// 调用方必须保证 Close 被调用 (通常 defer rows.Close())。
type StdRows struct {
	*sql.Rows
	release func()
}

// Close 关闭结果集并释放独占连接
func (r *StdRows) Close() error {
	err := r.Rows.Close()
	r.release()
	return err
}

// StdQueryContext 等价于 db.QueryContext, 额外保证 ctx 取消时 KILL。
// 返回的 StdRows 必须 Close, 否则独占连接不会归还。
func StdQueryContext(
	ctx context.Context, pool StdPool, query string, args ...interface{},
) (*StdRows, error) {
	return StdQueryContextWithOptions(ctx, pool, nil, query, args...)
}

// StdQueryContextWithOptions 带可选配置的 StdQueryContext
func StdQueryContextWithOptions(
	ctx context.Context, pool StdPool, opts []Option, query string, args ...interface{},
) (*StdRows, error) {
	s, conn, err := stdAcquire(ctx, pool, query, buildOptions(opts))
	if err != nil {
		return nil, err
	}

	rows, err := conn.QueryContext(ctx, query, args...)
	if err != nil {
		s.release()
		return nil, err
	}

	return &StdRows{Rows: rows, release: s.release}, nil
}
