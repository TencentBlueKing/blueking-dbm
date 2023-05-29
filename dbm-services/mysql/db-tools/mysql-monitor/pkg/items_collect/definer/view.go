package definer

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

func views(db *sqlx.DB) (msg []string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	q, args, err := sqlx.In(
		`SELECT TABLE_NAME, TABLE_SCHEMA, DEFINER 
					FROM information_schema.VIEWS 
					WHERE TABLE_SCHEMA NOT IN (?)`,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return nil, errors.Wrap(err, "build In query view")
	}

	var res []struct {
		ViewName   string `db:"TABLE_NAME"`
		ViewSchema string `db:"TABLE_SCHEMA"`
		Definer    string `db:"DEFINER"`
	}
	err = db.SelectContext(ctx, &res, db.Rebind(q), args...)
	if err != nil {
		return nil, errors.Wrap(err, "query views")
	}
	slog.Debug("query views", slog.Any("views", res))

	for _, ele := range res {
		owner := fmt.Sprintf(
			"view %s.%s",
			ele.ViewSchema, ele.ViewName,
		)
		if r := checkDefiner(owner, ele.Definer); r != "" {
			msg = append(msg, r)
		}
	}
	return msg, nil
}
