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
	// maxQueryRows 单个 SELECT 返回的最大行数; 防止 SELECT * FROM big_table 把 drs 撑爆
	maxQueryRows = 100000
	// maxQueryBytes 单个 SELECT 累计字节数兜底 (按 cell 字节估算, 不含 map 开销)
	maxQueryBytes int64 = 64 << 20 // 64 MB
)

// DoSQL 在已有 conn 上执行单条 SQL.
// 自动按 IsQueryCommand 分流到 doQuery / doExecute, 并按 retryOpts 做有限重试.
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

	if err == nil {
		return b, n, nil
	}

	// retry.Do 在所有 attempts 都失败后返回 retry.Error (聚合每次的 error);
	// 对非可重试的错误 (RetryIf 返回 false), retry-go 直接返回原始 error, 不会包成 retry.Error
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
