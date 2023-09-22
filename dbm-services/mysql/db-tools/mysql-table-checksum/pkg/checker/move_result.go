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

	err = r.validateHistoryTable()
	if err != nil {
		slog.Error("move result validate history table again", slog.String("error", err.Error()))
		return err
	}
	slog.Info("move result validate history table again success")

	slog.Info("move result", slog.Time("ts", r.startTS))

	conn, err := r.db.Conn(context.Background())
	if err != nil {
		slog.Error("get connect", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
	if err != nil {
		slog.Error("set binlog_format = 'statement'", slog.String("error", err.Error()))
		return err
	}
	_, err = conn.ExecContext(
		context.Background(),
		fmt.Sprintf(
			`INSERT INTO %s (%[2]s) SELECT %[2]s FROM %s WHERE ts >= ?`,
			r.resultHistoryTable,
			strings.Join(columns, ","),
			r.resultTbl,
		), r.startTS,
	)
	if err != nil {
		slog.Error("move result", slog.String("error", err.Error()))
		return err
	}

	return nil
}
