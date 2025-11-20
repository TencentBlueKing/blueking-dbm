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
	if len(list) == 0 {
		return defaultVal
	}
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

// IsDbMatched 是否匹配，先匹配白名单，再匹配黑名单
// 1. 不在白名单中，则不匹配
// 2. 在白名单中，且不在黑名单中，则匹配
// 3. 在白名单中，且在黑名单中，则不匹配
func (f *NsFilter) IsDbMatched(db string) bool {
	// 不在白名单中
	if !isMatch(f.WhiteDbList, db, true) {
		return false
	}

	// 在白名单中，且又在黑名单中，则不匹配
	if isMatch(f.BlackDbList, db, false) {
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

// FilterTb 过滤表名 Deprecated
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

// inWhiteList 判断表名是否在白名单中
func (f *NsFilter) inWhiteList(db, tb string) bool {
	dbInWhiteList := isMatch(f.WhiteDbList, db, true)
	tbInWhiteList := isMatch(f.WhiteTbList, tb, true)
	return dbInWhiteList && tbInWhiteList
}

// inBlackList 判断表名是否在黑名单中
func (f *NsFilter) inBlackList(db, tb string) bool {
	dbInBlackList := isMatch(f.BlackDbList, db, false)
	tbInBlackList := isMatch(f.BlackTbList, tb, false)
	return dbInBlackList && tbInBlackList
}

// FilterTbV2 过滤表名
// 1. 数据库中的库, 先用 db_patterns 获取目标列表, 再用 ignore_dbs 排除忽略库
// 2. 在上一步剩下的库中, 用 table_patterns 和 ignore_tables 做表选择
func (f *NsFilter) FilterTbV2(db string, tbList []string) (matchList, notMatchList []string) {
	if !f.IsDbMatched(db) {
		return nil, tbList
	}

	for _, tb := range tbList {
		if f.isTbMatched(db, tb) {
			matchList = append(matchList, tb)
		} else {
			notMatchList = append(notMatchList, tb)
		}
	}

	return
}

// FilterTbV2_Cartesian 笛卡尔积过滤表名. 目前不使用
func (f *NsFilter) FilterTbV2_Cartesian(db string, tbList []string) (matchList, notMatchList []string) {

	for _, tb := range tbList {
		v1 := f.inWhiteList(db, tb)
		v2 := f.inBlackList(db, tb)
		if v1 && !v2 {
			matchList = append(matchList, tb)
		} else {
			notMatchList = append(notMatchList, tb)
		}
	}

	return
}
