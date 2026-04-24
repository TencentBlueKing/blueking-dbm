package impl

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

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
// 按 classifier 分流到 doQuery / doExecute，不认识的命令返回 error。
func DoSQL(conn *sqlx.Conn, cmd string, timeout int, classifier *CommandClassifier) ([]byte, int64, error) {
	cmd = strings.TrimSpace(cmd)

	if !classifier.IsSupportedCommand(cmd) {
		return nil, 0, fmt.Errorf("unsupported command: %s", cmd)
	}

	if classifier.IsQueryCommand(cmd) {
		return doQuery(conn, cmd, timeout)
	}
	return doExecute(conn, cmd, timeout)
}

func doQuery(conn *sqlx.Conn, cmd string, timeout int) ([]byte, int64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	rows, err := conn.QueryxContext(ctx, cmd)
	if err != nil {
		// v1 的 rpc_core/execute_cmd.go:60 在超时时会 KILL connId, 但 SQLServer 的 connId
		// 永远为 0 (execute_cmds_on_addr.go:72 的 CONNECTION_ID 只对 MySQL 执行),
		// 所以 v1 SQLServer 超时后不会 KILL 后端 session. v2 保持一致, 不做 KILL.
		//
		// 如果将来需要超时 KILL, 在 Prepare 里获取 @@SPID 后传入此处:
		//   if errors.Is(err, context.DeadlineExceeded) && spid > 0 && db != nil {
		//       _, _ = db.Exec(fmt.Sprintf("KILL %d", spid))
		//   }
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

	b, _ := json.Marshal(srs)
	return b, 0, nil
}

func doExecute(conn *sqlx.Conn, cmd string, timeout int) ([]byte, int64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	result, err := conn.ExecContext(ctx, cmd)
	if err != nil {
		// 同 doQuery 的注释, v1 SQLServer 超时后不会 KILL, v2 保持一致.
		return nil, 0, err
	}

	n, err := result.RowsAffected()
	return nil, n, err
}
