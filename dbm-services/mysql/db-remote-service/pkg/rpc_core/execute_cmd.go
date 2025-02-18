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
func executeCmd(logger *slog.Logger, conn *sqlx.Conn, cmd string, timeout time.Duration) (int64, error) {
	for i := 0; i < 5; i++ {
		n, err := executeAtom(conn, cmd, timeout)
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

func executeAtom(conn *sqlx.Conn, cmd string, timeout time.Duration) (int64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	result, err := conn.ExecContext(ctx, cmd)
	if err != nil {
		return 0, err
	}

	return result.RowsAffected()
}

func queryCmd(logger *slog.Logger, conn *sqlx.Conn, cmd string, timeout time.Duration) (tableDataType, error) {
	for i := 0; i < 5; i++ {
		dataType, err := queryAtom(conn, cmd, timeout)
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

func queryAtom(conn *sqlx.Conn, cmd string, timeout time.Duration) (tableDataType, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	rows, err := conn.QueryxContext(ctx, cmd)
	if err != nil {
		return nil, err
	}

	defer func() {
		_ = rows.Close()
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
