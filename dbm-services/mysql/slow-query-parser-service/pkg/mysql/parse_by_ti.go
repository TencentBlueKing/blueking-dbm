package mysql

import (
	"regexp"
	"strings"

	pq "github.com/percona/go-mysql/query"
	"github.com/pingcap/tidb/pkg/parser"
	"github.com/pingcap/tidb/pkg/parser/ast"
	"github.com/pingcap/tidb/pkg/parser/format"

	"dbm-services/mysql/slow-query-parser-service/pkg/tiparser"
)

// replace Multi Values to ?+
// values(?,?,?),(?,?,?) to (?+)
// in (?,?,?,?) to (?+)
var replaceMultiValues = regexp.MustCompile(`\(\?(,\?|\),\(\?)+\)`) // .ReplaceAllString("", "(?+")

// AnalyzeSql 解析sql
// 计算指纹
// 获取表名
// 获取 sql 类型
func AnalyzeSql(db, oneSql string) (*Response, error) {
	stmts, _, err := parser.New().Parse(oneSql, "", "")
	if err != nil {
		return parseByPercona(db, oneSql) // percona 正则替换的方式
		//return nil, err
	}
	if len(stmts) != 1 {
		return nil, parser.ErrSyntax
	}

	tableNames := &tiparser.TableNameExtractor{TableNames: make(map[string]*ast.TableName)}
	sqlCommands := &tiparser.SqlCommandVisitor{}
	stmts[0].Accept(&tiparser.FingerprintVisitor{})
	stmts[0].Accept(tableNames)
	stmts[0].Accept(sqlCommands)
	fingerprint, err := tiparser.RestoreToSqlWithFlag(format.RestoreKeyWordUppercase|format.RestoreNameBackQuotes,
		stmts[0])
	if err != nil {
		return nil, err
	}

	fingerprint = replaceMultiValues.ReplaceAllString(fingerprint, "(?+)")
	resp := &Response{
		QueryString:     oneSql,
		QueryLength:     len(oneSql),
		QueryDigestText: fingerprint,
		QueryDigestMd5:  strings.ToLower(pq.Id(fingerprint)),
	}
	for _, tableName := range tableNames.TableNames {
		tableRef := &TableRef{tableName.Schema.O, tableName.Name.O}
		if tableRef.DbName == "" {
			tableRef.DbName = db
		}
		resp.TableReferences = append(resp.TableReferences, tableRef)
	}
	resp.Command = strings.Join(sqlCommands.CommandName, ",")
	// fmt.Println("xxxx", resp.Command, resp.TableReferences)
	// 优先取第一个表名
	for _, dbt := range resp.TableReferences {
		if resp.DbName == "" {
			resp.DbName = dbt.DbName
		}
		resp.TableName = dbt.TableName
		break
	}
	return resp, nil
}
