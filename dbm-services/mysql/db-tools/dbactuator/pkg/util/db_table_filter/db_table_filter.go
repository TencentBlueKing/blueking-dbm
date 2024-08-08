/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package db_table_filter 库表过滤
package db_table_filter

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
	_ "github.com/go-sql-driver/mysql" // mysql 驱动
	"github.com/jmoiron/sqlx"
)

var impossibleTableName = "@@<<~%~empty db~%~>>@@"

// DbTableFilter 库表过滤
type DbTableFilter struct {
	IncludeDbPatterns       []string
	IncludeTablePatterns    []string
	ExcludeDbPatterns       []string
	ExcludeTablePatterns    []string
	AdditionExcludePatterns []string // 隐式需要强制排除的库, 比如系统库之类的. 这些库的 ExcludeTable 强制为 *
	dbFilterIncludeRegex    string
	dbFilterExcludeRegex    string
	tableFilterIncludeRegex string
	tableFilterExcludeRegex string
}

// NewDbTableFilter 构造函数
// 如果是 mydumper，内置忽略 infodba_schema.conn_log 表
// NewDbTableFilter 完成后，需要 BuildFilter()
func NewDbTableFilter(includeDbPatterns []string, includeTablePatterns []string,
	excludeDbPatterns []string, excludeTablePatterns []string) (*DbTableFilter, error) {

	tf := &DbTableFilter{
		IncludeDbPatterns:       cleanIt(includeDbPatterns),
		IncludeTablePatterns:    cleanIt(includeTablePatterns),
		ExcludeDbPatterns:       cleanIt(excludeDbPatterns),
		ExcludeTablePatterns:    cleanIt(excludeTablePatterns),
		AdditionExcludePatterns: []string{},
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

	for _, db := range c.AdditionExcludePatterns {
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

	for _, db := range c.AdditionExcludePatterns {
		excludeParts = append(
			excludeParts,
			fmt.Sprintf(`%s\.%s$`, ReplaceGlob(db), ReplaceGlob("*")),
		)
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
func (c *DbTableFilter) GetTables(ip string, port int, user string, password string) (map[string][]string, error) {
	return c.getTablesByRegexp(
		ip,
		port,
		user,
		password,
		c.TableFilterRegex(),
	)
}

func (c *DbTableFilter) GetTablesByConn(conn *sqlx.Conn) (map[string][]string, error) {
	return c.getTablesByRegexpConn(conn, c.TableFilterRegex())
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

func (c *DbTableFilter) GetDbsByConn(conn *sqlx.Conn) ([]string, error) {
	return c.getDbsByRegexpConn(conn, c.DbFilterRegex())
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
func (c *DbTableFilter) GetExcludeTables(ip string, port int, user string, password string) (map[string][]string, error) {
	if c.tableFilterExcludeRegex == "" {
		return map[string][]string{}, nil
	}
	return c.getTablesByRegexp(
		ip,
		port,
		user,
		password,
		strings.Replace(c.tableFilterExcludeRegex, "!", "=", 1),
	)
}

func (c *DbTableFilter) getDbsByRegexpConn(conn *sqlx.Conn, reg string) ([]string, error) {
	rows, err := conn.QueryxContext(context.Background(), `SHOW DATABASES`)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = rows.Close()
	}()

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

	// close connect
	defer func() {
		if dbh != nil {
			_ = dbh.Close()
		}
	}()

	conn, err := dbh.Connx(context.Background())
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = conn.Close()
	}()

	return c.getDbsByRegexpConn(conn, reg)
}

func (c *DbTableFilter) getTablesByRegexp(ip string, port int, user string, password string, reg string) (
	map[string][]string,
	error,
) {
	dbh, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s:%d)/`, user, password, ip, port),
	)
	if err != nil {
		return nil, err
	}

	// close connect
	defer func() {
		if dbh != nil {
			_ = dbh.Close()
		}
	}()

	conn, err := dbh.Connx(context.Background())
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = conn.Close()
	}()

	return c.getTablesByRegexpConn(conn, reg)
}

func (c *DbTableFilter) getTablesByRegexpConn(conn *sqlx.Conn, reg string) (map[string][]string, error) {
	var dbs []string
	err := conn.SelectContext(context.Background(), &dbs, "SHOW DATABASES") //.Scan(&dbs)
	if err != nil {
		return nil, err
	}

	var fullnames []string
	for _, db := range dbs {
		var tables []string
		err := conn.SelectContext(
			context.Background(),
			&tables,
			`SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                  		WHERE TABLE_TYPE = "BASE TABLE" AND TABLE_SCHEMA = ?`,
			db,
		) //.Scan(&tables)
		if err != nil {
			return nil, err
		}

		if len(tables) == 0 {
			// 空库写入一个绝对不可能的假表名
			tables = []string{impossibleTableName}
		}

		for _, table := range tables {
			fullnames = append(fullnames, fmt.Sprintf("%s.%s", db, table))
		}
	}
	logger.Info("all table fullnames: %v", fullnames)

	res := make(map[string][]string)
	pattern, err := regexp2.Compile(reg, regexp2.None)
	if err != nil {
		return nil, err
	}
	for _, fullname := range fullnames {
		isMatch, err := pattern.MatchString(fullname)
		if err != nil {
			return nil, err
		}

		// 空库写了个特别不可能的假表名
		// 所以可以认为
		// 1. 如果只有 include table, 只有是 * 才可能匹配
		// 2. 如果有 include table 和 ignore table, include table 也必须是 * 才可能
		// 2.1 ignore table 不是 * 根本没办法排除
		// 2.2 ignore table 不是 * 会被匹配
		// 这样, 当一个库是空库时就能正确返回
		if isMatch {
			logger.Info("%s match", fullname)

			splitName := strings.Split(fullname, ".")
			logger.Info("%s split to %v", fullname, splitName)

			if _, ok := res[splitName[0]]; !ok {
				res[splitName[0]] = make([]string, 0)
			}

			if splitName[1] != impossibleTableName {
				res[splitName[0]] = append(res[splitName[0]], splitName[1])
				logger.Info("append %s to res", splitName[1])
			}
		} else {
			logger.Info("%s not match", fullname)
		}
	}

	logger.Info("get target res: %v", res)
	return res, nil
}
