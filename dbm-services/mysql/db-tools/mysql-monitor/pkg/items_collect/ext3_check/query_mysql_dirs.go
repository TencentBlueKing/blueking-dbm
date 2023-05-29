package ext3_check

import (
	"context"
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"path/filepath"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

func mysqlDirs(db *sqlx.DB, variables []string) (dirs []string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var datadir string

	for _, v := range variables {
		var dir sql.NullString
		err = db.GetContext(ctx, &dir, fmt.Sprintf(`SELECT @@%s`, v))
		if err != nil && err != sql.ErrNoRows {
			return nil, errors.Wrap(err, fmt.Sprintf(`SELECT @@%s`, v))
		}

		// mysql其他的目录可能是以 datadir 为 base, 所以要单独存一下
		if dir.Valid {
			dirs = append(dirs, dir.String)
			if v == "datadir" {
				datadir = dir.String
			}
		}
	}

	var binlogBase sql.NullString
	err = db.GetContext(ctx, &binlogBase, `SELECT @@log_bin_basename`)
	if err != nil && err != sql.ErrNoRows {
		return nil, errors.Wrap(err, `SELECT @@log_bin_basename`)
	}

	if binlogBase.Valid {
		dirs = append(dirs, filepath.Dir(binlogBase.String))
	}

	var relaylogBase sql.NullString
	err = db.GetContext(ctx, &relaylogBase, `SELECT @@relay_log_basename`)
	if err != nil && err != sql.ErrNoRows {
		return nil, errors.Wrap(err, `SELECT @@relay_log_basename`)
	}

	if relaylogBase.Valid {
		// fmt.Printf("relay-log: %s\n", filepath.Dir(relaylogBase.String))
		dirs = append(dirs, filepath.Dir(relaylogBase.String))
	}

	for i, dir := range dirs {
		if !filepath.IsAbs(dir) {
			dirs[i] = filepath.Join(datadir, dir)
		}
	}

	return dirs, nil
}
