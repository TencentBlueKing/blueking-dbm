package impl

import (
	"context"
	"database/sql/driver"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
)

const (
	maxQueryRows        = 100000
	maxQueryBytes int64 = 64 << 20 // 64 MB

	// float64 能精确表示的整数范围内, 整数值的 NUMBER 以 int64 返回
	maxExactFloatInt = 1 << 53
)

// SQLResultRow 一行查询结果, key 为 Oracle 返回的列名 (通常为大写)
type SQLResultRow map[string]interface{}

// DoQuery 在已有 conn 上执行一条只读查询, 返回 JSON 编码的 []SQLResultRow.
//
// 类型转换规则 (保证 JSON 可序列化且语义稳定):
//   - NUMBER / FLOAT / BINARY_*: 整数值转 int64, 其余转 float64; NaN/Inf 转字符串
//   - DATE / TIMESTAMP: "YYYY-MM-DD HH24:MI:SS[.FF6]", 带时区类型追加 " +HH:MM"
//   - RAW / BLOB: 大写 hex 字符串
//   - 其余字符类型 (VARCHAR2 / CHAR / CLOB / LONG ...): 字符串
func DoQuery(conn *sqlx.Conn, cmd string, timeout int) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	rows, err := conn.QueryContext(ctx, cmd)
	if err != nil {
		return nil, wrapTimeout(ctx, err, timeout)
	}
	defer func() {
		_ = rows.Close()
	}()

	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	colTypes, err := rows.ColumnTypes()
	if err != nil {
		return nil, err
	}
	typeNames := make([]string, len(cols))
	for i, ct := range colTypes {
		if i < len(typeNames) {
			typeNames[i] = strings.ToUpper(ct.DatabaseTypeName())
		}
	}

	result := make([]SQLResultRow, 0)
	var totalBytes int64
	for rows.Next() {
		if len(result) >= maxQueryRows {
			return nil, fmt.Errorf("result set exceeds row limit (%d rows); narrow your query with WHERE/ROWNUM", maxQueryRows)
		}

		values := make([]interface{}, len(cols))
		ptrs := make([]interface{}, len(cols))
		for i := range values {
			ptrs[i] = &values[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}

		row := make(SQLResultRow, len(cols))
		for i, col := range cols {
			v, size := normalizeValue(values[i], typeNames[i])
			row[col] = v
			totalBytes += int64(len(col)) + size
		}
		if totalBytes > maxQueryBytes {
			return nil, fmt.Errorf("result set exceeds byte limit (%d bytes); narrow your query with WHERE/ROWNUM", maxQueryBytes)
		}
		result = append(result, row)
	}
	if err := rows.Err(); err != nil {
		return nil, wrapTimeout(ctx, err, timeout)
	}

	return json.Marshal(result)
}

func wrapTimeout(ctx context.Context, err error, timeout int) error {
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return fmt.Errorf("query timeout after %ds: %w", timeout, err)
	}
	return err
}

// normalizeValue 把驱动返回的值转换为 JSON 友好的值, 同时返回估算的字节数 (用于结果集大小限制)
func normalizeValue(v interface{}, typeName string) (interface{}, int64) {
	if valuer, ok := v.(driver.Valuer); ok {
		inner, err := valuer.Value()
		if err != nil {
			s := fmt.Sprintf("%v", v)
			return s, int64(len(s))
		}
		v = inner
	}

	switch x := v.(type) {
	case nil:
		return nil, 4
	case string:
		if isNumericType(typeName) {
			if n, ok := parseNumber(x); ok {
				return n, int64(len(x))
			}
		}
		return x, int64(len(x))
	case []byte:
		if isBinaryType(typeName) {
			s := strings.ToUpper(hex.EncodeToString(x))
			return s, int64(len(s))
		}
		return string(x), int64(len(x))
	case time.Time:
		s := formatTime(x, typeName)
		return s, int64(len(s))
	case float64:
		return normalizeFloat(x), 8
	case float32:
		return normalizeFloat(float64(x)), 8
	case int64, int32, int16, int8, int, uint64, uint32, uint16, uint8, uint, bool:
		return x, 8
	default:
		s := fmt.Sprintf("%v", x)
		return s, int64(len(s))
	}
}

func isNumericType(typeName string) bool {
	for _, kw := range []string{"NUMBER", "FLOAT", "DOUBLE", "INTEGER", "DECIMAL"} {
		if strings.Contains(typeName, kw) {
			return true
		}
	}
	return false
}

func isBinaryType(typeName string) bool {
	return strings.Contains(typeName, "RAW") || strings.Contains(typeName, "BLOB")
}

func isTimeZoneType(typeName string) bool {
	return strings.Contains(typeName, "TZ") || strings.Contains(typeName, "TIME ZONE")
}

func parseNumber(s string) (interface{}, bool) {
	s = strings.TrimSpace(s)
	if i, err := strconv.ParseInt(s, 10, 64); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return normalizeFloat(f), true
	}
	return nil, false
}

func normalizeFloat(f float64) interface{} {
	if math.IsNaN(f) || math.IsInf(f, 0) {
		return strconv.FormatFloat(f, 'g', -1, 64)
	}
	if f == math.Trunc(f) && math.Abs(f) < maxExactFloatInt {
		return int64(f)
	}
	return f
}

func formatTime(t time.Time, typeName string) string {
	layout := "2006-01-02 15:04:05"
	if t.Nanosecond() != 0 {
		layout += ".000000"
	}
	if isTimeZoneType(typeName) {
		layout += " -07:00"
	}
	return t.Format(layout)
}
