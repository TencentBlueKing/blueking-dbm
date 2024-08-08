package pkg

import (
	"context"
	"slices"
	"time"

	"github.com/jmoiron/sqlx"
)

type showOpenTablesRow struct {
	Database   string `db:"Database"`
	Table      string `db:"Table"`
	InUse      int    `db:"In_use"`
	NameLocked int    `db:"Name_locked"`
}

func IsDBsInUsing(conn *sqlx.Conn, dbs []string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := conn.ExecContext(
		ctx,
		`FLUSH TABLES`,
	)
	if err != nil {
		return nil, err
	}

	for i := 0; i < 6; i++ {
		reOpenDBs, err := queryReOpenDBs(conn, dbs)
		if err != nil {
			return nil, err
		}

		if len(reOpenDBs) > 0 {
			return reOpenDBs, nil
		}
		time.Sleep(10 * time.Second)
	}

	return nil, nil
}

func queryReOpenDBs(conn *sqlx.Conn, dbs []string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var resOpenTables []showOpenTablesRow
	err := conn.SelectContext(
		ctx,
		&resOpenTables,
		`SHOW OPEN TABLES`,
	)
	if err != nil {
		return nil, err
	}

	var res []string
	for _, dbName := range dbs {
		if slices.IndexFunc(resOpenTables, func(sr showOpenTablesRow) bool {
			return dbName == sr.Database
		}) >= 0 {
			res = append(res, dbName)
		}
	}
	return res, nil
}
