package mysql_connlog

import (
	"context"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

func mysqlConnLogSize(db *sqlx.DB) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var dataDir string
	err := db.QueryRowxContext(ctx, `SELECT @@datadir`).Scan(&dataDir)
	if err != nil {
		slog.Error("select @@datadir", err)
		return "", err
	}

	var logSize int64

	slog.Debug("statistic conn log", slog.String("path", filepath.Join(dataDir, cst.DBASchema)))
	err = filepath.WalkDir(
		filepath.Join(dataDir, cst.DBASchema),
		func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				slog.Error("statistic conn log size", err, slog.String("path", path))
				return filepath.SkipDir
			}

			slog.Debug("statistic conn log size", slog.String("path", path))
			if strings.HasPrefix(filepath.Base(path), "conn_log") {
				st, sterr := os.Stat(path)
				if sterr != nil {
					return filepath.SkipDir
				}
				if !st.IsDir() {
					slog.Debug(
						"statistic conn log size",
						slog.Any("status", st),
					)
					logSize += st.Size()
				}
			}
			return nil
		},
	)
	if err != nil {
		slog.Error("statistic conn log size", err)
		return "", err
	}
	slog.Info("statistic conn log size", slog.Int64("size", logSize))

	if logSize >= sizeLimit {
		_, err = db.ExecContext(ctx, `SET GLOBAL INIT_CONNECT = ''`)
		if err != nil {
			slog.Error("disable init_connect", err, slog.Int64("size", logSize))
			return "", err
		}
		return fmt.Sprintf("too big connlog table size %d", logSize), nil
	}
	return "", nil
}
