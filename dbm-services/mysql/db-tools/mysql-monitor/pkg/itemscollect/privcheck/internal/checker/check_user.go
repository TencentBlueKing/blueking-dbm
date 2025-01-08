package checker

import (
	"fmt"
	"slices"
	"strings"

	"golang.org/x/exp/maps"
)

func (c *Analyzer) checkUser(userSummary *userPrivSummary) (res []*PrivErrorInfo) {
	conflictHosts := FindPatternCover(maps.Keys(userSummary.HostPrivSummaries))

	for _, pair := range conflictHosts {
		if ok, msg := compareHostSummary(
			userSummary.Username,
			userSummary.HostPrivSummaries[pair[0]],
			userSummary.HostPrivSummaries[pair[1]],
		); !ok {
			res = append(res, msg...)
		}
	}

	res = append(res, c.checkHosts(userSummary.Username, userSummary.HostPrivSummaries)...)

	return res
}

/*
host 不同的权限明细对吧
1. 密码
2. db 明细对比
*/
func compareHostSummary(username string, hs0, hs1 *hostPrivSummary) (ok bool, res []*PrivErrorInfo) {
	if hs0.Password != hs1.Password {
		res = append(res, &PrivErrorInfo{
			ErrorType: PrivErrorPasswordNotMatch,
			Object1:   fmt.Sprintf(`'%s'@'%s'`, username, hs0.Host),
			Object2:   fmt.Sprintf(`'%s'@'%s'`, username, hs1.Host),
			Msg:       fmt.Sprintf(`'%s' != '%s'`, hs0.Password, hs1.Password),
		})
	}

	dbs0 := maps.Keys(hs0.DBPrivSummaries)
	dbs1 := maps.Keys(hs1.DBPrivSummaries)
	slices.Sort(dbs0)
	slices.Sort(dbs1)

	// 库明细不一致
	if !slices.Equal(dbs0, dbs1) {
		res = append(
			res,
			&PrivErrorInfo{
				ErrorType: PrivErrorGrantToDifferentDB,
				Object1:   fmt.Sprintf(`'%s'@'%s'`, username, hs0.Host),
				Object2:   fmt.Sprintf(`'%s'@'%s'`, username, hs1.Host),
				Msg: fmt.Sprintf(
					"[`%s`] != [`%s`]",
					strings.Join(dbs0, "`, `"),
					strings.Join(dbs1, "`, `"),
				),
			},
		)
	}

	for _, dbName := range intersectStringSlice(dbs0, dbs1) {
		if ok, r := compareDBSummary(
			username,
			hs0.Host,
			hs1.Host,
			hs0.DBPrivSummaries[dbName],
			hs1.DBPrivSummaries[dbName],
		); !ok {
			res = append(res, r...)
		}
	}

	return len(res) == 0, res
}
