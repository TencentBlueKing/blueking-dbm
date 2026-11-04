/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package harvest

import (
	"database/sql"
	"fmt"
	"strings"
	"testing"
)

func TestProcesslistSQLLimits(t *testing.T) {
	infoExpr := fmt.Sprintf("LEFT(INFO, %d)", processlistInfoMaxLen)
	limitExpr := fmt.Sprintf("LIMIT %d", processlistMaxFetchRows)
	if !strings.Contains(processlistSQL, infoExpr) {
		t.Fatalf("processlistSQL should truncate INFO with %s, got %s", infoExpr, processlistSQL)
	}
	if !strings.Contains(processlistSQL, limitExpr) {
		t.Fatalf("processlistSQL should limit the result set with %s, got %s", limitExpr, processlistSQL)
	}
}

func TestTruncateProcesslistInfo(t *testing.T) {
	short := "SELECT 1"
	if got := truncateProcesslistInfo(short); got != short {
		t.Fatalf("truncateProcesslistInfo(%q) = %q, want unchanged", short, got)
	}

	long := strings.Repeat("a", processlistInfoMaxLen+8)
	got := truncateProcesslistInfo(long)
	if !strings.HasSuffix(got, "...") {
		t.Fatalf("truncated info should end with ..., got len=%d", len(got))
	}
	if len(got) != processlistInfoMaxLen+3 {
		t.Fatalf("truncated info len = %d, want %d", len(got), processlistInfoMaxLen+3)
	}
}

func TestIsSuspiciousProcesslistRow(t *testing.T) {
	tests := []struct {
		name string
		row  processlistRow
		want bool
	}{
		{
			name: "flush tables",
			row: processlistRow{
				Command: "Query",
				Time:    2,
				Info:    sql.NullString{String: "FLUSH TABLES WITH READ LOCK", Valid: true},
			},
			want: true,
		},
		{
			name: "flush table singular",
			row: processlistRow{
				Command: "Query",
				Time:    2,
				Info:    sql.NullString{String: "FLUSH TABLE t WITH READ LOCK", Valid: true},
			},
			want: true,
		},
		{
			name: "lock tables",
			row: processlistRow{
				Command: "Query",
				Time:    2,
				Info:    sql.NullString{String: "LOCK TABLES t WRITE", Valid: true},
			},
			want: true,
		},
		{
			name: "lock table singular",
			row: processlistRow{
				Command: "Query",
				Time:    2,
				Info:    sql.NullString{String: "LOCK TABLE t WRITE", Valid: true},
			},
			want: true,
		},
		{
			name: "unlock tables",
			row: processlistRow{
				Command: "Query",
				Time:    2,
				Info:    sql.NullString{String: "UNLOCK TABLES", Valid: true},
			},
			want: true,
		},
		{
			name: "waiting for global read lock",
			row: processlistRow{
				Command: "Query",
				Time:    3,
				State:   sql.NullString{String: "Waiting for global read lock", Valid: true},
			},
			want: true,
		},
		{
			name: "long query",
			row:  processlistRow{Command: "Query", Time: 11},
			want: true,
		},
		{
			name: "idle sleep is not suspicious",
			row:  processlistRow{Command: "Sleep", Time: 100},
			want: false,
		},
		{
			name: "binlog dump is not suspicious",
			row: processlistRow{
				Command: "Binlog Dump GTID",
				Time:    5102754,
				State:   sql.NullString{String: "Master has sent all binlog to slave; waiting for more updates", Valid: true},
			},
			want: false,
		},
		{
			name: "short query",
			row:  processlistRow{Command: "Query", Time: 0, Info: sql.NullString{String: "SELECT 1", Valid: true}},
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isSuspiciousProcesslistRow(tt.row)
			if got != tt.want {
				t.Fatalf("isSuspiciousProcesslistRow() = %v, want %v, row=%+v", got, tt.want, tt.row)
			}
		})
	}
}
