/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package partitionsvr

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// PartitionBoundaryRow 单条分区在 information_schema 中的名称与边界描述
type PartitionBoundaryRow struct {
	Name           string
	DescriptionRaw string
}

// intervalCheckOffsetDays 用于分区间隔检查的时区偏移（天）。
// 仅用于定位“今天所在/之后”的分区下界，不叠加 PartitionTimeInterval：
// 新间隔变小时（如 7→1）若叠加新间隔，边界仍可能落在当前大跨度分区内，会把当前分区误判为未来分区。
const intervalCheckOffsetDays = 1

// addStmtContext 汇总“添加分区语句”构建过程中的中间态数据。
// 仅在 GetAddStatement 内部使用，用于集中管理原先分散的局部变量，提升可读性与可维护性。
type addStmtContext struct {
	descKey         string // 分区范围关键字
	boundaryExpr    string // 分区查询边界表达式
	wantedDesc      string // 查询期望的分区描述列
	wantedName      string // 查询期望的分区名列
	wantedDescIfOld string // 当现有分区过旧时的分区表达式
	wantedNameIfOld string // 当现有分区过旧时的分区名称
	begin           int    // 追加分区的起始偏移（如 -1 表示从 今天 开始）
}

func (pc *PartitionConfig) ExecuteAddStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {

	partitionStepInfo = &PartitionStepInfo{
		Step:      "add",
		Status:    true,
		Message:   "",
		Statement: "",
	}

	// TODO: 增加判断当前分区间隔是否和下发的配置间隔一致
	// 如果不一致，则需要先检查预留分区是否有数据，如果没有数据，则清理预留分区，之后再使用新的规则增加预留分区
	if pc.IntervalCheck {
		err := pc.CheckInterval(pd, conn)
		if err != nil {
			partitionStepInfo.Status = false
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}
	addStatement, err := pc.GetAddStatement(pd, conn)
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}

	if addStatement == "" {
		partitionStepInfo.Message = "No need to execute add partition statement"
		return partitionStepInfo
	}

	// 记录执行的SQL语句
	partitionStepInfo.Statement = addStatement

	// 只设置锁等待超时时间
	_, err = conn.ExecWithTimeout(
		ExecTimeout,
		fmt.Sprintf("set session lock_wait_timeout=%d; %s", LockWaitTimeout, addStatement),
	)
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}

	partitionStepInfo.Message = "success"

	return partitionStepInfo
}

func (pc *PartitionConfig) CheckInterval(pd *PartitionDetail, conn *native.DbWorker) error {
	/*
		1. 获取未来预留分区
		2. 获取未来预留分区的步长
		3. 判断步长是否和下发 PartitionTimeInterval 一致
		4. 如果一致，则返回 nil
		5. 如果不一致，则检查预留分区是否有数据
		6. 如果预留分区有数据，则返回 对应错误
		7. 如果预留分区无数据，则清理预留分区，并应用新的间隔规则
	*/

	// 获取未来预留分区
	rows, err := pc.GetPartitionsFromTodayOnward(pd, conn, intervalCheckOffsetDays)
	if err != nil {
		return fmt.Errorf("get future partitions from today onward: %w", err)
	}
	// 未来预留分区不足 2 个时，无法判定步长，也无需继续处理
	if len(rows) < 2 {
		return nil
	}
	// 相邻分区的 PARTITION_DESCRIPTION 步长与下发 PartitionTimeInterval 一致则视为检查通过
	if pc.partitionStepsMatchConfig(rows) {
		return nil
	}
	// 当前查询结果已全部是未来分区，直接全量检查这些未来分区是否有数据
	futureNames := make([]string, 0, len(rows))
	for _, r := range rows {
		futureNames = append(futureNames, r.Name)
	}
	hasData, err := pc.HasDataInPartitions(pd, conn, futureNames)
	if err != nil {
		return fmt.Errorf("check if future partitions have data: %w", err)
	}
	if hasData {
		return fmt.Errorf("Future partitions have data, cannot directly clean up and apply new interval rules. Please clean up and try again.")
	}
	// 未来预留分区无数据，直接清理
	if err = pc.CleanupFuturePartitions(pd, conn, futureNames); err != nil {
		return fmt.Errorf("cleanup future partitions: %w", err)
	}
	return nil
}

// GetPartitionsFromTodayOnward 查询当前在用分区之后的未来预留分区。
// 步骤：
//  1. 用“今天 + 时区偏移”（不叠加新间隔）定位当前在用分区；
//  2. 再取 PARTITION_DESCRIPTION 严格大于当前分区的所有分区。
//
// 这样无论新间隔变大还是变小，都不会把当前大跨度分区误判为未来分区。
func (pc *PartitionConfig) GetPartitionsFromTodayOnward(
	pd *PartitionDetail,
	conn *native.DbWorker,
	offsetDays int,
) ([]PartitionBoundaryRow, error) {

	boundaryExpr, err := pc.GetIntervalCheckBoundaryExpr(offsetDays)
	if err != nil {
		return nil, err
	}

	// 当前在用分区：边界之后（含等于）的第一个分区
	currentSQL := fmt.Sprintf(
		"SELECT "+
			"PARTITION_NAME AS PARTITION_NAME, "+
			"PARTITION_DESCRIPTION AS PARTITION_DESCRIPTION "+
			"FROM "+
			"INFORMATION_SCHEMA.PARTITIONS "+
			"WHERE "+
			"TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_DESCRIPTION >= %s "+
			"ORDER BY PARTITION_DESCRIPTION ASC LIMIT 1;", boundaryExpr)

	currentRows, err := conn.QueryWithArgs(currentSQL, pd.DbName, pd.TbName)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return nil, nil
		}
		return nil, err
	}
	if len(currentRows) == 0 {
		return nil, nil
	}
	currentDesc := currentRows[0]["PARTITION_DESCRIPTION"].(string)

	// 未来预留分区：严格晚于当前在用分区
	futureSQL :=
		"SELECT " +
			"PARTITION_NAME AS PARTITION_NAME, " +
			"PARTITION_DESCRIPTION AS PARTITION_DESCRIPTION " +
			"FROM " +
			"INFORMATION_SCHEMA.PARTITIONS " +
			"WHERE " +
			"TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_DESCRIPTION > ? " +
			"ORDER BY PARTITION_DESCRIPTION ASC;"

	rows, err := conn.QueryWithArgs(futureSQL, pd.DbName, pd.TbName, currentDesc)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return nil, nil
		}
		return nil, err
	}

	out := make([]PartitionBoundaryRow, 0, len(rows))
	for _, row := range rows {
		out = append(out, PartitionBoundaryRow{
			Name:           row["PARTITION_NAME"].(string),
			DescriptionRaw: row["PARTITION_DESCRIPTION"].(string),
		})
	}
	return out, nil
}

// GetIntervalCheckBoundaryExpr 生成“定位当前在用分区”的边界表达式。
// 仅含时区偏移（及各类型自身的 DiffOneDay），不叠加 PartitionTimeInterval。
func (pc *PartitionConfig) GetIntervalCheckBoundaryExpr(offsetDays int) (string, error) {
	if offsetDays < 0 {
		return "", fmt.Errorf("offsetDays must be >= 0")
	}

	switch pc.PartitionType {
	case 0:
		return fmt.Sprintf("(TO_DAYS(now())+%d)", DiffOneDay+offsetDays), nil
	case 1:
		// type 1 3  name和description是同一天，但是list类型 不需要额外再加一天
		return fmt.Sprintf("(TO_DAYS(now())+%d)", offsetDays), nil
	case 3:
		return fmt.Sprintf("DATE_FORMAT(date_add(now(),interval %d day),'%%Y%%m%%d')", offsetDays), nil
	case 101:
		// name和description是同一天，例如20060102的数据实际在p20060103中，所以需要额外加1天
		return fmt.Sprintf("DATE_FORMAT(date_add(now(),interval %d day),'%%Y%%m%%d')", DiffOneDay+offsetDays), nil
	case 4:
		//  description 为 'YYYY-MM-DD'
		return fmt.Sprintf(`DATE_FORMAT(date_add(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, DiffOneDay+offsetDays), nil
	case 5, 6:
		return fmt.Sprintf("UNIX_TIMESTAMP(date_add(curdate(),INTERVAL %d DAY))", DiffOneDay+offsetDays), nil
	default:
		return "", errno.NotSupportedPartitionType
	}
}

// partitionStepsMatchConfig 校验相邻分区 PARTITION_DESCRIPTION 的步长是否等于下发的 PartitionTimeInterval（按各分区类型的语义）。
func (pc *PartitionConfig) partitionStepsMatchConfig(rows []PartitionBoundaryRow) bool {
	if len(rows) < 2 || pc.PartitionTimeInterval <= 0 {
		return false
	}
	for i := 0; i < len(rows)-1; i++ {
		if !pc.partitionStepMatches(rows[i].DescriptionRaw, rows[i+1].DescriptionRaw) {
			return false
		}
	}
	return true
}

func (pc *PartitionConfig) partitionStepMatches(desc1, desc2 string) bool {
	switch pc.PartitionType {
	case 0, 1:
		v1, err1 := strconv.Atoi(strings.TrimSpace(desc1))
		v2, err2 := strconv.Atoi(strings.TrimSpace(desc2))
		if err1 != nil || err2 != nil {
			return false
		}
		return v2-v1 == pc.PartitionTimeInterval
	case 5, 6:
		v1, err1 := strconv.ParseInt(strings.TrimSpace(desc1), 10, 64)
		v2, err2 := strconv.ParseInt(strings.TrimSpace(desc2), 10, 64)
		if err1 != nil || err2 != nil {
			return false
		}
		exp := int64(pc.PartitionTimeInterval) * 86400
		return v2-v1 == exp
	case 3, 101:
		d1, err1 := time.Parse("20060102", strings.TrimSpace(desc1))
		d2, err2 := time.Parse("20060102", strings.TrimSpace(desc2))
		if err1 != nil || err2 != nil {
			return false
		}
		days := int(d2.Sub(d1).Hours() / 24)
		return days == pc.PartitionTimeInterval
	case 4:
		d1, err1 := parsePartitionDescType4(desc1)
		d2, err2 := parsePartitionDescType4(desc2)
		if err1 != nil || err2 != nil {
			return false
		}
		days := int(d2.Sub(d1).Hours() / 24)
		return days == pc.PartitionTimeInterval
	default:
		return false
	}
}

func parsePartitionDescType4(raw string) (time.Time, error) {
	s := strings.TrimSpace(raw)
	s = strings.Trim(s, "'\"")
	return time.ParseInLocation("2006-01-02", s, time.Local)
}

// HasDataInPartitions 判断指定分区列表中是否存在数据。
// 返回 true 表示至少一个分区有数据，false 表示均无数据。
func (pc *PartitionConfig) HasDataInPartitions(
	pd *PartitionDetail,
	conn *native.DbWorker,
	partitionNames []string,
) (bool, error) {
	dbName := strings.ReplaceAll(pd.DbName, "`", "``")
	tbName := strings.ReplaceAll(pd.TbName, "`", "``")

	for _, partitionName := range partitionNames {
		safePartitionName := strings.ReplaceAll(partitionName, "`", "``")
		querySQL := fmt.Sprintf(
			"SELECT 1 "+
				"FROM `%s`.`%s` PARTITION (`%s`) "+
				"LIMIT 1;",
			dbName, tbName, safePartitionName,
		)

		_, err := conn.Query(querySQL)
		if err != nil {
			if strings.Contains(err.Error(), "not row found") {
				continue
			}
			return false, err
		}
		// 查询到任意一行数据，说明该分区有数据
		return true, nil
	}
	return false, nil
}

// CleanupFuturePartitions 清理指定未来预留分区。
func (pc *PartitionConfig) CleanupFuturePartitions(
	pd *PartitionDetail,
	conn *native.DbWorker,
	partitionNames []string,
) error {
	if len(partitionNames) == 0 {
		return nil
	}

	dbName := strings.ReplaceAll(pd.DbName, "`", "``")
	tbName := strings.ReplaceAll(pd.TbName, "`", "``")
	quoted := make([]string, 0, len(partitionNames))
	for _, name := range partitionNames {
		safeName := strings.ReplaceAll(name, "`", "``")
		quoted = append(quoted, fmt.Sprintf("`%s`", safeName))
	}

	dropSQL := fmt.Sprintf(
		"ALTER TABLE `%s`.`%s` DROP PARTITION %s",
		dbName, tbName, strings.Join(quoted, ","),
	)
	_, err := conn.ExecWithTimeout(
		ExecTimeout,
		fmt.Sprintf("set session lock_wait_timeout=%d; %s", LockWaitTimeout, dropSQL),
	)
	return err
}

func (pc *PartitionConfig) GetAddStatement(pd *PartitionDetail, conn *native.DbWorker) (string, error) {

	var querySQL, addSql, name string
	var desc int

	addStmtCtx, err := GetAddStmtCtx(pc.PartitionType)

	if err != nil {
		return addSql, err
	}

	// 可存储今日数据的分区是一个预留分区
	querySQL = fmt.Sprintf(
		"SELECT "+
			"COUNT(*) AS COUNT "+
			"FROM "+
			"INFORMATION_SCHEMA.PARTITIONS "+
			"WHERE "+
			"TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_DESCRIPTION >= %s", addStmtCtx.boundaryExpr)
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)

	// 如果是not row found，是因为未来没有新的分区，是需要添加的
	// COUNT(*) AS COUNT一定返回1条数据，即使查询不到，返回结果也是count=0
	if err != nil {
		return addSql, err
	}

	cnt, _ := strconv.Atoi(rows[0]["COUNT"].(string))
	// 是否需要添加分区
	if cnt >= pc.ExtraPartition {
		return addSql, nil
	}
	need := pc.ExtraPartition - cnt
	// 先获取当前最大的分区PARTITION_DESCRIPTION和PARTITION_NAME
	querySQL = fmt.Sprintf(
		"SELECT "+
			"%s %s , PARTITION_NAME AS PARTITION_NAME "+
			"FROM "+
			"INFORMATION_SCHEMA.PARTITIONS "+
			"WHERE "+
			"TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_DESCRIPTION >= %s "+
			"ORDER BY PARTITION_DESCRIPTION DESC LIMIT 1;", addStmtCtx.wantedDesc, addStmtCtx.wantedName, addStmtCtx.boundaryExpr)
	// QueryWithArgs会将占位符替换为实际值，注意只能是字符串
	rows, err = conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)

	// 是分区表单查询不到，可能分区过旧
	if err != nil && !strings.Contains(err.Error(), "not row found") {
		return addSql, err
	}
	// 表是分区表，但是已有的分区过旧，以至于不能包含今天或者未来的分区，添加能包含今天数据的分区
	if len(rows) == 0 {
		addStmtCtx.begin = -1
		querySQL = fmt.Sprintf(`select %s %s;`, addStmtCtx.wantedDescIfOld, addStmtCtx.wantedNameIfOld)

		rows, err = conn.Query(querySQL)

		if err != nil {
			return addSql, err
		}
		name = rows[0]["WANTED_NAME"].(string)
	} else {
		name = rows[0]["WANTED_NAME"].(string)
		current := strings.TrimPrefix(rows[0]["PARTITION_NAME"].(string), "p")
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return addSql, err
		}
		// 如果计算出希望创建的分区名比当前分区的名称还要小1天，并且分区间隔只有1天，则分区名会重复
		if formatDate.AddDate(0, 0, 1).Format("20060102") == current {
			name = current
		}
	}

	switch pc.PartitionType {
	case 0, 1, 5, 6:
		desc, _ = strconv.Atoi(rows[0]["WANTED_DESC"].(string))
		addSql, err = pc.NewPartitionNameDescType0Type1Type5(addStmtCtx.begin, need, name, desc, addStmtCtx.descKey)
	case 3, 101:
		addSql, err = pc.NewPartitionNameDescType3Type101(addStmtCtx.begin, need, name, addStmtCtx.descKey)
	case 4:
		addSql, err = pc.NewPartitionNameDescType4(addStmtCtx.begin, need, name, addStmtCtx.descKey)
	default:
		return addSql, errno.NotSupportedPartitionType
	}

	if err != nil {
		return addSql, err
	}

	addSql = fmt.Sprintf("alter table `%s`.`%s`  add partition( %s", pd.DbName, pd.TbName, addSql)

	return addSql, nil
}

func GetAddStmtCtx(partitionType int) (ctx *addStmtContext, err error) {
	ctx = &addStmtContext{}
	var diff int
	// 0 5 101是常规分区类型
	switch partitionType {
	case 0:
		diff = DiffOneDay
		ctx.descKey = "less than"
		ctx.boundaryExpr = fmt.Sprintf(`(TO_DAYS(now())+%d) `, diff)
		ctx.wantedDesc = "partition_description as WANTED_DESC,"
		ctx.wantedName = fmt.Sprintf(`DATE_FORMAT(from_days(PARTITION_DESCRIPTION-%d),'%%Y%%m%%d')  as WANTED_NAME`, diff)
		ctx.wantedDescIfOld = fmt.Sprintf(`(TO_DAYS(now())+%d) as WANTED_DESC,`, diff)
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 1:
		ctx.descKey = "in"
		ctx.boundaryExpr = "TO_DAYS(now())"
		ctx.wantedDesc = "partition_description as WANTED_DESC,"
		ctx.wantedName = "DATE_FORMAT(from_days(PARTITION_DESCRIPTION),'%Y%m%d')  as WANTED_NAME"
		ctx.wantedDescIfOld = "(TO_DAYS(now())) as WANTED_DESC,`"
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 3:
		ctx.descKey = "in"
		ctx.boundaryExpr = "DATE_FORMAT(now(),'%Y%m%d')"
		ctx.wantedName = "partition_description as WANTED_NAME"
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 101:
		// 101类型分区，分区名和desc同一天，但是desc为今天，不能算在预留分区个数中，因为【less than 今天】存储的是历史数据，所以diff为1
		// 101类型的diff只用于确定边界表达式，不用来生成新的分区名称
		diff = DiffOneDay
		ctx.descKey = "less than"
		ctx.boundaryExpr = fmt.Sprintf(`DATE_FORMAT(date_add(now(),interval %d day),'%%Y%%m%%d')`, diff)
		ctx.wantedName = "partition_description as WANTED_NAME"
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 4:
		diff = DiffOneDay
		ctx.descKey = "less than"
		ctx.boundaryExpr = fmt.Sprintf(`DATE_FORMAT(date_add(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, diff)
		ctx.wantedName = fmt.Sprintf(
			`DATE_FORMAT(date_sub(replace(partition_description,'\'',''),interval %d day),'%%Y%%m%%d') as WANTED_NAME`, diff)
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 5, 6:
		diff = DiffOneDay
		ctx.descKey = "less than"
		ctx.boundaryExpr = fmt.Sprintf(`UNIX_TIMESTAMP(date_add(curdate(),INTERVAL %d DAY))`, diff)
		ctx.wantedDesc = "partition_description as WANTED_DESC,"
		ctx.wantedName = fmt.Sprintf(
			`DATE_FORMAT(date_sub(from_unixtime(partition_description),interval %d day),'%%Y%%m%%d') as WANTED_NAME`, diff)
		ctx.wantedDescIfOld = fmt.Sprintf(`UNIX_TIMESTAMP(DATE_ADD(curdate(),INTERVAL %d DAY)) as WANTED_DESC,`, diff)
		ctx.wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	default:
		return ctx, errno.NotSupportedPartitionType
	}
	return ctx, nil
}

func (pc *PartitionConfig) NewPartitionNameDescType0Type1Type5(begin int, need int, name string, desc int,
	descKey string) (string, error) {
	var newdesc, ratio int
	var newname, sql string
	ratio = 1
	if pc.PartitionType == 5 || pc.PartitionType == 6 {
		ratio = 86400
	}
	for i := begin; i < need; i++ {
		// 生成分区description
		newdesc = desc + (i+1)*pc.PartitionTimeInterval*ratio
		// 生成分区名
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*pc.PartitionTimeInterval).Format("20060102")
		sql = fmt.Sprintf("%s partition `p%s`  values %s (%d),", sql, newname, descKey, newdesc)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}

func (pc *PartitionConfig) NewPartitionNameDescType3Type101(begin int, need int, name string, descKey string) (string, error) {
	var newname, sql string
	for i := begin; i < need; i++ {
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*pc.PartitionTimeInterval).Format("20060102")
		sql = fmt.Sprintf("%s partition `p%s` values %s (%s),", sql, newname, descKey, newname)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}

func (pc *PartitionConfig) NewPartitionNameDescType4(begin int, need int, name string, descKey string) (string, error) {
	var newname, newdesc, sql string
	for i := begin; i < need; i++ {
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*pc.PartitionTimeInterval).Format("20060102")
		newdesc = formatDate.AddDate(0, 0, (i+2)*pc.PartitionTimeInterval).Format("'2006-01-02'")
		sql = fmt.Sprintf("%s partition `p%s`  values %s (%s),", sql, newname, descKey, newdesc)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}
