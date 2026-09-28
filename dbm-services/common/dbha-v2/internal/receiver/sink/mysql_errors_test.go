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

package sink

import (
	"context"
	"database/sql"
	"errors"
	"testing"

	mysqldriver "github.com/go-sql-driver/mysql"
)

func TestClassifyMySQLError(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		err  error
		want mysqlErrKind
	}{
		{name: "deadlock 1213", err: &mysqldriver.MySQLError{Number: 1213}, want: mysqlErrDeadlock},
		{name: "lock wait 1205", err: &mysqldriver.MySQLError{Number: 1205}, want: mysqlErrDeadlock},
		{name: "data too long 1406", err: &mysqldriver.MySQLError{Number: 1406}, want: mysqlErrData},
		{name: "illegal value 1366", err: &mysqldriver.MySQLError{Number: 1366}, want: mysqlErrData},
		{name: "out of range 1264", err: &mysqldriver.MySQLError{Number: 1264}, want: mysqlErrData},
		{name: "truncated 1265", err: &mysqldriver.MySQLError{Number: 1265}, want: mysqlErrData},
		{name: "bad datetime 1292", err: &mysqldriver.MySQLError{Number: 1292}, want: mysqlErrData},
		{name: "null 1048", err: &mysqldriver.MySQLError{Number: 1048}, want: mysqlErrData},
		{name: "bad json 3140", err: &mysqldriver.MySQLError{Number: 3140}, want: mysqlErrData},
		{name: "readonly 1290", err: &mysqldriver.MySQLError{Number: 1290}, want: mysqlErrTransient},
		{name: "readonly 1836", err: &mysqldriver.MySQLError{Number: 1836}, want: mysqlErrTransient},
		{name: "ctx canceled", err: context.Canceled, want: mysqlErrFatal},
		{name: "conn done", err: sql.ErrConnDone, want: mysqlErrFatal},
		{name: "db closed", err: errors.New("sql: database is closed"), want: mysqlErrFatal},
		{name: "deadline", err: context.DeadlineExceeded, want: mysqlErrTransient},
		{name: "other mysql", err: &mysqldriver.MySQLError{Number: 1040}, want: mysqlErrTransient},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := classifyMySQLError(tc.err)
			if got != tc.want {
				t.Fatalf("classifyMySQLError() = %v, want %v", got, tc.want)
			}
		})
	}
}
