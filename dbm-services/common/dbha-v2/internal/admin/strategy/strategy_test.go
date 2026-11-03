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
	"context"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/ginx"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"github.com/go-sql-driver/mysql"
	gormmysql "gorm.io/driver/mysql"
	"gorm.io/gorm"
)

type capturedQuery struct {
	sql  string
	vars []any
}

type queryRecorder struct {
	queries []capturedQuery
}

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

func TestQueryStrategiesByNamesUsesPlaceholders(t *testing.T) {
	s, _, rec := newDryRunStrategy(t)

	if _, err := s.QueryStrategiesByNames(context.Background(), 7, []string{"a", "b"}); err != nil {
		t.Fatalf("query strategies failed, errmsg: %s", err)
	}

	got := rec.last(t)
	if !strings.Contains(got.sql, "WHERE bk_biz_id = ? AND name IN (?,?)") {
		t.Fatalf("unexpected sql, sql: %s", got.sql)
	}
	if want := []any{7, "a", "b"}; !reflect.DeepEqual(got.vars, want) {
		t.Fatalf("unexpected vars, got: %v, want: %v", got.vars, want)
	}
}

func TestQueryStrategiesByNamesBindsInjectionPayloads(t *testing.T) {
	s, _, rec := newDryRunStrategy(t)
	payloads := []string{"x' OR '1'='1", "x'; DROP TABLE t; --"}

	if _, err := s.QueryStrategiesByNames(context.Background(), 7, payloads); err != nil {
		t.Fatalf("query strategies failed, errmsg: %s", err)
	}

	got := rec.last(t)
	for _, payload := range payloads {
		if strings.Contains(got.sql, payload) {
			t.Fatalf("payload leaked into sql text, sql: %s", got.sql)
		}
	}
	if want := []any{7, payloads[0], payloads[1]}; !reflect.DeepEqual(got.vars, want) {
		t.Fatalf("payloads must be bound vars, got: %v, want: %v", got.vars, want)
	}
}

func TestQueryStrategiesByNamesEmptyNames(t *testing.T) {
	s, _, rec := newDryRunStrategy(t)

	if _, err := s.QueryStrategiesByNames(context.Background(), 7, nil); err != nil {
		t.Fatalf("query strategies failed, errmsg: %s", err)
	}

	got := rec.last(t)
	if !strings.Contains(got.sql, "name IN (NULL)") {
		t.Fatalf("empty names must match nothing, sql: %s", got.sql)
	}
	if want := []any{7}; !reflect.DeepEqual(got.vars, want) {
		t.Fatalf("unexpected vars, got: %v, want: %v", got.vars, want)
	}
}

func TestQueryStrategiesByNamesMatchesMapForm(t *testing.T) {
	cases := [][]string{nil, {"a"}, {"a", "b", "c"}}
	for _, names := range cases {
		s, gdb, rec := newDryRunStrategy(t)

		if _, err := s.QueryStrategiesByNames(context.Background(), 7, names); err != nil {
			t.Fatalf("query strategies failed, errmsg: %s", err)
		}
		typed := rec.last(t)

		var out []*hamodel.DbSwitchingStrategy
		legacy := map[string]any{"bk_biz_id": 7, "name": names}
		if err := gdb.Model(&hamodel.DbSwitchingStrategy{}).Where(legacy).Find(&out).Error; err != nil {
			t.Fatalf("legacy query failed, errmsg: %s", err)
		}
		mapped := rec.last(t)

		if !reflect.DeepEqual(typed.vars, mapped.vars) {
			t.Fatalf("vars differ from map form, names: %v, got: %v, want: %v", names, typed.vars, mapped.vars)
		}
	}
}

// newDryRunStrategy builds a Strategy over a DryRun MySQL dialector that never connects,
// and records every generated query.
func newDryRunStrategy(t *testing.T) (*Strategy, *gorm.DB, *queryRecorder) {
	t.Helper()

	dialector := gormmysql.New(gormmysql.Config{
		DSN:                       "u:p@tcp(127.0.0.1:3306)/db",
		SkipInitializeWithVersion: true,
	})
	gdb, err := gorm.Open(dialector, &gorm.Config{DryRun: true, DisableAutomaticPing: true})
	if err != nil {
		t.Fatalf("open dry run db failed, errmsg: %s", err)
	}

	rec := &queryRecorder{}
	err = gdb.Callback().Query().After("gorm:query").Register("test:capture", func(tx *gorm.DB) {
		rec.queries = append(rec.queries, capturedQuery{
			sql:  strings.Join(strings.Fields(tx.Statement.SQL.String()), " "),
			vars: append([]any(nil), tx.Statement.Vars...),
		})
	})
	if err != nil {
		t.Fatalf("register capture callback failed, errmsg: %s", err)
	}

	return &Strategy{DB: hamysql.WithGormDB(gdb, nil)}, gdb, rec
}

func (r *queryRecorder) last(t *testing.T) capturedQuery {
	t.Helper()

	if len(r.queries) == 0 {
		t.Fatal("no query captured")
	}
	return r.queries[len(r.queries)-1]
}
