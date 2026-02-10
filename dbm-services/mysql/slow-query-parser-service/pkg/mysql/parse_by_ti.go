package mysql

import (
	"regexp"
	"strconv"
	"strings"

	pq "github.com/percona/go-mysql/query"
	"github.com/pingcap/tidb/pkg/parser"
	"github.com/pingcap/tidb/pkg/parser/ast"
	"github.com/pingcap/tidb/pkg/parser/format"

	"dbm-services/mysql/slow-query-parser-service/pkg/tiparser"
)

// replace Multi Values to ?+
// values(?,?,?),(?,?,?) to (?+/*omitted N items ...*/)
// in (?,?,?,?) to (?+/*omitted N items ...*/)
var replaceMultiValues = regexp.MustCompile(`\(\?(,\?|\),\(\?)+\)`)

// replaceMultiValuesWithCount 替换多值占位符，并添加数量注释
// 例如: (?,?,?) -> (?+/*omitted 3 items ...*/), 但返回两个版本
// 注意：ReplaceAllStringFunc 会对每个匹配项分别调用回调函数，
// 所以对于 "col1 IN (?,?,?) AND col2 IN (?,?)" 这样的 SQL，
// 会分别匹配两次，第一次 match="(?,?,?)" count=3，第二次 match="(?,?)" count=2
func replaceMultiValuesWithCount(fingerprint string) (withComment, forHash string) {
	// 用于计算哈希的版本，不包含注释
	forHash = replaceMultiValues.ReplaceAllString(fingerprint, "(?+)")
	if strings.Count(fingerprint, "?") < 100 {
		return forHash, forHash
	}
	// 当检测到 ? 的数量大于 100 时，显示/*omitted N items ...*/
	withComment = replaceMultiValues.ReplaceAllStringFunc(fingerprint, func(match string) string {
		// 计算当前匹配项中的问号数量（不是整个 SQL 的问号总数）
		count := strings.Count(match, "?")
		return "(?+/*omitted " + strconv.Itoa(count) + " items ...*/)"
	})

	return withComment, forHash
}

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

	// 生成两个版本：一个带注释（用于显示），一个不带注释（用于计算MD5）
	fingerprintWithComment, fingerprintForHash := replaceMultiValuesWithCount(fingerprint)

	resp := &Response{
		QueryString: oneSql, // do not return original sql
		// remove # Time:
		QueryLength:     len(oneSql),
		QueryDigestText: fingerprintWithComment,                     // 使用带注释的版本
		QueryDigestMd5:  strings.ToLower(pq.Id(fingerprintForHash)), // 使用不带注释的版本计算MD5
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
