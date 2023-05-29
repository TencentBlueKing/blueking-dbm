package checker

import (
	"context"
	"fmt"
	"strings"

	"golang.org/x/exp/slog"
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
			err,
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
			slog.Error("iterator columns", err)
			return err
		}

		columns = append(columns, col)
	}

	err = r.validateHistoryTable()
	if err != nil {
		slog.Error("move result validate history table again", err)
		return err
	}
	slog.Info("move result validate history table again success")

	slog.Info("move result", slog.Time("ts", r.startTS))

	conn, err := r.db.Conn(context.Background())
	if err != nil {
		slog.Error("get connect", err)
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
	if err != nil {
		slog.Error("set binlog_format = 'statement'", err)
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
		slog.Error("move result", err)
		return err
	}

	return nil
}
