package pkg

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// ResourceKeywords 是 MySQL 语句中可能出现的资源限制关键字。
// 顺序与 ResourceRegexps 一一对应，也与 ResourceLimits 结构体字段对应。
var ResourceKeywords = []string{
	"MAX_QUERIES_PER_HOUR",
	"MAX_UPDATES_PER_HOUR",
	"MAX_CONNECTIONS_PER_HOUR",
	"MAX_USER_CONNECTIONS",
}

// ResourceRegexps 是 ResourceKeywords 对应的预编译正则，用于从 WITH 子句中提取资源限制值。
var ResourceRegexps []*regexp.Regexp

func init() {
	ResourceRegexps = make([]*regexp.Regexp, len(ResourceKeywords))
	for i, kw := range ResourceKeywords {
		ResourceRegexps[i] = regexp.MustCompile(`(?i)` + kw + `\s+(\d+)`)
	}
}

// ResourceLimits 表示 MySQL 账号的 4 种资源限制。
type ResourceLimits struct {
	MaxQuestions   int
	MaxUpdates     int
	MaxConnections int
	MaxUserConns   int
}

// Merge 将 other 中的非零值合并到当前 ResourceLimits 中。
// 用于从多条 GRANT 语句中累积同一用户的资源限制。
func (rl ResourceLimits) Merge(other ResourceLimits) ResourceLimits {
	if other.MaxQuestions > 0 {
		rl.MaxQuestions = other.MaxQuestions
	}
	if other.MaxUpdates > 0 {
		rl.MaxUpdates = other.MaxUpdates
	}
	if other.MaxConnections > 0 {
		rl.MaxConnections = other.MaxConnections
	}
	if other.MaxUserConns > 0 {
		rl.MaxUserConns = other.MaxUserConns
	}
	return rl
}

// FormatWithClause 将资源限制格式化为 SQL 的 WITH 子句。
// 如果所有限制均为 0，返回空字符串。
func (rl ResourceLimits) FormatWithClause() string {
	var parts []string
	if rl.MaxQuestions > 0 {
		parts = append(parts, fmt.Sprintf("MAX_QUERIES_PER_HOUR %d", rl.MaxQuestions))
	}
	if rl.MaxUpdates > 0 {
		parts = append(parts, fmt.Sprintf("MAX_UPDATES_PER_HOUR %d", rl.MaxUpdates))
	}
	if rl.MaxConnections > 0 {
		parts = append(parts, fmt.Sprintf("MAX_CONNECTIONS_PER_HOUR %d", rl.MaxConnections))
	}
	if rl.MaxUserConns > 0 {
		parts = append(parts, fmt.Sprintf("MAX_USER_CONNECTIONS %d", rl.MaxUserConns))
	}
	if len(parts) == 0 {
		return ""
	}
	return " WITH " + strings.Join(parts, " ")
}

// ParseResourceLimits 从 SQL 语句的尾部（rest）中提取资源限制值。
// 未出现的关键字对应值为 0（MySQL 默认）。
func ParseResourceLimits(rest string) ResourceLimits {
	var rl ResourceLimits
	for i, re := range ResourceRegexps {
		m := re.FindStringSubmatch(rest)
		if m == nil {
			continue
		}
		val, _ := strconv.Atoi(m[1])
		switch i {
		case 0:
			rl.MaxQuestions = val
		case 1:
			rl.MaxUpdates = val
		case 2:
			rl.MaxConnections = val
		case 3:
			rl.MaxUserConns = val
		}
	}
	return rl
}
