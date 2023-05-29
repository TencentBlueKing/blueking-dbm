package logical

import (
	"regexp"
	"strings"
)

// NsFilter 用于过滤库名和表名
type NsFilter struct {
	WhiteDbList []string
	BlackDbList []string
	WhiteTbList []string
	BlackTbList []string
}

// NewNsFilter 创建一个NsFilter
// 1. 长度允许为空
// whiteList中，值为空值，表示匹配全部
// blackList中，值为空值，表示不匹配任何
// 2. 正则表达式
func NewNsFilter(whiteDbList, blackDbList, whiteTbList, blackTbList []string) *NsFilter {
	v := &NsFilter{
		WhiteDbList: whiteDbList,
		BlackDbList: blackDbList,
		WhiteTbList: whiteTbList,
		BlackTbList: blackTbList,
	}

	return v

}

/*
	isMatch 判断name是否匹配list

有 * 时，把*替换成.*，作正则匹配
无 * 时，直接比较 大小写敏感.
注： mongodb中，不会存在A和a两个库，创建了A库，a库创建会失败。但可以存在A和a两个表
*/
func isMatch(list []string, name string, defaultVal bool) bool {
	for _, item := range list {
		// 空值，白名单返回true，黑名单返回false
		if item == "" {
			return defaultVal
		}
		if strings.Contains(item, "*") {
			item = "^" + strings.ReplaceAll(item, "*", ".*")
			if m, err := regexp.MatchString(item, name); err == nil && m {
				return true
			}
		} else if item == name {
			return true
		}
	}
	return false
}

// IsDbMatched 是否匹配
// 如果不在白名单中
func (f *NsFilter) IsDbMatched(db string) bool {
	// 空的白名单，表示全部匹配
	if len(f.WhiteDbList) > 0 && !isMatch(f.WhiteDbList, db, true) {
		return false
	}

	// 空的黑名单，表示全部不匹配
	if len(f.BlackDbList) > 0 && isMatch(f.BlackDbList, db, false) {
		return false
	}
	return true
}

func (f *NsFilter) isTbMatched(db, tb string) bool {
	if len(f.WhiteTbList) > 0 && !isMatch(f.WhiteTbList, tb, true) {
		return false
	}
	if len(f.BlackTbList) > 0 && isMatch(f.BlackTbList, tb, false) {
		return false
	}
	return true
}

// FilterDb 过滤库名
// 返回匹配和不匹配的库名
func (f *NsFilter) FilterDb(dbList []string) (matchList, notMatchList []string) {
	for _, db := range dbList {
		if f.IsDbMatched(db) {
			matchList = append(matchList, db)
		} else {
			notMatchList = append(notMatchList, db)
		}
	}
	return
}

// FilterTb 过滤表名
func (f *NsFilter) FilterTb(tbList []string) (matchList, notMatchList []string) {
	for _, tb := range tbList {
		if f.isTbMatched("", tb) {
			matchList = append(matchList, tb)
		} else {
			notMatchList = append(notMatchList, tb)
		}
	}
	return
}
