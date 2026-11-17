package util

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"io"
	commtypes "k8s-dbs/common/types"
	"testing"
	"time"
)

func TestDetectDatabaseLocation(t *testing.T) {
	t.Setenv("TZ", "Asia/Shanghai")
	tests := []struct {
		name       string
		session    string
		system     string
		offset     int64
		databaseAt string
	}{
		{"system_cst", "SYSTEM", "CST", 28800, "2026-11-11 17:08:20"},
		{"system_utc", "SYSTEM", "UTC", 0, "2026-11-11 09:08:20"},
		{"explicit_offset", "+08:00", "UTC", 28800, "2026-11-11 17:08:20"},
		{"named_timezone", "Asia/Shanghai", "UTC", 28800, "2026-11-11 17:08:20"},
		{"system_cst_negative", "SYSTEM", "CST", -21600, "2026-11-11 03:08:20"},
		{"negative_offset", "-06:00", "UTC", -21600, "2026-11-11 03:08:20"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var queries []string
			db := sql.OpenDB(timeZoneTestConnector{
				values:  []driver.Value{tt.session, tt.system, tt.offset},
				queries: &queries,
			})
			defer db.Close()
			loc, err := detectDatabaseLocation(db)
			if err != nil {
				t.Fatal(err)
			}
			if len(queries) != 1 || queries[0] != timeZoneTestQuery {
				t.Fatalf("unexpected queries: %v", queries)
			}
			parsed, err := time.ParseInLocation(time.DateTime, tt.databaseAt, loc)
			if err != nil {
				t.Fatal(err)
			}
			if got := parsed.UTC().Format(time.DateTime); got != "2026-11-11 09:08:20" {
				t.Fatalf("incorrect instant: %s", got)
			}
			var value commtypes.JSONDatetime
			if err := value.Scan(parsed); err != nil {
				t.Fatal(err)
			}
			data, err := value.MarshalJSON()
			if err != nil {
				t.Fatal(err)
			}
			if string(data) != `"2026-11-11 17:08:20"` {
				t.Fatalf("incorrect response time: %s", data)
			}
			queryTime, err := time.ParseInLocation(time.DateTime, "2026-11-11 17:08:20", commtypes.Location())
			if err != nil {
				t.Fatal(err)
			}
			if got := queryTime.In(loc).Format(time.DateTime); got != tt.databaseAt {
				t.Fatalf("incorrect query time: %s", got)
			}
			writeValue, err := value.Value()
			if err != nil {
				t.Fatal(err)
			}
			if got := writeValue.(time.Time).In(loc).Format(time.DateTime); got != tt.databaseAt {
				t.Fatalf("incorrect write parameter time: %s", got)
			}
		})
	}
}

func TestDetectDatabaseLocationErrors(t *testing.T) {
	tests := []struct {
		name   string
		values []driver.Value
		err    error
	}{
		{"query_failed", nil, errors.New("query failed")},
		{"unknown_timezone", []driver.Value{"Invalid/Timezone", "UTC", int64(0)}, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var queries []string
			db := sql.OpenDB(timeZoneTestConnector{values: tt.values, queries: &queries, err: tt.err})
			defer db.Close()
			if _, err := detectDatabaseLocation(db); err == nil {
				t.Fatal("expected timezone detection to fail")
			}
		})
	}
}

const timeZoneTestQuery = "SELECT @@session.time_zone, @@system_time_zone, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())"

type timeZoneTestConnector struct {
	values  []driver.Value
	queries *[]string
	err     error
}

func (c timeZoneTestConnector) Connect(context.Context) (driver.Conn, error) {
	return timeZoneTestConn{c}, nil
}

func (c timeZoneTestConnector) Driver() driver.Driver { return timeZoneTestDriver{} }

type timeZoneTestDriver struct{}

func (timeZoneTestDriver) Open(string) (driver.Conn, error) {
	return nil, errors.New("unexpected driver Open")
}

type timeZoneTestConn struct{ timeZoneTestConnector }

func (timeZoneTestConn) Prepare(string) (driver.Stmt, error) {
	return nil, errors.New("unexpected Prepare")
}

func (timeZoneTestConn) Close() error { return nil }

func (timeZoneTestConn) Begin() (driver.Tx, error) {
	return nil, errors.New("unexpected Begin")
}

func (c timeZoneTestConn) QueryContext(_ context.Context, query string, _ []driver.NamedValue) (driver.Rows, error) {
	*c.queries = append(*c.queries, query)
	if query != timeZoneTestQuery {
		return nil, errors.New("unexpected query")
	}
	if c.err != nil {
		return nil, c.err
	}
	return &timeZoneTestRows{values: c.values}, nil
}

type timeZoneTestRows struct {
	values []driver.Value
	done   bool
}

func (*timeZoneTestRows) Columns() []string { return []string{"session", "system", "offset"} }
func (*timeZoneTestRows) Close() error      { return nil }

func (r *timeZoneTestRows) Next(dest []driver.Value) error {
	if r.done {
		return io.EOF
	}
	copy(dest, r.values)
	r.done = true
	return nil
}
