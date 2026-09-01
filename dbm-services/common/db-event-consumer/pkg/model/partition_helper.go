// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
)

// BuildMysqlPartitionClause 生成 MySQL 按天分区的 SQL 子句
// 使用 to_days(dateColumn) 做 RANGE 分区
// 默认创建前后各 30 天的分区
func BuildMysqlPartitionClause(dateColumn string) string {
	timeNow := time.Now()
	partitionsPreCreated := []string{}
	for i := -7; i < 30; i++ {
		days := cmutil.TimeToDays(timeNow.AddDate(0, 0, i))
		dateint := cast.ToInt(timeNow.AddDate(0, 0, i).Format("20060102"))
		partitionsPreCreated = append(partitionsPreCreated,
			fmt.Sprintf("PARTITION p%d VALUES LESS THAN (%d) ENGINE = InnoDB", dateint, days+1))
	}
	partitionInfo := []string{
		fmt.Sprintf("/*!50100 PARTITION BY RANGE (to_days(`%s`))", dateColumn),
		"(",
		strings.Join(partitionsPreCreated, ",\n"),
		")",
		"*/",
	}
	return strings.Join(partitionInfo, "\n")
}
