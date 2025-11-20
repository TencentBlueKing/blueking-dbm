// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/samber/lo"
)

// QueryMycnfConfig 查询 mysqld 的参数
func QueryMycnfConfig(variables []string, db *sqlx.DB) (map[string]interface{}, error) {
	inCause := lo.Map(variables, func(item string, _ int) string {
		return strconv.Quote(item)
	})
	sqlStr := fmt.Sprintf(`show global variables where variable_name in (%s)`, strings.Join(inCause, ","))
	res := make(map[string]interface{})
	type row struct {
		VariableName string `json:"variable_name" db:"Variable_name"`
		Value        string `json:"value" db:"Value"`
	}
	var rows []row
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	err := db.SelectContext(ctx, &rows, sqlStr)
	if err != nil {
		return nil, err
	}
	for _, r := range rows {
		res[r.VariableName] = r.Value
	}
	return res, err
}
