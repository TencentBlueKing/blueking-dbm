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
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"fmt"
	"strings"

	"github.com/spf13/cast"
)

const PT_MAX_ROWS int64 = 10000000                 // 1000万行
const PT_MAX_SIZE int64 = 200 * 1024 * 1024 * 1024 // 200GB

func (c *PartitionExecComp) GetAllDbTbRealName() {
	// Confs是一个结构体指针类型的切片，如果是值类型，循环拿出来的是值拷贝
	// for _, conf := range c.Params.Configs {
	// 	// 这里可以加一个并发
	// 	err := conf.GetOneDbTbRealName(c.Conn)
	// 	if err != nil {
	// 		fmt.Println(err.Error())
	// 		logger.Error(err.Error())
	// 		conf.ErrorLog = append(conf.ErrorLog, err)
	// 		continue
	// 	}
	// }

}

// GetOneDbTbRealName 根据dbLike tbLike获取真实库表名称，以及当前是否是分区表
func GetOneDbTbRealInfo(conn *native.DbWorker, dbLike string, tbLike string) (partitionDetails []*PartitionDetail, err error) {
	// 如果sql成功执行，返回值中一定会有CREATE_OPTIONS字段

	// 公共部分
	baseQuerySQL := `
		SELECT
			TABLE_SCHEMA AS TABLE_SCHEMA,
			TABLE_NAME AS TABLE_NAME,
			CREATE_OPTIONS AS CREATE_OPTIONS
		FROM
			information_schema.TABLES
		WHERE
	`
	var querySQL string
	// 判断 dblike 和 tblike 是否包含 %
	dbLikeHasWildcard := strings.Contains(dbLike, "%")
	tbLikeHasWildcard := strings.Contains(tbLike, "%")

	switch {
	case dbLikeHasWildcard && tbLikeHasWildcard:
		querySQL = baseQuerySQL + "TABLE_SCHEMA LIKE ? AND TABLE_NAME LIKE ?"
	case dbLikeHasWildcard && !tbLikeHasWildcard:
		querySQL = baseQuerySQL + "TABLE_SCHEMA LIKE ? AND TABLE_NAME = ?"
	case !dbLikeHasWildcard && tbLikeHasWildcard:
		querySQL = baseQuerySQL + "TABLE_SCHEMA = ? AND TABLE_NAME LIKE ?"
	default:
		querySQL = baseQuerySQL + "TABLE_SCHEMA = ? AND TABLE_NAME = ?"
	}

	rows, err := conn.QueryWithArgs(querySQL, dbLike, tbLike)
	if err != nil {
		return nil, fmt.Errorf("target database:%s, table:%s may not exist! Error: %v", dbLike, tbLike, err)
	}

	// 遍历dbLike tbLike查询到的结果集，获取每个库表的分区信息
	for _, row := range rows {
		pd := PartitionDetail{}
		pd.DbName = row["TABLE_SCHEMA"].(string)
		pd.TbName = row["TABLE_NAME"].(string)
		pd.IsPartitioned = pd.CheckPartitioned(row["CREATE_OPTIONS"])
		partitionDetails = append(partitionDetails, &pd)
	}
	return partitionDetails, nil
}

// CheckCurrPartInfo
func (pc *PartitionConfig) CheckCurrPartInfo(conn *native.DbWorker, partitionDetails []*PartitionDetail) (err error) {
	for _, pd := range partitionDetails {
		partInfo, err := pd.GetCurrPartInfo(conn)
		if err != nil {
			return fmt.Errorf("%s.%s, ErrorInfo is: %s", pd.DbName, pd.TbName, err.Error())
		}
		fmt.Println(partInfo)
	}

	return nil
}

// GetCurrPartInfo 获取当前目标表的分区信息 用来判断分区配置是否变化 是否需要重新初始化分区表
// 以单个具体的库表为维度
func (pd *PartitionDetail) GetCurrPartInfo(conn *native.DbWorker) (partInfo *PartitionInfo, err error) {
	partInfo = &PartitionInfo{}

	querySQL := `
		SELECT
			PARTITION_EXPRESSION AS PARTITION_EXPRESSION,
			PARTITION_METHOD AS PARTITION_METHOD,
			PARTITION_NAME AS PARTITION_NAME
		FROM
			information_schema.PARTITIONS
		WHERE
			TABLE_SCHEMA = ? AND TABLE_NAME = ?
		ORDER BY PARTITION_DESCRIPTION ASC
		LIMIT 2;`

	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)

	if err != nil {
		return nil, err
	}

	for _, row := range rows {
		fmt.Println(row)
	}

	return partInfo, nil
}

func (pd *PartitionDetail) CheckUniqueKey(conn *native.DbWorker) (err error) {
	querySQL := `
		SELECT
			DISTINCT TABLE_SCHEMA AS TABLE_SCHEMA,
			TABLE_NAME AS TABLE_NAME
		FROM
			information_schema.TABLE_CONSTRAINTS
		WHERE
			TABLE_SCHEMA = ? AND TABLE_NAME = ? AND CONSTRAINT_TYPE IN ('UNIQUE', 'PRIMARY KEY');`
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil && !strings.Contains(err.Error(), "not row found") {
		return fmt.Errorf("mysql connection or query error: %v", err)
	}

	if len(rows) == 0 {
		pd.HasUniqueKey = false
	} else {
		pd.HasUniqueKey = true
	}
	return nil

}

func (pd *PartitionDetail) CheckPartitioned(createOpt interface{}) bool {
	return strings.Contains(createOpt.(string), "partitioned")
}

func (pd *PartitionDetail) CheckTableSize(conn *native.DbWorker) (err error) {
	querySQL := `
		SELECT 
			TABLE_ROWS, 
			(DATA_LENGTH + INDEX_LENGTH) AS BYTES
		FROM 
			information_schema.tables 
		WHERE 
			TABLE_SCHEMA = ? 
			AND TABLE_NAME = ?`
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil {
		return fmt.Errorf("error occurred while checking table size: %s", err.Error())
	}
	if len(rows) == 0 {
		return fmt.Errorf("table does not exist. error: %v", err)
	}
	tableRows := cast.ToInt64(rows[0]["TABLE_ROWS"])

	tableBytes := cast.ToInt64(rows[0]["BYTES"])

	if !(tableRows < PT_MAX_ROWS && tableBytes < PT_MAX_SIZE) {
		return fmt.Errorf("table size exceeds partitioning limit: rows=%d (max=%d), bytes=%d (max=%d)", tableRows, PT_MAX_ROWS, tableBytes, PT_MAX_SIZE)
	}

	return nil
}
