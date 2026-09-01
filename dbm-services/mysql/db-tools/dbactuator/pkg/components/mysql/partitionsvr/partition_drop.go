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
	"fmt"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// ExecuteDropStatement 生成并输出目标表的删除过期分区语句。
// 根据分区配置与表现状调用 GetDropStatement 构造 DROP PARTITION 语句，
// 当前实现仅打印语句，实际执行可按需接入。
// 参数：
//   - pd: 目标库表分区信息
//   - conn: 数据库连接
func (pc *PartitionConfig) ExecuteDropStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {

	partitionStepInfo = &PartitionStepInfo{
		Step:      "drop",
		Status:    true,
		Message:   "",
		Statement: "",
	}

	if pc.Phase != "online" {
		partitionStepInfo.Message = "Phase is off, no need to execute drop partition statement"
		return partitionStepInfo
	}

	dropStatement, err := pc.GetDropStatement(pd, conn)

	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}

	if dropStatement == "" {
		partitionStepInfo.Message = "No need to execute drop partition statement"
		return partitionStepInfo
	}
	// 记录执行的SQL语句
	partitionStepInfo.Statement = dropStatement

	// 这里超时退出只是执行退出，mysql内连接无法释放
	// 先设置会话级超时时间为60秒
	_, err = conn.ExecWithTimeout(
		ExecTimeout,
		fmt.Sprintf("set session lock_wait_timeout=%d; %s", LockWaitTimeout, dropStatement),
	)

	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	partitionStepInfo.Message = "success"

	return partitionStepInfo
}

func (pc *PartitionConfig) GetDropStatement(pd *PartitionDetail, conn *native.DbWorker) (string, error) {

	var querySQL, dropSql, boundaryExpr string
	// 保留时间+1天，考虑时区差异引起的时间计算不稳定
	// reserve := pc.ReservedPartition*pc.PartitionTimeInterval + 1
	reserve := pc.ExpireTime + 1
	switch pc.PartitionType {
	case 0:
		boundaryExpr = fmt.Sprintf(`(TO_DAYS(now())-%d) `, reserve-DiffOneDay)
	case 1:
		boundaryExpr = fmt.Sprintf(`(TO_DAYS(now())-%d) `, reserve)
	case 3:
		boundaryExpr = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'%%Y%%m%%d')`, reserve)
	case 101:
		// 101类型分区，分区名和desc不相差一天，但是用了less than
		boundaryExpr = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'%%Y%%m%%d')`, reserve-DiffOneDay)
	case 4:
		boundaryExpr = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, reserve-DiffOneDay)
	case 5, 6:
		boundaryExpr = fmt.Sprintf(`UNIX_TIMESTAMP(date_sub(curdate(),INTERVAL %d DAY))`, reserve-DiffOneDay)
	default:
		return dropSql, errno.NotSupportedPartitionType
	}

	querySQL = fmt.Sprintf(
		"SELECT "+
			"PARTITION_NAME AS PARTITION_NAME "+
			"FROM "+
			"INFORMATION_SCHEMA.PARTITIONS "+
			"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? "+
			"AND PARTITION_DESCRIPTION < %s "+
			"ORDER BY PARTITION_DESCRIPTION ASC", boundaryExpr)

	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return dropSql, nil
		}
		return dropSql, fmt.Errorf("error occurred while checking partition info: %s", err.Error())
	}

	// 分区名称格式为p20130101 p年月日格式
	reg := regexp.MustCompile(fmt.Sprintf("^%s$", "p[0-9]{8}"))

	var expired []string
	for _, row := range rows {
		name := row["PARTITION_NAME"].(string)
		if reg.MatchString(name) {
			expired = append(expired, name)
		} else {
			return dropSql, fmt.Errorf("partition_name [%s] not like 'p20130101', "+
				"not created by partition system, can't be dropped", name)
		}
	}
	if len(expired) != 0 {
		dropSql = fmt.Sprintf("alter table `%s`.`%s` drop partition %s", pd.DbName, pd.TbName, strings.Join(expired, ","))
	}
	return dropSql, nil
}
