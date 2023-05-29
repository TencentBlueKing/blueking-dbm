package definer

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

func snapshot(db *sqlx.DB) error {
	if !snapped {
		ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
		defer cancel()

		err := db.SelectContext(ctx, &mysqlUsers, `SELECT user FROM mysql.user`)
		if err != nil {
			slog.Error("query users", err)
			return err
		}
		slog.Debug("query users", slog.Any("users", mysqlUsers))
		snapped = true
	}
	return nil
}
