// Package safesql 提供带「服务端取消」能力的 SQL 执行封装。
//
// 背景:
// go-sql-driver/mysql 在 context 超时/取消时, 只会关闭本地 TCP 连接并把连接标记为
// bad conn, 并不会通知 MySQL 终止正在执行的语句。服务端线程会一直挂着, 直到阻塞根因
// 解除后才在写回包时发现对端已断开。对于 SHOW SLAVE STATUS 这类可能被内部锁卡住的
// 语句, 每轮采集超时都会在服务端堆积一个僵死线程。
//
// 本包在执行语句前先独占一条连接并记录其 CONNECTION_ID, 当 ctx 被取消时, 另开一条
// 连接发送 KILL QUERY <id> (可选 KILL <id>), 让服务端也尽快放弃这次执行。
// 这与 mysql 命令行客户端 Ctrl+C 的做法 (client/mysql.cc 的 kill_query) 一致。
//
// 本文件是与具体 SQL 库无关的核心逻辑:
//   - sqlx.go 提供基于 *sqlx.DB / *sqlx.Conn 的入口 (函数名无前缀)
//   - std.go  提供基于 *sql.DB / *sql.Conn 的入口 (函数名带 Std 前缀)
//
// 注意:
//  1. KILL 只是设置 thread 的 kill flag, 线程需要运行到可中断点才会退出。若语句卡在
//     内部 mutex (如 SHOW SLAVE STATUS 等 channel_map/data_lock), KILL 同样可能无效,
//     但至少不会让连接继续被复用, 且根因解除时会立刻退出。
//  2. 仅适用于真实的 MySQL 实例。proxy admin 端口不支持 CONNECTION_ID()/KILL,
//     此时会自动降级为普通执行 (与原行为一致)。
//  3. KILL 使用的是同一个连接池里的新连接, 账号与业务语句相同; 同用户的线程无需
//     PROCESS/SUPER 权限即可 KILL。
package safesql

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"sync/atomic"
	"time"

	"github.com/go-sql-driver/mysql"
)

const logName = "safesql"

// erNoSuchThread MySQL 1094, KILL 时线程已不存在, 属于预期情况
const erNoSuchThread = 1094

// defaultKillTimeout KILL 语句自身的超时
const defaultKillTimeout = 3 * time.Second

// Conn 独占连接的通用能力。
// *sql.Conn 与 *sqlx.Conn (内嵌了 *sql.Conn) 都直接满足该接口,
// 所以会话初始化回调可以同时用于两条路径。
type Conn interface {
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error)
	QueryRowContext(ctx context.Context, query string, args ...interface{}) *sql.Row
}

// connCloser 可归还的独占连接
type connCloser interface {
	Conn
	Close() error
}

// killer 用于发送 KILL 的连接池。
// 这里只要求 ExecContext, *sql.DB / *sqlx.DB 都满足。
type killer interface {
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
}

type options struct {
	killTimeout    time.Duration
	killConnection bool
	onTimeout      func(threadID int64, query string, killErr error)
	sessionInit    []func(ctx context.Context, conn Conn) error
}

// Option 可选配置
type Option func(*options)

// WithKillTimeout 设置 KILL 语句自身的超时, 默认 3s
func WithKillTimeout(d time.Duration) Option {
	return func(o *options) {
		if d > 0 {
			o.killTimeout = d
		}
	}
}

// WithKillConnection 超时时使用 KILL <id> (断开整条连接) 而不是 KILL QUERY <id>。
// 语句本身可能跨多条 (如 SET + REPLACE) 或处于事务中时, 用它更干净。
func WithKillConnection() Option {
	return func(o *options) {
		o.killConnection = true
	}
}

// WithOnTimeout 注册超时回调, 可用于自定义上报。killErr 为 KILL 语句的执行结果。
func WithOnTimeout(fn func(threadID int64, query string, killErr error)) Option {
	return func(o *options) {
		o.onTimeout = fn
	}
}

// WithSessionVars 在独占连接上执行 SET SESSION, 用于设置会话变量。
// 形如 WithSessionVars("time_zone", "'+08:00'", "sql_log_bin", "0"),
// 参数必须成对出现, 且 value 原样拼进 SQL (需要引号请自己带上)。
//
// 这些 SET 在取到 connection id 并启动 watcher 之后执行, 因此同样受 ctx 超时保护。
func WithSessionVars(kv ...string) Option {
	return func(o *options) {
		if len(kv)%2 != 0 {
			slog.Error(
				logName+" WithSessionVars needs even number of args, ignored",
				slog.Int("count", len(kv)),
			)
			return
		}
		for i := 0; i < len(kv); i += 2 {
			o.sessionInit = append(
				o.sessionInit,
				execSessionSQL(fmt.Sprintf("SET SESSION %s = %s", kv[i], kv[i+1])),
			)
		}
	}
}

// WithSessionSQL 在独占连接上按顺序执行任意语句, 用于 SET SESSION TRANSACTION
// ISOLATION LEVEL / SET NAMES 这类不能写成 SET SESSION x = y 的场景。
func WithSessionSQL(stmts ...string) Option {
	return func(o *options) {
		for _, stmt := range stmts {
			o.sessionInit = append(o.sessionInit, execSessionSQL(stmt))
		}
	}
}

// WithSessionInit 注册自定义初始化回调, 可在里面做任意事情 (带参数的 SET、
// 读回变量校验等)。多次注册按顺序执行, 任一返回 error 则整次调用失败。
//
// 回调拿到的是 Conn 接口; 需要 sqlx 专有方法时自行断言成 *sqlx.Conn。
func WithSessionInit(fn func(ctx context.Context, conn Conn) error) Option {
	return func(o *options) {
		if fn != nil {
			o.sessionInit = append(o.sessionInit, fn)
		}
	}
}

func execSessionSQL(stmt string) func(ctx context.Context, conn Conn) error {
	return func(ctx context.Context, conn Conn) error {
		if _, err := conn.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("session init %s: %w", stmt, err)
		}
		return nil
	}
}

func buildOptions(opts []Option) *options {
	o := &options{killTimeout: defaultKillTimeout}
	for _, fn := range opts {
		fn(o)
	}
	return o
}

// session 持有一条独占连接, 并在 ctx 取消时负责 KILL
type session struct {
	conn     connCloser
	threadID int64
	finished atomic.Bool
	done     chan struct{}
}

// newSession 接管一条已取得的独占连接。
// 返回 error 时连接已被归还, 调用方无需再处理。
func newSession(
	ctx context.Context, k killer, conn connCloser, query string, o *options,
) (*session, error) {
	s := &session{conn: conn, done: make(chan struct{})}

	// 取不到 connection id 时降级为普通执行, 不影响原有逻辑
	if err := conn.QueryRowContext(ctx, `SELECT CONNECTION_ID()`).Scan(&s.threadID); err != nil {
		slog.Warn(
			logName+" get connection id failed, fallback to plain exec",
			slog.String("error", err.Error()),
		)
		s.threadID = 0
	}

	if s.threadID > 0 {
		go s.watch(ctx, k, query, o)
	}

	// 会话初始化放在 watcher 启动之后, 这样连 SET 本身卡住也能被 KILL
	for _, fn := range o.sessionInit {
		if err := fn(ctx, conn); err != nil {
			s.release()
			return nil, err
		}
	}

	return s, nil
}

func (s *session) watch(ctx context.Context, k killer, query string, o *options) {
	select {
	case <-s.done:
		return
	case <-ctx.Done():
		if s.finished.Load() {
			return
		}
		killErr := kill(k, s.threadID, o)
		slog.Warn(
			logName+" context done, cancel server side query",
			slog.Int64("thread id", s.threadID),
			slog.String("query", query),
			slog.String("ctx error", ctx.Err().Error()),
			slog.Any("kill error", killErr),
		)
		if o.onTimeout != nil {
			o.onTimeout(s.threadID, query, killErr)
		}
	}
}

// release 停止 watcher 并归还连接。ctx 已超时的连接会被 database/sql 直接丢弃。
func (s *session) release() {
	if !s.finished.CompareAndSwap(false, true) {
		return
	}
	// 让 watcher 退出; 若 watcher 已在执行 KILL, 这里不等待它
	close(s.done)
	_ = s.conn.Close()
}

func kill(k killer, threadID int64, o *options) error {
	stmt := fmt.Sprintf("KILL QUERY %d", threadID)
	if o.killConnection {
		stmt = fmt.Sprintf("KILL %d", threadID)
	}

	// 必须用全新的 ctx, 原 ctx 已经取消
	ctx, cancel := context.WithTimeout(context.Background(), o.killTimeout)
	defer cancel()

	if _, err := k.ExecContext(ctx, stmt); err != nil {
		var merr *mysql.MySQLError
		if errors.As(err, &merr) && merr.Number == erNoSuchThread {
			return nil
		}
		return err
	}
	return nil
}

// mapScanRow 把 *sql.Rows 的第一行读成 map, []byte 统一转成 string。
// 无结果时返回空 map。
func mapScanRow(rows *sql.Rows) (map[string]interface{}, error) {
	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	res := make(map[string]interface{}, len(cols))
	if rows.Next() {
		vals := make([]interface{}, len(cols))
		ptrs := make([]interface{}, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		for i, c := range cols {
			res[c] = vals[i]
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	normalizeBytes(res)
	return res, nil
}

func normalizeBytes(m map[string]interface{}) {
	for k, v := range m {
		if b, ok := v.([]byte); ok {
			m[k] = string(b)
		}
	}
}
