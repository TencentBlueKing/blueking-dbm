package checker

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"fmt"
	"log/slog"
	"strings"
)

func (r *Checker) moveResult(ticketId int64) error {
	// 在 master 上以这样的方式转存当次的校验结果可以让 slave 转存真实结果
	rows, err := r.db.Queryx(
		`SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?`,
		config.ResultDb, config.ResultTable,
	)
	if err != nil {
		slog.Error(
			"fetch result table columns",
			slog.String("error", err.Error()),
			slog.String("result table", config.ResultTable),
			slog.String("result db", config.ResultDb),
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
	_, err = r.conn.ExecContext(
		context.Background(),
		fmt.Sprintf(
			`REPLACE INTO %s.%s (%s) SELECT %s FROM %s.%s WHERE ts >= ? AND ticket_id = ? AND master_ip = ? AND master_port = ?`,
			config.ResultDb,
			config.ResultHistoryTable,
			columnsStr,
			columnsStr,
			config.ResultDb,
			config.ResultTable,
		),
		r.startTS, ticketId, config.ChecksumConfig.Ip, config.ChecksumConfig.Port,
	)
	if err != nil {
		slog.Error("move result", slog.String("error", err.Error()))
		return err
	}

	return nil
}
