package checker

import (
	"context"
	"log/slog"
	"regexp"
	"strings"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

type checksumTableFilter struct {
	ignoreDbs         map[string]struct{}
	includeDbs        map[string]struct{}
	ignoreDbRegex     *regexp.Regexp
	includeDbRegex    *regexp.Regexp
	ignoreTablesAll   map[string]struct{}
	ignoreTablesByDb  map[string]map[string]struct{}
	includeTablesAll  map[string]struct{}
	includeTablesByDb map[string]map[string]struct{}
	ignoreTableRegex  *regexp.Regexp
	includeTableRegex *regexp.Regexp
	hasIncludeDb      bool
	hasIncludeTable   bool
}

func newChecksumTableFilter(filter config.Filter) (*checksumTableFilter, error) {
	f := &checksumTableFilter{
		ignoreDbs:         make(map[string]struct{}),
		includeDbs:        make(map[string]struct{}),
		ignoreTablesAll:   make(map[string]struct{}),
		ignoreTablesByDb:  make(map[string]map[string]struct{}),
		includeTablesAll:  make(map[string]struct{}),
		includeTablesByDb: make(map[string]map[string]struct{}),
	}

	for _, db := range filter.IgnoreDatabases {
		f.ignoreDbs[strings.ToLower(db)] = struct{}{}
	}
	for _, db := range filter.Databases {
		f.includeDbs[strings.ToLower(db)] = struct{}{}
	}
	f.hasIncludeDb = len(f.includeDbs) > 0

	parseQualifiedNames(filter.IgnoreTables, f.ignoreTablesAll, f.ignoreTablesByDb)
	parseQualifiedNames(filter.Tables, f.includeTablesAll, f.includeTablesByDb)
	f.hasIncludeTable = len(f.includeTablesAll) > 0 || len(f.includeTablesByDb) > 0

	var err error
	if filter.IgnoreDatabasesRegex != "" {
		f.ignoreDbRegex, err = regexp.Compile(filter.IgnoreDatabasesRegex)
		if err != nil {
			return nil, err
		}
	}
	if filter.DatabasesRegex != "" {
		f.includeDbRegex, err = regexp.Compile(filter.DatabasesRegex)
		if err != nil {
			return nil, err
		}
		f.hasIncludeDb = true
	}
	if filter.IgnoreTablesRegex != "" {
		f.ignoreTableRegex, err = regexp.Compile(filter.IgnoreTablesRegex)
		if err != nil {
			return nil, err
		}
	}
	if filter.TablesRegex != "" {
		f.includeTableRegex, err = regexp.Compile(filter.TablesRegex)
		if err != nil {
			return nil, err
		}
		f.hasIncludeTable = true
	}

	return f, nil
}

func parseQualifiedNames(items []string, all map[string]struct{}, byDb map[string]map[string]struct{}) {
	for _, item := range items {
		item = strings.ToLower(strings.TrimSpace(item))
		if item == "" {
			continue
		}
		if idx := strings.Index(item, "."); idx >= 0 {
			db := item[:idx]
			tbl := item[idx+1:]
			if byDb[db] == nil {
				byDb[db] = make(map[string]struct{})
			}
			byDb[db][tbl] = struct{}{}
			continue
		}
		all[item] = struct{}{}
	}
}

func (f *checksumTableFilter) dbAllowed(db string) bool {
	db = strings.ToLower(db)

	if _, ok := f.ignoreDbs[db]; ok {
		return false
	}
	if f.ignoreDbRegex != nil && f.ignoreDbRegex.MatchString(db) {
		return false
	}
	if f.hasIncludeDb {
		if _, ok := f.includeDbs[db]; ok {
			return true
		}
		if f.includeDbRegex != nil && f.includeDbRegex.MatchString(db) {
			return true
		}
		return false
	}
	return true
}

func (f *checksumTableFilter) tableAllowed(db, tbl string) bool {
	db = strings.ToLower(db)
	tbl = strings.ToLower(tbl)

	if _, ok := f.ignoreTablesAll[tbl]; ok {
		return false
	}
	if dbTables, ok := f.ignoreTablesByDb[db]; ok {
		if _, ok := dbTables[tbl]; ok {
			return false
		}
	}
	if f.ignoreTableRegex != nil && f.ignoreTableRegex.MatchString(tbl) {
		return false
	}
	if f.hasIncludeTable {
		if _, ok := f.includeTablesAll[tbl]; ok {
			return true
		}
		if dbTables, ok := f.includeTablesByDb[db]; ok {
			if _, ok := dbTables[tbl]; ok {
				return true
			}
		}
		if f.includeTableRegex != nil && f.includeTableRegex.MatchString(tbl) {
			return true
		}
		return false
	}
	return true
}

func (f *checksumTableFilter) isCheckable(db, tbl string) bool {
	return f.dbAllowed(db) && f.tableAllowed(db, tbl)
}

func (r *Checker) hasCheckableTables() (bool, error) {
	filter, err := newChecksumTableFilter(r.Config.Filter)
	if err != nil {
		slog.Error("build checksum table filter", slog.String("error", err.Error()))
		return false, err
	}

	rows, err := r.conn.QueryxContext(
		context.Background(),
		`SELECT table_schema, table_name
		 FROM information_schema.tables
		 WHERE table_type = 'BASE TABLE'`,
	)
	if err != nil {
		slog.Error("query checkable tables", slog.String("error", err.Error()))
		return false, err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		var db, tbl string
		if err := rows.Scan(&db, &tbl); err != nil {
			slog.Error("scan checkable tables", slog.String("error", err.Error()))
			return false, err
		}
		if filter.isCheckable(db, tbl) {
			return true, nil
		}
	}
	if err := rows.Err(); err != nil {
		slog.Error("iterate checkable tables", slog.String("error", err.Error()))
		return false, err
	}
	return false, nil
}
