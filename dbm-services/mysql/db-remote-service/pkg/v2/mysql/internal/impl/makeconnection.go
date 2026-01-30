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

func Prepare(addr, user, password, timezone, charset string, timeout int) (*sqlx.DB, *sqlx.Conn, int64, error) {
	db, err := makeConnection(
		addr, user, password,
		timezone, charset, timeout,
	)
	if err != nil {
		return nil, nil, 0, err
	}

	conn, err := db.Connx(context.Background())
	if err != nil {
		_ = db.Close()
		return nil, nil, 0, err
	}

	var connId int64
	err = conn.GetContext(context.Background(), &connId, `SELECT CONNECTION_ID()`)
	if err != nil {
		_ = conn.Close()
		_ = db.Close()
		return nil, nil, 0, err
	}

	return db, conn, connId, nil
}

// makeConnection 创建数据库连接，处理 default 字符集的特殊逻辑
func makeConnection(addr, user, password, timezone, charset string, timeout int) (*sqlx.DB, error) {
	// 如果不是 default 字符集，直接连接
	if charset != "default" {
		return connectWithRetry(addr, user, password, timezone, charset, timeout)
	}

	// 处理 default 字符集：先建立临时连接获取服务器字符集
	tempDB, err := connectWithRetry(addr, user, password, timezone, "", timeout)
	if err != nil {
		return nil, err
	}

	// 查询服务器字符集
	var serverCharset string
	err = tempDB.QueryRow(`SELECT @@character_set_server`).Scan(&serverCharset)
	// 无论成功与否，都关闭临时连接
	_ = tempDB.Close()

	if err != nil {
		return nil, fmt.Errorf("query server charset failed: %w", err)
	}

	// 使用实际字符集重新连接
	return connectWithRetry(addr, user, password, timezone, serverCharset, timeout)
}

// connectWithRetry 带重试的数据库连接（纯粹的连接逻辑，不处理 default 字符集）
func connectWithRetry(addr, user, password, timezone, charset string, timeout int) (db *sqlx.DB, err error) {
	dsn := fmt.Sprintf(`%s:%s@tcp(%s)/?timeout=%ds`, user, password, addr, timeout)
	if timezone != "" {
		dsn = dsn + fmt.Sprintf("&time_zone=%s", url.QueryEscape(fmt.Sprintf(`'%s'`, timezone)))
	}
	if charset != "" {
		dsn = dsn + fmt.Sprintf("&charset=%s", charset)
	}

	err = retry.Do(
		func() error {
			db, err = sqlx.Connect("mysql", dsn)
			return err
		},
		retry.Attempts(3),
		retry.Delay(2*time.Second),
		retry.DelayType(retry.FixedDelay),
	)
	if err != nil {
		slog.Error("failed to connect to mysql server", slog.String("error", err.Error()), slog.String("dsn", dsn))
		return nil, err
	}

	return db, nil
}
