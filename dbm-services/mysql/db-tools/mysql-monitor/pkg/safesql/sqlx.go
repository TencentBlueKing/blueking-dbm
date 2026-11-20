package safesql

import (
	"context"
	"database/sql"

	"github.com/jmoiron/sqlx"
)

// Pool sqlx 连接池抽象。
// *sqlx.DB 以及任何嵌入了 *sqlx.DB 的类型 (如 *pkg.MySQLMonitorDBH) 都直接满足该接口。
type Pool interface {
	Connx(ctx context.Context) (*sqlx.Conn, error)
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
}

func acquire(
	ctx context.Context, pool Pool, query string, o *options,
) (*session, *sqlx.Conn, error) {
	conn, err := pool.Connx(ctx)
	if err != nil {
		return nil, nil, err
	}

	s, err := newSession(ctx, pool, conn, query, o)
	if err != nil {
		return nil, nil, err
	}
	return s, conn, nil
}

// WithConn 最通用入口: 在一条独占连接上执行 fn, ctx 取消时顺带 KILL 服务端语句。
// fn 内部必须使用传入的 conn 和 ctx; 不要把 conn 泄漏到 fn 之外。
func WithConn(
	ctx context.Context, pool Pool, name string,
	fn func(ctx context.Context, conn *sqlx.Conn) error,
	opts ...Option,
) error {
	s, conn, err := acquire(ctx, pool, name, buildOptions(opts))
	if err != nil {
		return err
	}
	defer s.release()

	return fn(ctx, conn)
}

// ExecContext 等价于 db.ExecContext, 额外保证 ctx 取消时服务端语句被 KILL
func ExecContext(
	ctx context.Context, pool Pool, query string, args ...interface{},
) (sql.Result, error) {
	return ExecContextWithOptions(ctx, pool, nil, query, args...)
}

// ExecContextWithOptions 带可选配置的 ExecContext
func ExecContextWithOptions(
	ctx context.Context, pool Pool, opts []Option, query string, args ...interface{},
) (sql.Result, error) {
	var res sql.Result
	err := WithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sqlx.Conn) error {
			var e error
			res, e = conn.ExecContext(ctx, query, args...)
			return e
		},
		opts...,
	)
	return res, err
}

// GetContext 等价于 db.GetContext (取一行到 dest), 额外保证 ctx 取消时 KILL
func GetContext(
	ctx context.Context, pool Pool, dest interface{}, query string, args ...interface{},
) error {
	return GetContextWithOptions(ctx, pool, nil, dest, query, args...)
}

// GetContextWithOptions 带可选配置的 GetContext
func GetContextWithOptions(
	ctx context.Context, pool Pool, opts []Option,
	dest interface{}, query string, args ...interface{},
) error {
	return WithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sqlx.Conn) error {
			return conn.GetContext(ctx, dest, query, args...)
		},
		opts...,
	)
}

// SelectContext 等价于 db.SelectContext (取多行到 dest slice), 额外保证 ctx 取消时 KILL
func SelectContext(
	ctx context.Context, pool Pool, dest interface{}, query string, args ...interface{},
) error {
	return SelectContextWithOptions(ctx, pool, nil, dest, query, args...)
}

// SelectContextWithOptions 带可选配置的 SelectContext
func SelectContextWithOptions(
	ctx context.Context, pool Pool, opts []Option,
	dest interface{}, query string, args ...interface{},
) error {
	return WithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sqlx.Conn) error {
			return conn.SelectContext(ctx, dest, query, args...)
		},
		opts...,
	)
}

// ScanRowContext 等价于 db.QueryRowx(...).Scan(dest...), 额外保证 ctx 取消时 KILL。
// 无结果时返回 sql.ErrNoRows。
func ScanRowContext(
	ctx context.Context, pool Pool, query string, args []interface{}, dest ...interface{},
) error {
	return ScanRowContextWithOptions(ctx, pool, nil, query, args, dest...)
}

// ScanRowContextWithOptions 带可选配置的 ScanRowContext
func ScanRowContextWithOptions(
	ctx context.Context, pool Pool, opts []Option,
	query string, args []interface{}, dest ...interface{},
) error {
	return WithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sqlx.Conn) error {
			return conn.QueryRowxContext(ctx, query, args...).Scan(dest...)
		},
		opts...,
	)
}

// MapScanRowContext 取第一行并以 map 返回 ([]byte 已转成 string),
// 适合 SHOW SLAVE STATUS / SHOW GLOBAL STATUS 这类列不固定的语句。
// 无结果时返回空 map 且 err 为 nil。
func MapScanRowContext(
	ctx context.Context, pool Pool, query string, args ...interface{},
) (map[string]interface{}, error) {
	return MapScanRowContextWithOptions(ctx, pool, nil, query, args...)
}

// MapScanRowContextWithOptions 带可选配置的 MapScanRowContext
func MapScanRowContextWithOptions(
	ctx context.Context, pool Pool, opts []Option, query string, args ...interface{},
) (map[string]interface{}, error) {
	res := make(map[string]interface{})
	err := WithConn(
		ctx, pool, query,
		func(ctx context.Context, conn *sqlx.Conn) error {
			rows, err := conn.QueryxContext(ctx, query, args...)
			if err != nil {
				return err
			}
			defer func() {
				_ = rows.Close()
			}()

			if rows.Next() {
				if err := rows.MapScan(res); err != nil {
					return err
				}
			}
			return rows.Err()
		},
		opts...,
	)
	if err != nil {
		return nil, err
	}

	normalizeBytes(res)
	return res, nil
}

// Rows 包装 *sqlx.Rows, Close 时顺带归还独占连接并停止 watcher。
// 调用方必须保证 Close 被调用 (通常 defer rows.Close())。
type Rows struct {
	*sqlx.Rows
	release func()
}

// Close 关闭结果集并释放独占连接
func (r *Rows) Close() error {
	err := r.Rows.Close()
	r.release()
	return err
}

// QueryxContext 等价于 db.QueryxContext, 额外保证 ctx 取消时 KILL。
// 返回的 Rows 必须 Close, 否则独占连接不会归还。
func QueryxContext(
	ctx context.Context, pool Pool, query string, args ...interface{},
) (*Rows, error) {
	return QueryxContextWithOptions(ctx, pool, nil, query, args...)
}

// QueryxContextWithOptions 带可选配置的 QueryxContext
func QueryxContextWithOptions(
	ctx context.Context, pool Pool, opts []Option, query string, args ...interface{},
) (*Rows, error) {
	s, conn, err := acquire(ctx, pool, query, buildOptions(opts))
	if err != nil {
		return nil, err
	}

	rows, err := conn.QueryxContext(ctx, query, args...)
	if err != nil {
		s.release()
		return nil, err
	}

	return &Rows{Rows: rows, release: s.release}, nil
}
