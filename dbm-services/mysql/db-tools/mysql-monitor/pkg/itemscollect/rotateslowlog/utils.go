package rotateslowlog

import (
	"log/slog"

	"github.com/jmoiron/sqlx"
)

func slowLogStatus(db *sqlx.DB) (slowLogOn bool, slowLogPath string, err error) {
	err = db.QueryRowx(
		`SELECT @@slow_query_log, @@slow_query_log_file`,
	).Scan(&slowLogOn, &slowLogPath)

	if err != nil {
		slog.Error("query slow_query_log, slow_query_log_file", slog.String("error", err.Error()))
		return false, "", err
	}

	slog.Info(
		"rotate slow log",
		slog.Bool("slow_query_log", slowLogOn),
		slog.String("slow_query_log_file", slowLogPath),
	)

	return slowLogOn, slowLogPath, nil
}
