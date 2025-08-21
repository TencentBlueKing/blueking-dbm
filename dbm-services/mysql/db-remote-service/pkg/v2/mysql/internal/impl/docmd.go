package impl

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/jmoiron/sqlx"
)

func DoSQL(conn *sqlx.Conn, sql string, timeout int) ([]byte, int64, error) {
	sql = strings.TrimSpace(sql)
	var cmdWorker func(*sqlx.Conn, string, int) (SQLResultRows, int64, error)
	if IsQueryCommand(sql) {
		cmdWorker = doQuery
	} else {
		cmdWorker = doExecute
	}

	crs := make(SQLResultRows, 0)
	var n int64
	var err error
	err = retry.Do(
		func() error {
			crs, n, err = cmdWorker(conn, sql, timeout)
			return err
		},
		retryOpts...,
	)

	b, _ := json.Marshal(crs)

	var rErrs retry.Error
	errors.As(err, &rErrs)

	return b, n, errors.Join(rErrs...)
}

func doQuery(conn *sqlx.Conn, sql string, timeout int) (SQLResultRows, int64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	rows, err := conn.QueryxContext(ctx, sql)
	if err != nil {
		return nil, 0, err
	}
	defer func() {
		_ = rows.Close()
	}()

	srs := make(SQLResultRows, 0)
	for rows.Next() {
		data := make(map[string]interface{})
		if err := rows.MapScan(data); err != nil {
			return nil, 0, err
		}
		for k, v := range data {
			if value, ok := v.([]byte); ok {
				data[k] = string(value)
			}
		}
		srs = append(srs, data)
	}
	if err := rows.Err(); err != nil {
		return nil, 0, err
	}
	return srs, 0, nil
}

func doExecute(conn *sqlx.Conn, sql string, timeout int) (SQLResultRows, int64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()
	result, err := conn.ExecContext(ctx, sql)
	if err != nil {
		return nil, 0, err
	}
	n, err := result.RowsAffected()
	return nil, n, err
}
