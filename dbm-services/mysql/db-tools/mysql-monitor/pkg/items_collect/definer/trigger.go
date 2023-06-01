package definer

import (
	"context"
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

func triggers(db *sqlx.DB) (msg []string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	q, args, err := sqlx.In(
		`SELECT TRIGGER_NAME, TRIGGER_SCHEMA, DEFINER   
					FROM information_schema.TRIGGERS  
					WHERE TRIGGER_SCHEMA NOT IN (?)`,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return nil, errors.Wrap(err, "build In query trigger")
	}

	var res []struct {
		TriggerName   string `db:"TRIGGER_NAME"`
		TriggerSchema string `db:"TRIGGER_SCHEMA"`
		Definer       string `db:"DEFINER"`
	}
	err = db.SelectContext(ctx, &res, db.Rebind(q), args...)
	if err != nil {
		return nil, errors.Wrap(err, "query triggers")
	}
	slog.Debug("query triggers", slog.Any("triggers", res))

	for _, ele := range res {
		owner := fmt.Sprintf(
			"trigger %s.%s",
			ele.TriggerSchema, ele.TriggerName,
		)
		if r := checkDefiner(owner, ele.Definer); r != "" {
			msg = append(msg, r)
		}
	}
	return msg, nil
}
