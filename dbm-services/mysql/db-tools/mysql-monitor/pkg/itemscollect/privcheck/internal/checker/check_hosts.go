package checker

import (
	"fmt"
	"slices"
	"strings"

	"golang.org/x/exp/maps"
)

func (c *Analyzer) checkHosts(username string, hostSummaries map[string]*hostPrivSummary) (res []*PrivErrorInfo) {
	for _, hostSummary := range hostSummaries {
		res = append(res, c.checkHost(username, hostSummary)...)
	}

	return res
}

func (c *Analyzer) checkHost(username string, hostSummary *hostPrivSummary) (res []*PrivErrorInfo) {
	if len(hostSummary.DBPrivSummaries) <= 1 {
		return nil
	}

	for _, pair := range FindPatternCover(maps.Keys(hostSummary.DBPrivSummaries)) {
		//if !c.deep {
		//	res = append(
		//		res,
		//		fmt.Sprintf("%s@%s db conflict: %v", username, hostSummary.Host, pair),
		//	)
		//}
		if ok, r := compareDBSummary(
			username, hostSummary.Host, hostSummary.Host,
			hostSummary.DBPrivSummaries[pair[0]],
			hostSummary.DBPrivSummaries[pair[1]],
		); !ok {
			res = append(res, r...)
		}
	}

	return res
}

/*
dbname 不同的权限明细对比
1. with grant option 对比
2. 表明细对比
  - 表名
  - 权限
*/
func compareDBSummary(username, host0, host1 string, ds0, ds1 *dbPrivSummary) (ok bool, res []*PrivErrorInfo) {
	if ds0.WithGrantOption != ds1.WithGrantOption {
		res = append(
			res,
			&PrivErrorInfo{
				ErrorType: PrivErrorWithGrantOptionNotMatch,
				Object1:   fmt.Sprintf("'%s'@'%s' to `%s`", username, host0, ds0.DBName),
				Object2:   fmt.Sprintf("'%s'@'%s' to `%s`", username, host1, ds1.DBName),
				Msg:       fmt.Sprintf(`with grant option not match`),
			},
		)
	}

	tbs0 := maps.Keys(ds0.TablePrivSummaries)
	tbs1 := maps.Keys(ds1.TablePrivSummaries)
	slices.Sort(tbs0)
	slices.Sort(tbs1)
	// 表明细不一致
	if !slices.Equal(tbs0, tbs1) {
		res = append(
			res,
			&PrivErrorInfo{
				ErrorType: PrivErrorGrantToDifferentTable,
				Object1:   fmt.Sprintf("'%s'@'%s' to `%s`", username, host0, ds0.DBName),
				Object2:   fmt.Sprintf("'%s'@'%s' to `%s`", username, host1, ds1.DBName),
				Msg: fmt.Sprintf(
					"[`%s`] != [`%s`]",
					strings.Join(tbs0, "`, `"),
					strings.Join(tbs1, "`, `"),
				),
			},
		)
	}

	// 表名一样的部分对比权限
	for _, tbName := range intersectStringSlice(tbs0, tbs1) {
		p0 := ds0.TablePrivSummaries[tbName].Privileges
		p1 := ds1.TablePrivSummaries[tbName].Privileges
		slices.Sort(p0)
		slices.Sort(p1)
		if !slices.Equal(p0, p1) {
			res = append(
				res,
				&PrivErrorInfo{
					ErrorType: PrivErrorPrivilegesNotMatch,
					Object1:   fmt.Sprintf("'%s'@'%s' to `%s`.`%s`", username, host0, ds0.DBName, tbName),
					Object2:   fmt.Sprintf("'%s'@'%s' to `%s`.`%s`", username, host1, ds1.DBName, tbName),
					Msg: fmt.Sprintf(
						"['%s'] != ['%s']",
						strings.Join(p0, "', '"),
						strings.Join(p1, "', '"),
					),
				},
			)
		}
	}

	return len(res) == 0, res
}
