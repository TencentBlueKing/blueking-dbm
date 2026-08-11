package saveproxyconnlog

import (
	"context"
	"fmt"
	"log/slog"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
)

const createTableSQL = `CREATE TABLE IF NOT EXISTS infodba_schema.proxy_conn_log (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	proxy_ip VARCHAR(32) NOT NULL,
	conn_time DATETIME NOT NULL,
	username VARCHAR(64) NOT NULL,
	client_host VARCHAR(64) NOT NULL,
	thread_id BIGINT NOT NULL,
	KEY idx_proxy_ip (proxy_ip,username),
	KEY idx_user_host (username, client_host),
	KEY idx_conn_time (conn_time),
	KEY idx_thread (thread_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='dml show disable sql_log_bin'`

// initConn 初始化连接：关闭 binlog
func initConn(ctx context.Context, conn *sqlx.Conn) error {
	_, err := conn.ExecContext(ctx, `SET sql_log_bin = 0`)
	if err != nil {
		slog.Error("set sql_log_bin=0 failed", slog.String("error", err.Error()))
		return err
	}
	return nil
}

// createTable 建表，仅在表不存在时调用
func createTable(ctx context.Context, conn *sqlx.Conn) error {
	_, err := conn.ExecContext(ctx, createTableSQL)
	if err != nil {
		slog.Error("create proxy_conn_log table failed", slog.String("error", err.Error()))
		return err
	}
	slog.Info("proxy_conn_log table created")
	return nil
}

// isTableNotExistErr 判断是否为表不存在错误 (MySQL error 1146)
func isTableNotExistErr(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), "1146") || strings.Contains(err.Error(), "doesn't exist")
}

// batchInsert 批量写入连接日志到后端 MySQL
// 如果写入时发现表不存在，则自动建表后重试一次
func batchInsert(ctx context.Context, conn *sqlx.Conn, entries []*ConnLogEntry, proxyIP string) error {
	if len(entries) == 0 {
		return nil
	}

	// 构建多值 INSERT 语句
	valuePlaceholders := make([]string, 0, len(entries))
	args := make([]interface{}, 0, len(entries)*5)

	for _, entry := range entries {
		valuePlaceholders = append(valuePlaceholders, "(?, ?, ?, ?, ?)")
		args = append(args, proxyIP, entry.ConnTime, entry.Username, entry.ClientHost, entry.ThreadID)
	}

	insertSQL := fmt.Sprintf(
		`INSERT INTO infodba_schema.proxy_conn_log (proxy_ip, conn_time, username, client_host, thread_id) VALUES %s`,
		strings.Join(valuePlaceholders, ","),
	)

	_, err := conn.ExecContext(ctx, insertSQL, args...)
	if err != nil {
		// 表不存在时自动建表并重试
		if isTableNotExistErr(err) {
			slog.Info("table not exist, creating table and retry")
			if createErr := createTable(ctx, conn); createErr != nil {
				return createErr
			}
			_, err = conn.ExecContext(ctx, insertSQL, args...)
			if err != nil {
				slog.Error("batch insert after create table still failed",
					slog.String("error", err.Error()),
					slog.Int("batch_size", len(entries)),
				)
				return err
			}
		} else {
			slog.Error(
				"batch insert proxy conn log failed",
				slog.String("error", err.Error()),
				slog.Int("batch_size", len(entries)),
			)
			return err
		}
	}

	// slog.Info("batch insert proxy conn log", slog.Int("count", len(entries)))
	return nil
}

// cleanOldData 清理过期的连接日志数据（7天前），分批删除
func cleanOldData(ctx context.Context, conn *sqlx.Conn, proxyIP string) error {
	for {
		result, err := conn.ExecContext(
			ctx,
			`DELETE FROM infodba_schema.proxy_conn_log 
			 WHERE proxy_ip = ? AND conn_time < DATE_SUB(NOW(), INTERVAL 7 DAY) 
			 LIMIT 10000`,
			proxyIP,
		)
		if err != nil {
			slog.Error("clean old proxy conn log failed", slog.String("error", err.Error()))
			return err
		}

		affected, err := result.RowsAffected()
		if err != nil {
			return err
		}

		if affected == 0 {
			break
		}

		slog.Info(
			"clean old proxy conn log",
			slog.Int64("deleted", affected),
			slog.String("proxy_ip", config.MonitorConfig.Ip),
		)
	}

	return nil
}
