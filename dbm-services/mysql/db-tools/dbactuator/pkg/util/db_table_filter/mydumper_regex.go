package db_table_filter

import (
	"fmt"
	"strings"
)

func BuildMydumperRegex(
	includeDbPatterns []string,
	includeTablePatterns []string,
	excludeDbPatterns []string,
	excludeTablePatterns []string,
) (*DbTableFilter, error) {
	tf, err := NewDbTableFilter(includeDbPatterns, includeTablePatterns, excludeDbPatterns, excludeTablePatterns)
	if err != nil {
		return nil, err
	}

	tf.buildDbFilterRegex()
	tf.buildTableFilterRegex()
	return tf, nil
}

// MyloaderRegex TODO
func (c *DbTableFilter) MyloaderRegex(doDr bool) string {
	if doDr {
		// infodba_schema 不忽略，因为需要同步旧库的信息过来，不然replication可能会报错
		sysDBExclude := `^(?!(mysql\.|sys\.|test\.|db_infobase\.))`
		return sysDBExclude
	}
	for i, db := range c.IncludeDbPatterns {
		c.IncludeDbPatterns[i] = fmt.Sprintf(`%s\.`, ReplaceGlob(db))
	}
	for i, tb := range c.IncludeTablePatterns {
		if containGlob(tb) {
			c.IncludeTablePatterns[i] = ReplaceGlob(tb)
		} else {
			c.IncludeTablePatterns[i] = fmt.Sprintf(`%s$`, tb)
		}
	}
	for i, db := range c.ExcludeDbPatterns {
		c.ExcludeDbPatterns[i] = fmt.Sprintf(`%s\.`, ReplaceGlob(db))
	}
	for i, tb := range c.ExcludeTablePatterns {
		if containGlob(tb) {
			c.ExcludeTablePatterns[i] = ReplaceGlob(tb)
		} else {
			c.ExcludeTablePatterns[i] = fmt.Sprintf(`%s$`, tb)
		}
	}

	c.dbFilterIncludeRegex = buildRegexString(c.IncludeDbPatterns)
	c.tableFilterIncludeRegex = buildRegexString(c.IncludeTablePatterns)
	c.dbFilterExcludeRegex = buildRegexString(c.ExcludeDbPatterns)
	c.tableFilterExcludeRegex = buildRegexString(c.ExcludeTablePatterns)

	if c.dbFilterIncludeRegex != "" && c.dbFilterExcludeRegex == "" {
		dbtableInclude := fmt.Sprintf(`^(%s%s)`, c.dbFilterIncludeRegex, c.tableFilterIncludeRegex)
		return dbtableInclude
	}

	if c.dbFilterExcludeRegex != "" && c.dbFilterIncludeRegex == "" {
		dbtableExclude := fmt.Sprintf(`^(?!(%s%s))`, c.dbFilterExcludeRegex, c.tableFilterExcludeRegex)
		return dbtableExclude
	}
	if c.dbFilterIncludeRegex != "" && c.dbFilterExcludeRegex != "" {
		dbtable := fmt.Sprintf(`^(?=(?:%s%s))(?!(?:%s%s))`, c.dbFilterIncludeRegex, c.tableFilterIncludeRegex,
			c.dbFilterExcludeRegex, c.tableFilterExcludeRegex)
		return dbtable
	}
	return ""
}

func buildRegexString(patterns []string) string {
	ss := strings.Join(patterns, "|")
	if len(patterns) > 1 {
		ss = fmt.Sprintf(`(%s)`, ss)
	}
	return ss
}
