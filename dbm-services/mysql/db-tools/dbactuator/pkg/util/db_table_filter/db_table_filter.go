// Package db_table_filter 库表过滤
package db_table_filter

import (
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
	_ "github.com/go-sql-driver/mysql" // mysql 驱动
	"github.com/jmoiron/sqlx"
)

// DbTableFilter 库表过滤
type DbTableFilter struct {
	IncludeDbPatterns       []string
	IncludeTablePatterns    []string
	ExcludeDbPatterns       []string
	ExcludeTablePatterns    []string
	dbFilterIncludeRegex    string
	dbFilterExcludeRegex    string
	tableFilterIncludeRegex string
	tableFilterExcludeRegex string
}

// NewDbTableFilter 构造函数
// 如果是 mydumper，内置忽略 infodba_schema.conn_log 表
// NewDbTableFilter 完成后，需要 BuildFilter()
func NewDbTableFilter(
	includeDbPatterns []string,
	includeTablePatterns []string,
	excludeDbPatterns []string,
	excludeTablePatterns []string,
) (*DbTableFilter, error) {

	tf := &DbTableFilter{
		IncludeDbPatterns:       cleanIt(includeDbPatterns),
		IncludeTablePatterns:    cleanIt(includeTablePatterns),
		ExcludeDbPatterns:       cleanIt(excludeDbPatterns),
		ExcludeTablePatterns:    cleanIt(excludeTablePatterns),
		dbFilterIncludeRegex:    "",
		dbFilterExcludeRegex:    "",
		tableFilterIncludeRegex: "",
		tableFilterExcludeRegex: "",
	}

	err := tf.validate()
	if err != nil {
		return nil, err
	}

	return tf, nil
}

// BuildFilter normal build filter
// is different with NewMydumperRegex
func (c *DbTableFilter) BuildFilter() {
	c.buildDbFilterRegex()
	c.buildTableFilterRegex()
}

func (c *DbTableFilter) validate() error {
	if len(c.IncludeDbPatterns) == 0 || len(c.IncludeTablePatterns) == 0 {
		return fmt.Errorf("include patterns can't be empty")
	}
	if !((len(c.ExcludeDbPatterns) > 0 && len(c.ExcludeTablePatterns) > 0) ||
		(len(c.ExcludeDbPatterns) == 0 && len(c.ExcludeTablePatterns) == 0)) {
		return fmt.Errorf("exclude patterns can't be partial empty")
	}

	if err := globCheck(c.IncludeDbPatterns); err != nil {
		return err
	}
	if err := globCheck(c.IncludeTablePatterns); err != nil {
		return err
	}
	if err := globCheck(c.ExcludeDbPatterns); err != nil {
		return err
	}
	if err := globCheck(c.ExcludeTablePatterns); err != nil {
		return err
	}
	return nil
}

func (c *DbTableFilter) buildDbFilterRegex() {
	var includeParts []string
	for _, db := range c.IncludeDbPatterns {
		includeParts = append(includeParts, fmt.Sprintf(`%s$`, ReplaceGlob(db)))
	}

	var excludeParts []string
	for _, db := range c.ExcludeDbPatterns {
		excludeParts = append(excludeParts, fmt.Sprintf(`%s$`, ReplaceGlob(db)))
	}
	c.dbFilterIncludeRegex = buildIncludeRegexp(includeParts)
	c.dbFilterExcludeRegex = buildExcludeRegexp(excludeParts)
}

func (c *DbTableFilter) buildTableFilterRegex() {
	var includeParts []string
	for _, db := range c.IncludeDbPatterns {
		for _, table := range c.IncludeTablePatterns {
			includeParts = append(
				includeParts,
				fmt.Sprintf(`%s\.%s$`, ReplaceGlob(db), ReplaceGlob(table)),
			)
		}
	}

	var excludeParts []string
	for _, db := range c.ExcludeDbPatterns {
		for _, table := range c.ExcludeTablePatterns {
			excludeParts = append(
				excludeParts,
				fmt.Sprintf(`%s\.%s$`, ReplaceGlob(db), ReplaceGlob(table)),
			)
		}
	}
	/*
		if mydumper {
			// ignore infodba_schema.conn_log
			// 这里没有放到 ExcludeDbPatterns=[infodba_schema, mysql,test...], ExcludeTablePatterns=[conn_log] 里，因为会拼多
			excludeParts = append(excludeParts, fmt.Sprintf(`%s\.%s$`, native.INFODBA_SCHEMA, "conn_log"))
		}
	*/
	c.tableFilterIncludeRegex = buildIncludeRegexp(includeParts)
	c.tableFilterExcludeRegex = buildExcludeRegexp(excludeParts)
}

// TableFilterRegex 返回表过滤正则
func (c *DbTableFilter) TableFilterRegex() string {
	return fmt.Sprintf(`^%s%s`, c.tableFilterIncludeRegex, c.tableFilterExcludeRegex)
}

// DbFilterRegex 返回库过滤正则
func (c *DbTableFilter) DbFilterRegex() string {
	return fmt.Sprintf(`^%s%s`, c.dbFilterIncludeRegex, c.dbFilterExcludeRegex)
}

// GetTables 过滤后的表
func (c *DbTableFilter) GetTables(ip string, port int, user string, password string) ([]string, error) {
	return c.getTablesByRegexp(
		ip,
		port,
		user,
		password,
		c.TableFilterRegex(),
	)
}

// GetDbs 过滤后的库
func (c *DbTableFilter) GetDbs(ip string, port int, user string, password string) ([]string, error) {
	return c.getDbsByRegexp(
		ip,
		port,
		user,
		password,
		c.DbFilterRegex(),
	)
}

// GetExcludeDbs 排除的库
func (c *DbTableFilter) GetExcludeDbs(ip string, port int, user string, password string) ([]string, error) {
	if c.dbFilterExcludeRegex == "" {
		return []string{}, nil
	}
	return c.getDbsByRegexp(
		ip,
		port,
		user,
		password,
		strings.Replace(c.dbFilterExcludeRegex, "!", "=", 1), // 替换掉第一个 ! , 这样就变成匹配模式
	)
}

// GetExcludeTables 排除的表
func (c *DbTableFilter) GetExcludeTables(ip string, port int, user string, password string) ([]string, error) {
	if c.tableFilterExcludeRegex == "" {
		return []string{}, nil
	}
	return c.getTablesByRegexp(
		ip,
		port,
		user,
		password,
		strings.Replace(c.tableFilterExcludeRegex, "!", "=", 1),
	)
}

func (c *DbTableFilter) getDbsByRegexp(ip string, port int, user string, password string, reg string) (
	[]string,
	error,
) {
	dbh, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s:%d)/`, user, password, ip, port),
	)
	if err != nil {
		return nil, err
	}

	rows, err := dbh.Queryx(`SHOW DATABASES`)
	if err != nil {
		return nil, err
	}

	pattern, err := regexp2.Compile(reg, regexp2.None)
	if err != nil {
		return nil, err
	}

	var selectedDbs []string
	for rows.Next() {
		var database string
		err := rows.Scan(&database)
		if err != nil {
			return nil, err
		}

		ok, err := pattern.MatchString(database)
		if err != nil {
			return nil, err
		}
		if ok {
			selectedDbs = append(selectedDbs, database)
		}
	}

	return selectedDbs, nil
}

func (c *DbTableFilter) getTablesByRegexp(ip string, port int, user string, password string, reg string) (
	[]string,
	error,
) {
	dbh, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s:%d)/`, user, password, ip, port),
	)
	if err != nil {
		return nil, err
	}

	rows, err := dbh.Queryx(
		`SELECT CONCAT(table_schema, ".", table_name) AS fullname` +
			` from INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE="BASE TABLE"`,
	)
	if err != nil {
		return nil, err
	}

	pattern, err := regexp2.Compile(reg, regexp2.None)
	if err != nil {
		return nil, err
	}

	var selectedTables []string
	for rows.Next() {
		var fullname string
		err := rows.Scan(&fullname)
		if err != nil {
			return nil, err
		}

		ok, err := pattern.MatchString(fullname)
		if err != nil {
			return nil, err
		}
		if ok {
			selectedTables = append(selectedTables, fullname)
		}
	}

	return selectedTables, nil
}
