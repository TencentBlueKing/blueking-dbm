package mysql_connlog

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"fmt"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

// mysqlConnLogRotate TODO
/*
1. binlog 是 session 变量, 所以只需要禁用就行了
2. 首先禁用了 init_connect, 后续表 rotate 失败会 return, 不会恢复 init_connect. 所以不会影响连接
*/
func mysqlConnLogRotate(db *sqlx.DB) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	conn, err := db.Connx(ctx)
	if err != nil {
		slog.Error("connlog rotate get conn from db", err)
		return "", err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(ctx, `SET SQL_LOG_BIN=0`)
	if err != nil {
		slog.Error("disable binlog", err)
		return "", err
	}
	slog.Info("rotate conn log disable binlog success")

	var initConn string
	err = conn.QueryRowxContext(ctx, "SELECT @@INIT_CONNECT").Scan(&initConn)
	if err != nil {
		slog.Error("query init connect", err)
		return "", err
	}
	slog.Info("rotate conn log", slog.String("init connect", initConn))

	_, err = conn.ExecContext(ctx, `SET @OLD_INIT_CONNECT=@@INIT_CONNECT`)
	if err != nil {
		slog.Error("save init_connect", err)
		return "", err
	}

	var oldInitConn string
	err = conn.QueryRowxContext(ctx, "SELECT @OLD_INIT_CONNECT").Scan(&oldInitConn)
	if err != nil {
		slog.Error("query old init connect", err)
		return "", err
	}
	slog.Info("rotate conn log", slog.String("old init connect", oldInitConn))

	if initConn != oldInitConn {
		err = errors.Errorf("save init_connect failed")
		slog.Error("check save init connect", err)
		return "", err
	}

	_, err = conn.ExecContext(ctx, `SET GLOBAL INIT_CONNECT = ''`)
	if err != nil {
		slog.Error("disable init_connect", err)
		return "", err
	}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			`DROP TABLE IF EXISTS %s.conn_log_old`, cst.DBASchema,
		),
	)
	if err != nil {
		slog.Error("drop conn_log_old", err)
		return "", err
	}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			`RENAME TABLE %[1]s.conn_log to %[1]s.conn_log_old`,
			cst.DBASchema,
		),
	)
	if err != nil {
		slog.Error("rename conn_log", err)
		return "", err
	}
	slog.Info("rotate conn log", "rename conn_log success")

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			`CREATE TABLE IF NOT EXISTS %[1]s.conn_log like %[1]s.conn_log_old`,
			cst.DBASchema,
		),
	)
	if err != nil {
		slog.Error("recreate conn_log", err)
		return "", err
	}
	slog.Info("rotate conn log", "recreate conn_log success")

	_, err = conn.ExecContext(ctx, `SET GLOBAL INIT_CONNECT = @OLD_INIT_CONNECT`)
	if err != nil {
		slog.Error("restore init_connect", err)
		return "", err
	}
	initConn = ""
	err = conn.QueryRowxContext(ctx, "SELECT @@INIT_CONNECT").Scan(&initConn)
	if err != nil {
		slog.Error("query init connect", err)
		return "", err
	}
	slog.Info("rotate conn log", slog.String("init connect", initConn))
	if initConn != oldInitConn {
		err = errors.Errorf("restore init_connect failed")
		slog.Error("check restore init_connect", err)
		return "", err
	}

	return "", nil
}
