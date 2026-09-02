package checker

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
)

func (r *Checker) moveResult() error {
	// 在 master 上以这样的方式转存当次的校验结果可以让 slave 转存真实结果
	rows, err := r.db.Queryx(
		`SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?`,
		r.resultDB,
		r.resultTbl,
	)
	if err != nil {
		slog.Error(
			"fetch result table columns",
			slog.String("error", err.Error()),
			slog.String("result table", r.resultTbl),
			slog.String("result db", r.resultDB),
		)
		return err
	}
	var columns []string
	for rows.Next() {
		var col string
		err := rows.Scan(&col)
		if err != nil {
			slog.Error("iterator columns", slog.String("error", err.Error()))
			return err
		}

		columns = append(columns, col)
	}

	slog.Info("move result", slog.Time("from", r.startTS))

	columnsStr := strings.Join(columns, ",")
	// 为了兼容 flashback, 这里拼上库前缀
	// 这里拿个新的conn, 因为有可能过了很久, 原来的 r.conn 已经失效了
	conn, err := r.db.Connx(context.Background())
	if err != nil {
		slog.Info("fetch connection", slog.String("error", err.Error()))
		return err
	}
	_, err = conn.ExecContext(
		context.Background(), `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;`,
	)
	if err != nil {
		slog.Error("set transaction isolation level", slog.String("error", err.Error()))
		return err
	}
	_, err = conn.ExecContext(context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
	if err != nil {
		slog.Error(
			"set binlog format to statement", slog.String("error", err.Error()),
		)
		return err
	}

	_, err = conn.ExecContext(
		context.Background(),
		fmt.Sprintf(
			`REPLACE INTO %s.%s (%s) SELECT %s FROM %s.%s WHERE ts >= ? AND master_ip = ? AND master_port = ?`,
			r.resultDB,
			r.resultHistoryTable,
			columnsStr,
			columnsStr,
			r.resultDB,
			r.resultTbl,
		), r.startTS, r.Config.Ip, r.Config.Port,
	)
	if err != nil {
		slog.Error("move result", slog.String("error", err.Error()))
		return err
	}

	return nil
}
