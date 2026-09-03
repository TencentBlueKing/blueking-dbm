/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import "strings"

// analysisIrrelevantColumns 选机匹配完全不读这些列。
// Agent 用 SELECT * 时会看见它们，并按字面意思编造失败原因（例如把 1970 的 consume_time
// 当成“从未空闲/不可用”，把 is_idle=0 当成“机器不空闲”）。这些分析没有意义。
var analysisIrrelevantColumns = map[string]string{
	"consume_time": "只在机器被申请选中并落账后才更新；默认 1970-01-01 08:00:01（Unix 0）表示从未被消费，Unused 资源几乎都是这个值，不是匹配条件",
	"is_init":      "导入侧是否做过初始化的标记，选机 SQL 不读，json 也不对外暴露",
	"is_idle":      "导入侧是否做过空闲检查的标记，不是“机器当前是否空闲”；选机只看 status=Unused",
}

const analysisIrrelevantWarning = `consume_time / is_init / is_idle 不是选机条件，禁止当作申请失败原因。` +
	`consume_time 只在机器被选取落账后才更新；1970-01-01 08:00:01 表示从未被消费，Unused 机器几乎都是这个值，不表示被锁定。` +
	`is_idle=0 不表示机器不空闲，is_init=0 不表示机器未就绪。可用状态只看 status=Unused 和 gse_agent_status_code。` +
	`只有失败现场层级是 cas 时才允许谈并发抢占，禁止从 consume_time 反推锁定。`

func appendAnalysisWarning(existing, extra string) string {
	if extra == "" {
		return existing
	}
	if existing == "" {
		return extra
	}
	if strings.Contains(existing, extra) {
		return existing
	}
	return existing + "；" + extra
}

func isAnalysisIrrelevantColumn(name string) bool {
	_, ok := analysisIrrelevantColumns[strings.ToLower(name)]
	return ok
}

func sqlMentionsIrrelevantColumns(sql string) bool {
	upper := strings.ToUpper(sql)
	for col := range analysisIrrelevantColumns {
		if strings.Contains(upper, strings.ToUpper(col)) {
			return true
		}
	}
	return false
}

func stripIrrelevantColumns(columns []string, rows []interface{}) (filteredCols []string, filteredRows []interface{}, stripped bool) {
	for _, col := range columns {
		if isAnalysisIrrelevantColumn(col) {
			stripped = true
			continue
		}
		filteredCols = append(filteredCols, col)
	}
	if !stripped {
		return columns, rows, false
	}
	for _, row := range rows {
		m, ok := row.(map[string]interface{})
		if !ok {
			filteredRows = append(filteredRows, row)
			continue
		}
		clean := make(map[string]interface{}, len(m))
		for k, v := range m {
			if !isAnalysisIrrelevantColumn(k) {
				clean[k] = v
			}
		}
		filteredRows = append(filteredRows, clean)
	}
	return filteredCols, filteredRows, true
}
