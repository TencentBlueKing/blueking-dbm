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
	case 0, 1, 5:
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
	case 5:
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
	if pc.PartitionType == 5 {
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
