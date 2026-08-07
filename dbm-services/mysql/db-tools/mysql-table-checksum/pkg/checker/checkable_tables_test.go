package checker

import (
	"testing"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

func TestChecksumTableFilter(t *testing.T) {
	filter, err := newChecksumTableFilter(config.Filter{
		IgnoreDatabases:      []string{"mysql", "infodba_schema"},
		IgnoreDatabasesRegex: "bak_.*",
	})
	if err != nil {
		t.Fatalf("newChecksumTableFilter: %v", err)
	}

	cases := []struct {
		db, tbl string
		want    bool
	}{
		{"mysql", "user", false},
		{"infodba_schema", "checksum", false},
		{"bak_20240101", "t1", false},
		{"biz", "t1", true},
	}
	for _, tc := range cases {
		got := filter.isCheckable(tc.db, tc.tbl)
		if got != tc.want {
			t.Fatalf("isCheckable(%q, %q) = %v, want %v", tc.db, tc.tbl, got, tc.want)
		}
	}
}

func TestChecksumTableFilterDbAllowed(t *testing.T) {
	filter, err := newChecksumTableFilter(config.Filter{
		IgnoreDatabases: []string{"mysql", "infodba_schema"},
	})
	if err != nil {
		t.Fatalf("newChecksumTableFilter: %v", err)
	}

	if !filter.dbAllowed("empty_biz") {
		t.Fatal("empty business db should pass db filter")
	}
}
