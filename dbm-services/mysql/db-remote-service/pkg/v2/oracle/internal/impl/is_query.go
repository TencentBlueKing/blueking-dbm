package impl

import (
	"regexp"
	"strings"
)

// Oracle RPC 只提供只读查询能力:
//   - 只放行以 SELECT / WITH 开头的语句 (允许前导空白和注释)
//   - 拒绝 SELECT ... FOR UPDATE (会加行锁)
//
// 注意: 这里只是第一道防线. 真正的只读保证依赖数据库账号权限
// (ORACLE_SYS_READ_USER 只应授予 CREATE SESSION / SELECT_CATALOG_ROLE 等只读权限),
// 因为 SELECT 中调用的函数仍可能通过自治事务产生写入.
var (
	leadingCommentsRe = regexp.MustCompile(`^(?s)(\s+|/\*.*?\*/|--[^\n]*(\n|$))*`)
	forUpdateRe       = regexp.MustCompile(`(?is)\bfor\s+update\b`)
)

// NormalizeCommand 去掉首尾空白和结尾分号 (Oracle 驱动执行单条语句时结尾带分号会报 ORA-00911)
func NormalizeCommand(cmd string) string {
	s := strings.TrimSpace(cmd)
	for strings.HasSuffix(s, ";") {
		s = strings.TrimSpace(strings.TrimSuffix(s, ";"))
	}
	return s
}

// IsReadOnlyQuery 判断是否为允许执行的只读查询
func IsReadOnlyQuery(cmd string) bool {
	body := cmd
	if loc := leadingCommentsRe.FindStringIndex(cmd); loc != nil {
		body = cmd[loc[1]:]
	}
	lower := strings.ToLower(body)
	if !hasKeywordPrefix(lower, "select") && !hasKeywordPrefix(lower, "with") {
		return false
	}
	return !forUpdateRe.MatchString(body)
}

func hasKeywordPrefix(s, kw string) bool {
	if !strings.HasPrefix(s, kw) {
		return false
	}
	if len(s) == len(kw) {
		return true
	}
	switch s[len(kw)] {
	case ' ', '\t', '\n', '\r', '(', '*', '/':
		return true
	}
	return false
}
