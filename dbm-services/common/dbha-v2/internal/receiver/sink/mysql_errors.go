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
	"strings"

	mysqldriver "github.com/go-sql-driver/mysql"
)

// mysqlErrKind classifies MySQL write errors for batch retry / fallback.
type mysqlErrKind int

const (
	mysqlErrTransient mysqlErrKind = iota
	mysqlErrDeadlock
	mysqlErrData
	mysqlErrFatal
)

var dataErrorNumbers = map[uint16]struct{}{
	1406: {}, // Data too long
	1366: {}, // Incorrect string value
	1264: {}, // Out of range
	1265: {}, // Data truncated
	1292: {}, // Incorrect datetime
	1048: {}, // Column cannot be null
	3140: {}, // Invalid JSON
}

var deadlockErrorNumbers = map[uint16]struct{}{
	1213: {}, // Deadlock
	1205: {}, // Lock wait timeout
}

// classifyMySQLError classifies err assuming the caller ctx is still valid.
// Caller must check ctx.Err() first and treat a finished ctx as fatal.
func classifyMySQLError(err error) mysqlErrKind {
	if err == nil {
		return mysqlErrTransient
	}
	if errors.Is(err, context.Canceled) {
		return mysqlErrFatal
	}
	if errors.Is(err, sql.ErrConnDone) {
		return mysqlErrFatal
	}
	if isDatabaseClosed(err) {
		return mysqlErrFatal
	}

	var myErr *mysqldriver.MySQLError
	if errors.As(err, &myErr) {
		if _, ok := deadlockErrorNumbers[myErr.Number]; ok {
			return mysqlErrDeadlock
		}
		if _, ok := dataErrorNumbers[myErr.Number]; ok {
			return mysqlErrData
		}
	}
	return mysqlErrTransient
}

func isDatabaseClosed(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), "database is closed")
}
