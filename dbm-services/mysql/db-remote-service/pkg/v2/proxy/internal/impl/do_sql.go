package impl

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/jmoiron/sqlx"
)

const (
	maxQueryRows        = 100000
	maxQueryBytes int64 = 64 << 20 // 64 MB
)

// SQLResultRow 一行查询结果
type SQLResultRow map[string]interface{}

// SQLResultRows 全部行
type SQLResultRows []SQLResultRow

// DoSQL 在已有 conn 上执行单条命令。
// 按 IsQueryCommand / IsExecuteCommand 分流，不认识的命令返回 error。
func DoSQL(conn *sqlx.Conn, sql string, timeout int) ([]byte, int64, error) {
	sql = strings.TrimSpace(sql)

	if !IsSupportedCommand(sql) {
		return nil, 0, fmt.Errorf("unsupported command: %s", sql)
	}

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

	if err == nil {
		return b, n, nil
	}

	var rErrs retry.Error
	if errors.As(err, &rErrs) {
		return b, n, errors.Join(rErrs...)
	}
	return b, n, err
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
	var totalBytes int64
	for rows.Next() {
		if len(srs) >= maxQueryRows {
			return nil, 0, fmt.Errorf("result set exceeds row limit (%d rows); narrow your query with WHERE/LIMIT", maxQueryRows)
		}
		data := make(map[string]interface{})
		if err := rows.MapScan(data); err != nil {
			return nil, 0, err
		}
		for k, v := range data {
			totalBytes += int64(len(k))
			if value, ok := v.([]byte); ok {
				data[k] = string(value)
				totalBytes += int64(len(value))
			}
		}
		if totalBytes > maxQueryBytes {
			return nil, 0, fmt.Errorf("result set exceeds byte limit (%d bytes); narrow your query with WHERE/LIMIT", maxQueryBytes)
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
