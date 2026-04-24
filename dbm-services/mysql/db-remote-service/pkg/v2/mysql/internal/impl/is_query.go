package impl

import (
	"regexp"
	"slices"
	"strings"
)

// queryCmds 以这些关键字开头的 SQL 走 query 路径 (返回 rows), 其余走 execute 路径 (返回 RowsAffected).
var queryCmds = []string{
	"use",
	"explain",
	"select",
	"show",
	"desc",
}

// 提到包级避免每次调用重编
var (
	splitWordsPattern    = regexp.MustCompile(`\s+`)
	tdbctlExecutePattern = regexp.MustCompile(`(?mi)^.*execute\s+['"](.*)['"]$`)
)

// IsQueryCommand 判断一条 SQL 应该走 query 还是 execute 路径.
//
// 特殊处理 tdbctl 的子命令: tdbctl get/show 是 query, tdbctl connect ... execute '<sql>'
// 需要按内嵌的真实 SQL 二次判断.
func IsQueryCommand(command string) bool {
	words := splitWordsPattern.Split(strings.TrimSpace(command), -1)
	if len(words) == 0 || words[0] == "" {
		return false
	}

	firstWord := strings.ToLower(words[0])
	if firstWord == "tdbctl" {
		return isTDBCTLQuery(words, command)
	}

	return slices.Index(queryCmds, firstWord) >= 0
}

// isTDBCTLQuery 判断 tdbctl 子命令是否是 query 类
// words 已经是切分后的结果, command 用于 connect ... execute '<sql>' 模式的二次匹配
func isTDBCTLQuery(words []string, command string) bool {
	// tdbctl 后必须至少跟一个子命令; 否则按非 query 处理, 让上层走 execute 路径报真正的 SQL 错
	if len(words) < 2 {
		return false
	}

	secondWord := strings.ToLower(words[1])
	switch secondWord {
	case "get", "show":
		return true
	case "connect":
		matches := tdbctlExecutePattern.FindStringSubmatch(command)
		if len(matches) < 2 {
			return false
		}
		return IsQueryCommand(matches[1])
	default:
		return false
	}
}
