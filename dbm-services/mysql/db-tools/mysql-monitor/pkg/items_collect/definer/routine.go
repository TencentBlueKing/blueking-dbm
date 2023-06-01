package definer

import (
	"context"
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

func routines(db *sqlx.DB) (msg []string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	q, args, err := sqlx.In(
		`SELECT ROUTINE_TYPE, ROUTINE_NAME, ROUTINE_SCHEMA, DEFINER 
					FROM information_schema.ROUTINES 
					WHERE ROUTINE_SCHEMA NOT IN (?)`,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return nil, errors.Wrap(err, "build In query routine")
	}

	var res []struct {
		RoutineType   string `db:"ROUTINE_TYPE"`
		RoutineName   string `db:"ROUTINE_NAME"`
		RoutineSchema string `db:"ROUTINE_SCHEMA"`
		Definer       string `db:"DEFINER"`
	}
	err = db.SelectContext(ctx, &res, db.Rebind(q), args...)
	if err != nil {
		return nil, errors.Wrap(err, "query routines")
	}
	slog.Debug("query routines", slog.Any("routines", res))

	for _, ele := range res {
		owner := fmt.Sprintf(
			"%s %s.%s",
			ele.RoutineType, ele.RoutineSchema, ele.RoutineName,
		)
		if r := checkDefiner(owner, ele.Definer); r != "" {
			msg = append(msg, r)
		}
	}
	return msg, nil
}
