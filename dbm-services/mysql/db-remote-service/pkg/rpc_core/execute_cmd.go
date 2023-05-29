package rpc_core

import (
	"context"

	"github.com/jmoiron/sqlx"
)

// executeCmd TODO
// func executeCmd(db *sqlx.DB, cmd string, timeout int) (int64, error) {
func executeCmd(conn *sqlx.Conn, cmd string, ctx context.Context) (int64, error) {
	// ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
	// defer cancel()

	result, err := conn.ExecContext(ctx, cmd)
	if err != nil {
		return 0, err
	}

	return result.RowsAffected()
}

// queryCmd TODO
// func queryCmd(db *sqlx.DB, cmd string, timeout int) (tableDataType, error) {
func queryCmd(conn *sqlx.Conn, cmd string, ctx context.Context) (tableDataType, error) {
	// ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
	// defer cancel()

	rows, err := conn.QueryxContext(ctx, cmd)
	if err != nil {
		return nil, err
	}

	defer func() {
		_ = rows.Close()
	}()

	tableData := make(tableDataType, 0)

	for rows.Next() {
		data := make(map[string]interface{})
		err := rows.MapScan(data)
		if err != nil {
			return nil, err
		}
		for k, v := range data {
			if value, ok := v.([]byte); ok {
				data[k] = string(value)
			}
		}
		tableData = append(tableData, data)

	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return tableData, nil
}
