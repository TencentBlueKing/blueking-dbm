package rpc_core

import (
	"context"
	"errors"
	"log/slog"
	"slices"
	"time"

	"github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
)

var retryErrNum []uint16

func init() {
	retryErrNum = []uint16{
		1130,
		1045,
		//1064,
	}
}

// executeCmd TODO
// func executeCmd(db *sqlx.DB, cmd string, timeout int) (int64, error) {
func executeCmd(logger *slog.Logger, db *sqlx.DB, conn *sqlx.Conn, connId int64, cmd string, timeout time.Duration) (int64, error) {
	for i := 0; i < 5; i++ {
		n, err := executeAtom(logger, db, conn, connId, cmd, timeout)
		if err == nil {
			logger.Info("execute cmd success", slog.String("cmd", cmd))
			return n, nil
		}

		logger.Error("execute cmd failed", slog.String("cmd", cmd), slog.String("error", err.Error()))

		var me *mysql.MySQLError
		ok := errors.As(err, &me)

		if !ok {
			return n, err
		}

		// 不在重试错误中
		if slices.Index(retryErrNum, me.Number) < 0 {
			return n, err
		}
		logger.Error("retry execute cmd", slog.String("cmd", cmd))
		time.Sleep(2 * time.Second)
	}
	return -1, errors.New("timeout")
}

func executeAtom(logger *slog.Logger, db *sqlx.DB, conn *sqlx.Conn, connId int64, cmd string, timeout time.Duration) (int64, error) {
	logger.Info("execute cmd", slog.String("cmd", cmd), slog.String("timeout", timeout.String()))
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	result, err := conn.ExecContext(ctx, cmd)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) && connId > 0 {
			logger.Error("execute cmd timeout, try to kill conn", slog.String("cmd", cmd), slog.Int64("connId", connId))
			_, _ = db.Exec(`KILL ?`, connId)
		}
		return 0, err
	}

	return result.RowsAffected()
}

func queryCmd(logger *slog.Logger, db *sqlx.DB, conn *sqlx.Conn, connId int64, cmd string, timeout time.Duration) (tableDataType, error) {
	for i := 0; i < 5; i++ {
		dataType, err := queryAtom(logger, db, conn, connId, cmd, timeout)
		if err == nil {
			logger.Info("query cmd success", slog.String("cmd", cmd))
			return dataType, nil
		}

		logger.Error("query cmd failed", slog.String("cmd", cmd), slog.String("error", err.Error()))

		var me *mysql.MySQLError
		ok := errors.As(err, &me)

		if !ok {
			return dataType, err
		}

		// 不在重试错误中
		if slices.Index(retryErrNum, me.Number) < 0 {
			return dataType, err
		}
		logger.Error("retry query cmd", slog.String("cmd", cmd))
		time.Sleep(2 * time.Second)
	}
	return nil, errors.New("timeout")
}

func queryAtom(logger *slog.Logger, db *sqlx.DB, conn *sqlx.Conn, connId int64, cmd string, timeout time.Duration) (tableDataType, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	rows, err := conn.QueryxContext(ctx, cmd)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) && connId > 0 {
			logger.Info("query cmd timeout, try to kill conn", slog.String("cmd", cmd), slog.Int64("connId", connId))
			_, _ = db.Exec(`KILL ?`, connId)
		}
		return nil, err
	}

	defer func() {
		err := rows.Close()
		if err != nil {
			slog.Error(
				"close rows failed",
				slog.String("cmd", cmd),
				slog.String("error", err.Error()))
		} else {
			slog.Info("close rows success", slog.String("cmd", cmd))
		}
	}()

	tableData := make(tableDataType, 0)

	for rows.Next() {
		data := make(map[string]interface{})
		err := rows.MapScan(data)
		if err != nil {
			return nil, err
		}

		//slog.Debug("scan row map", slog.Any("map", data))
		for k, v := range data {
			if value, ok := v.([]byte); ok {
				//slog.Debug(
				//	"reflect result",
				//	slog.Any("before", v),
				//	slog.Any("after", value),
				//)
				data[k] = string(value)
			}
		}
		tableData = append(tableData, data)

	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return tableData, nil
}
