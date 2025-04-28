/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tiparser

import (
	"bytes"
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/pingcap/tidb/pkg/parser"
	"github.com/pingcap/tidb/pkg/parser/ast"
	"github.com/pingcap/tidb/pkg/parser/format"
	"github.com/pingcap/tidb/pkg/parser/mysql"
	"github.com/pingcap/tidb/pkg/parser/opcode"
	driver "github.com/pingcap/tidb/pkg/parser/test_driver"
)

func ParseSql(sql string) ([]ast.StmtNode, error) {
	p := parser.New()
	stmts, _, err := p.Parse(sql, "", "")
	if err != nil {
		return nil, err
	}
	return stmts, nil
}

// ParseOneSql 解析单个sql
func ParseOneSql(sql string) (ast.StmtNode, error) {
	p := parser.New()
	stmt, err := p.ParseOneStmt(sql, "", "")
	if err != nil {
		fmt.Printf("parse error: %v\nsql: %v", err, sql)
		return nil, err
	}
	return stmt, nil
}

// GetNumberOfJoinTables 获取Join语句的表数量
func GetNumberOfJoinTables(stmt *ast.Join) int {
	nums := 0
	if stmt == nil {
		return nums
	}
	parseTableFunc := func(resultSetNode ast.ResultSetNode) int {
		switch t := resultSetNode.(type) {
		case *ast.TableSource:
			return 1
		case *ast.Join:
			return GetNumberOfJoinTables(t)
		}
		return 0
	}
	nums += parseTableFunc(stmt.Left) + parseTableFunc(stmt.Right)
	return nums
}

// GetTableFromOnCondition 获取Join语句的OnCondition
func GetTableFromOnCondition(stmt *ast.Join) []*ast.OnCondition {
	onConditions := make([]*ast.OnCondition, 0)
	if stmt == nil {
		return onConditions
	}

	// 如果最外层的ON Condition为nil，内层ON Condition一定也为nil，不需要再递归子节点
	if stmt.On != nil {
		onConditions = append(onConditions, stmt.On)
		onConditions = append(onConditions, getTableFromOnCondition(stmt)...)
	}

	return onConditions
}

func getTableFromOnCondition(stmt *ast.Join) []*ast.OnCondition {
	onConditions := make([]*ast.OnCondition, 0)
	parseTableFunc := func(resultSetNode ast.ResultSetNode) []*ast.OnCondition {
		switch t := resultSetNode.(type) {
		case *ast.Join:
			if t.On != nil {
				onConditions = append(onConditions, t.On)
			}
			return getTableFromOnCondition(t)
		}
		return nil
	}

	onConditions = append(onConditions, parseTableFunc(stmt.Left)...)
	onConditions = append(onConditions, parseTableFunc(stmt.Right)...)

	return onConditions
}

// GetTables 获取Join语句的表名
func GetTables(stmt *ast.Join) []*ast.TableName {
	tables := []*ast.TableName{}
	if stmt == nil {
		return tables
	}
	if n := stmt.Right; n != nil {
		switch t := n.(type) {
		case *ast.TableSource:
			tableName, ok := t.Source.(*ast.TableName)
			if ok {
				tables = append(tables, tableName)
			}
		case *ast.Join:
			tables = append(tables, GetTables(t)...)
		}
	}
	if n := stmt.Left; n != nil {
		switch t := n.(type) {
		case *ast.TableSource:
			tableName, ok := t.Source.(*ast.TableName)
			if ok {
				tables = append(tables, tableName)
			}
		case *ast.Join:
			tables = append(tables, GetTables(t)...)
		}
	}
	return tables
}

// GetTableSources 获取Join语句的TableSource
func GetTableSources(stmt *ast.Join) []*ast.TableSource {
	sources := []*ast.TableSource{}
	if stmt == nil {
		return sources
	}
	if n := stmt.Left; n != nil {
		switch t := n.(type) {
		case *ast.TableSource:
			sources = append(sources, t)
		case *ast.Join:
			sources = append(sources, GetTableSources(t)...)
		}
	}
	if n := stmt.Right; n != nil {
		switch t := n.(type) {
		case *ast.TableSource:
			sources = append(sources, t)
		case *ast.Join:
			sources = append(sources, GetTableSources(t)...)
		}
	}
	return sources
}

// GetTableNameWithQuote 获取带引号的表名
func GetTableNameWithQuote(stmt *ast.TableName) string {
	if stmt.Schema.String() == "" {
		return fmt.Sprintf("`%s`", stmt.Name)
	} else {
		return fmt.Sprintf("`%s`.`%s`", stmt.Schema, stmt.Name)
	}
}

// RemoveArrayRepeat 去重
func RemoveArrayRepeat(input []string) (output []string) {
	for _, i := range input {
		repeat := false
		for _, j := range output {
			if i == j {
				repeat = true
				break
			}
		}
		if !repeat {
			output = append(output, i)
		}
	}
	return output
}

// IsAllInOptions 判断是否都是指定的类型
func IsAllInOptions(Options []*ast.ColumnOption, opTp ...ast.ColumnOptionType) bool {
	exists := make(map[ast.ColumnOptionType]bool, len(opTp))
	for _, tp := range opTp {
		for _, op := range Options {
			if tp == op.Tp {
				exists[tp] = true
			}
		}
	}
	// has one no exists, return false
	for _, tp := range opTp {
		if _, exist := exists[tp]; !exist {
			return false
		}
	}
	return true
}

// HasOneInOptions has one in options
func HasOneInOptions(Options []*ast.ColumnOption, opTp ...ast.ColumnOptionType) bool {
	// has one exists, return true
	for _, tp := range opTp {
		for _, op := range Options {
			if tp == op.Tp {
				return true
			}
		}
	}
	return false
}

// MysqlDataTypeIsBlob 判断是否为blob类型
func MysqlDataTypeIsBlob(tp byte) bool {
	switch tp {
	case mysql.TypeBlob, mysql.TypeLongBlob, mysql.TypeMediumBlob, mysql.TypeTinyBlob:
		return true
	default:
		return false
	}
}

// ScanWhereStmt scan where stmt
func ScanWhereStmt(fn func(expr ast.ExprNode) (skip bool), exprs ...ast.ExprNode) {
	for _, expr := range exprs {
		if expr == nil {
			continue
		}
		// skip all children node
		if fn(expr) {
			continue
		}
		switch x := expr.(type) {
		case *ast.ColumnNameExpr:
		case *ast.SubqueryExpr:
		case *ast.BinaryOperationExpr:
			ScanWhereStmt(fn, x.L, x.R)
		case *ast.UnaryOperationExpr:
			ScanWhereStmt(fn, x.V)
			// boolean_primary is true|false
		case *ast.IsTruthExpr:
			ScanWhereStmt(fn, x.Expr)
			// boolean_primary is (not) null
		case *ast.IsNullExpr:
			ScanWhereStmt(fn, x.Expr)
			// boolean_primary comparison_operator {ALL | ANY} (subquery)
		case *ast.CompareSubqueryExpr:
			ScanWhereStmt(fn, x.L, x.R)
		case *ast.ExistsSubqueryExpr:
			ScanWhereStmt(fn, x.Sel)
			// boolean_primary IN (expr,...)
		case *ast.PatternInExpr:
			es := []ast.ExprNode{}
			es = append(es, x.Expr)
			es = append(es, x.Sel)
			es = append(es, x.List...)
			ScanWhereStmt(fn, es...)
			// boolean_primary Between expr and expr
		case *ast.BetweenExpr:
			ScanWhereStmt(fn, x.Expr, x.Left, x.Right)
			// boolean_primary (not) like expr
		case *ast.PatternLikeOrIlikeExpr:
			ScanWhereStmt(fn, x.Expr, x.Pattern)
			// boolean_primary (not) regexp expr
		case *ast.PatternRegexpExpr:
			ScanWhereStmt(fn, x.Expr, x.Pattern)
		case *ast.RowExpr:
			ScanWhereStmt(fn, x.Values...)
		case *ast.ParenthesesExpr:
			ScanWhereStmt(fn, x.Expr)
		}
	}
}

// WhereStmtHasSubQuery check if where stmt has subquery
func WhereStmtHasSubQuery(where ast.ExprNode) bool {
	hasSubQuery := false
	ScanWhereStmt(func(expr ast.ExprNode) (skip bool) {
		switch expr.(type) {
		case *ast.SubqueryExpr:
			hasSubQuery = true
			return true
		}
		return false
	}, where)
	return hasSubQuery
}

// IsFuncUsedOnColumnInWhereStmt check if where stmt has func used on column
func IsFuncUsedOnColumnInWhereStmt(cols map[string]struct{}, where ast.ExprNode) bool {
	usedFunc := false
	ScanWhereStmt(func(expr ast.ExprNode) (skip bool) {
		switch x := expr.(type) {
		case *ast.FuncCallExpr:
			for _, columnNameExpr := range x.Args {
				if col1, ok := columnNameExpr.(*ast.ColumnNameExpr); ok {
					if _, ok := cols[col1.Name.String()]; ok {
						usedFunc = true
						return true
					}
				}
			}
		}
		return false
	}, where)
	return usedFunc
}

// ScanColumnValueFromExpr scan column value from where stmt
func ScanColumnValueFromExpr(where ast.ExprNode, fn func(*ast.ColumnName, []*driver.ValueExpr) bool) {
	ScanWhereStmt(func(expr ast.ExprNode) (skip bool) {
		var values []*driver.ValueExpr
		var columnNameExpr *ast.ColumnNameExpr

		switch x := expr.(type) {
		case *ast.BinaryOperationExpr:
			if colValue, checkValueExpr := x.L.(*driver.ValueExpr); checkValueExpr {
				values = append(values, colValue)
			} else if columnName, checkColumnNameExpr := x.L.(*ast.ColumnNameExpr); checkColumnNameExpr {
				columnNameExpr = columnName
			} else {
				return false
			}
			if colValue, checkValueExpr := x.R.(*driver.ValueExpr); checkValueExpr {
				values = append(values, colValue)
			} else if columnName, checkColumnNameExpr := x.R.(*ast.ColumnNameExpr); checkColumnNameExpr {
				columnNameExpr = columnName
			} else {
				return false
			}
			if len(values) == 0 || columnNameExpr == nil {
				return false
			}

			return fn(columnNameExpr.Name, values)
		case *ast.PatternInExpr:
			c, ok := x.Expr.(*ast.ColumnNameExpr)
			if !ok {
				return false
			}
			columnNameExpr = c
			for _, expr := range x.List {
				if v, ok := expr.(*driver.ValueExpr); ok {
					values = append(values, v)
				}
			}
			if len(values) == 0 || columnNameExpr == nil {
				return false
			}

			return fn(columnNameExpr.Name, values)
		}
		return false
	}, where)
}

// WhereStmtExistNot where stmt exist not
func WhereStmtExistNot(where ast.ExprNode) bool {
	existNOT := false
	ScanWhereStmt(func(expr ast.ExprNode) (skip bool) {
		switch x := expr.(type) {
		case *ast.IsNullExpr:
			existNOT = true
			return true
		case *ast.BinaryOperationExpr:
			if x.Op == opcode.NE || x.Op == opcode.Not {
				existNOT = true
				return true
			}
		case *ast.PatternInExpr:
			if x.Not {
				existNOT = true
				return true
			}
		case *ast.PatternLikeOrIlikeExpr:
			if x.Not {
				existNOT = true
				return true
			}
		case *ast.ExistsSubqueryExpr:
			if v, ok := x.Sel.(*ast.SubqueryExpr); ok && x.Not && v.Exists {
				existNOT = true
				return true
			}
		}
		return false
	}, where)
	return existNOT
}

func WhereStmtExistScalarSubQueries(where ast.ExprNode) bool {
	existScalarSubQueries := false
	ScanWhereStmt(func(expr ast.ExprNode) (skip bool) {
		switch x := expr.(type) {
		case *ast.SubqueryExpr:
			if query, ok := x.Query.(*ast.SelectStmt); ok {
				if len(query.Fields.Fields) == 1 {
					existScalarSubQueries = true
					return true
				}
			}
		}
		return false
	}, where)
	return existScalarSubQueries
}

// GetAlterTableSpecByTp get alter table spec by type
func GetAlterTableSpecByTp(specs []*ast.AlterTableSpec, ts ...ast.AlterTableType) []*ast.AlterTableSpec {
	s := []*ast.AlterTableSpec{}
	if specs == nil {
		return s
	}
	for _, spec := range specs {
		for _, tp := range ts {
			if spec.Tp == tp {
				s = append(s, spec)
			}
		}
	}
	return s
}

func NewTableName(schema, table string) *ast.TableName {
	return &ast.TableName{
		Name:   ast.NewCIStr(table),
		Schema: ast.NewCIStr(schema),
	}
}

// GetPrimaryKey get primary key
func GetPrimaryKey(stmt *ast.CreateTableStmt) (map[string]struct{}, bool) {
	hasPk := false
	pkColumnsName := map[string]struct{}{}
	for _, constraint := range stmt.Constraints {
		if constraint.Tp == ast.ConstraintPrimaryKey {
			hasPk = true
			for _, col := range constraint.Keys {
				pkColumnsName[col.Column.Name.L] = struct{}{}
			}
		}
	}
	if !hasPk {
		for _, col := range stmt.Cols {
			if HasOneInOptions(col.Options, ast.ColumnOptionPrimaryKey) {
				hasPk = true
				pkColumnsName[col.Name.Name.L] = struct{}{}
			}
		}
	}
	return pkColumnsName, hasPk
}

// HasPrimaryKey 判断是否有主键
func HasPrimaryKey(stmt *ast.CreateTableStmt) bool {
	_, hasPk := GetPrimaryKey(stmt)
	return hasPk
}

func HasUniqIndex(stmt *ast.CreateTableStmt) bool {
	for _, constraint := range stmt.Constraints {
		switch constraint.Tp {
		case ast.ConstraintUniq:
			return true
		}
	}
	return false
}

func replaceTableName(query, schema, table string) string {
	re := regexp.MustCompile(fmt.Sprintf("%s\\.%s|`%s`\\.`%s`|`%s`\\.%s|%s\\.`%s`",
		schema, table, schema, table, schema, table, schema, table))
	return re.ReplaceAllString(query, fmt.Sprintf("`%s`", table))
}

func GetLimitCount(limit *ast.Limit, _default int64) (int64, error) {
	if limit == nil {
		return _default, nil
	}
	return strconv.ParseInt(ExprFormat(limit.Count), 0, 64)
}

// TableChecker check table
type TableChecker struct {
	schemaTables map[string]map[string]*ast.CreateTableStmt
}

// NewTableChecker create a new TableChecker
func NewTableChecker() *TableChecker {
	return &TableChecker{
		schemaTables: map[string]map[string]*ast.CreateTableStmt{},
	}
}

func (t *TableChecker) Add(schemaName, tableName string, table *ast.CreateTableStmt) {
	tables, ok := t.schemaTables[schemaName]
	if ok {
		tables[tableName] = table
	} else {
		t.schemaTables[schemaName] = map[string]*ast.CreateTableStmt{tableName: table}
	}
}

// CheckColumnByName check if table has column
func (t *TableChecker) CheckColumnByName(colNameStmt *ast.ColumnName) (bool, bool) {
	schemaName := colNameStmt.Schema.String()
	tableName := colNameStmt.Table.String()
	colName := colNameStmt.Name.String()
	tables, schemaExists := t.schemaTables[schemaName]
	if schemaExists {
		table, tableExists := tables[tableName]
		if tableExists {
			return TableExistCol(table, colName), false
		}
	}
	if schemaName != "" {
		return false, false
	}
	colExists := false
	colIsAmbiguous := false

	for _, tables := range t.schemaTables {
		table, tableExist := tables[tableName]
		if tableExist {
			exist := TableExistCol(table, colName)
			if exist {
				if colExists {
					colIsAmbiguous = true
				}
				colExists = true
			}
		}
		if tableName != "" {
			continue
		}
		for _, table := range tables {
			exist := TableExistCol(table, colName)
			if exist {
				if colExists {
					colIsAmbiguous = true
				}
				colExists = true
			}
		}
	}
	return colExists, colIsAmbiguous
}

// TableExistCol check if table has column
func TableExistCol(table *ast.CreateTableStmt, colName string) bool {
	if table == nil {
		return false
	}
	colName = strings.ToLower(colName)
	for _, col := range table.Cols {
		if col.Name.Name.L == colName {
			return true
		}
	}
	return false
}

func RestoreToSqlWithFlag(restoreFlag format.RestoreFlags, node ast.Node) (sqlStr string, err error) {
	buf := new(bytes.Buffer)
	restoreCtx := format.NewRestoreCtx(restoreFlag, buf)
	err = node.Restore(restoreCtx)
	if nil != err {
		return "", err
	}
	return buf.String(), nil
}

// Fingerprint returns the fingerprint of a SQL statement.
// query digest text
func Fingerprint(oneSql string, isCaseSensitive bool) (fingerprint string, err error) {
	stmts, _, err := parser.New().Parse(oneSql, "", "")
	if err != nil {
		return "", err
	}
	if len(stmts) != 1 {
		return "", parser.ErrSyntax
	}

	stmts[0].Accept(&FingerprintVisitor{})
	if !isCaseSensitive {
		stmts[0].Accept(&CapitalizeProcessor{
			capitalizeTableName:      true,
			capitalizeTableAliasName: true,
			capitalizeDatabaseName:   true,
		})
	}
	fingerprint, err = RestoreToSqlWithFlag(format.RestoreKeyWordUppercase|format.RestoreNameBackQuotes, stmts[0])
	if err != nil {
		return "", err
	}
	return
}

// ExtractIndexFromCreateTableStmt extract index from create table statement.
func ExtractIndexFromCreateTableStmt(table *ast.CreateTableStmt) map[string] /*index name*/ []string /*indexed column*/ {
	var result = make(map[string][]string)

	for _, constraint := range table.Constraints {
		if constraint.Tp == ast.ConstraintPrimaryKey {
			// The name of a PRIMARY KEY is always PRIMARY,
			// which thus cannot be used as the name for any other kind of index.
			result["PRIMARY"] = []string{constraint.Keys[0].Column.Name.L}
		}

		if constraint.Tp == ast.ConstraintIndex ||
			constraint.Tp == ast.ConstraintKey ||
			constraint.Tp == ast.ConstraintUniq ||
			constraint.Tp == ast.ConstraintUniqIndex ||
			constraint.Tp == ast.ConstraintUniqKey {
			for _, key := range constraint.Keys {
				result[constraint.Name] = append(result[constraint.Name], key.Column.Name.L)
			}
		}
	}
	return result
}

// match table name if input is table name
func ConvertAliasToTable(alias string, tables []*ast.TableSource) (*ast.TableName, error) {
	for _, table := range tables {
		t, ok := table.Source.(*ast.TableName)
		if !ok || t == nil {
			continue
		}

		if strings.ToLower(alias) == table.AsName.L || alias == t.Name.L {
			return t, nil
		}

		return t, nil
	}
	return nil, errors.New("can not find table")
}
