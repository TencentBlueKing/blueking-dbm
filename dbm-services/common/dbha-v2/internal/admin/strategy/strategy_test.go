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

package strategy

import (
	"errors"
	"fmt"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/ginx"
	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/go-sql-driver/mysql"
)

func duplicate(key string) error {
	return fmt.Errorf("insert strategy: %w", &mysql.MySQLError{
		Number: duplicateEntryCode, Message: "Duplicate entry '0-x-0' for key '" + key + "'",
	})
}

func TestWriteErrorMapsUniqueKeys(t *testing.T) {
	const table = "t_db_switching_strategy."
	cases := []struct {
		name string
		err  error
		want error
	}{
		{name: "event mysql8", err: duplicate(table + "idx_biz_event_reason"), want: ginx.ErrStrategyEventExists},
		{name: "event mysql57", err: duplicate("idx_biz_event_reason"), want: ginx.ErrStrategyEventExists},
		{name: "name mysql8", err: duplicate(table + "idx_name"), want: ginx.ErrStrategyNameExists},
		{name: "name mysql57", err: duplicate("idx_name"), want: ginx.ErrStrategyNameExists},
	}
	for _, item := range cases {
		got := writeError(item.err)
		if !errors.Is(got, item.want) {
			t.Fatalf("unique key not mapped, case: %s, got: %s", item.name, got)
		}
		if strings.Contains(got.Error(), "Duplicate entry") {
			t.Fatalf("raw mysql message leaked, case: %s", item.name)
		}
	}
}

func TestWriteErrorKeepsOtherFailures(t *testing.T) {
	others := []error{
		duplicate("PRIMARY"),
		duplicate("idx_name_other"),
		&mysql.MySQLError{Number: 1205, Message: "Lock wait timeout exceeded"},
		errors.New("connection refused"),
	}
	for _, err := range others {
		got := writeError(err)
		if errors.Is(got, ginx.ErrStrategyEventExists) || errors.Is(got, ginx.ErrStrategyNameExists) {
			t.Fatalf("unexpected business error, errmsg: %s", err)
		}
		var wrapped *gerrors.Error
		if !errors.As(got, &wrapped) || !wrapped.HasCode(gerrors.MysqlFailure) {
			t.Fatalf("other failure must stay a mysql failure, errmsg: %s", err)
		}
	}
}
