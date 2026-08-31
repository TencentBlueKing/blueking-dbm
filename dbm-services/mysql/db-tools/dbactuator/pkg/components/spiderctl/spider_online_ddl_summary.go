/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"fmt"
	"strings"
)

type schemaApplyFailure struct {
	name string
	host string
	port int
	err  error
}

func formatSchemaApplySummary(layer string, total int, db string, failures []schemaApplyFailure) string {
	var summary strings.Builder
	fmt.Fprintf(
		&summary,
		"%s schema apply summary: total=%d success=%d failed=%d db=%s",
		layer,
		total,
		total-len(failures),
		len(failures),
		db,
	)
	for _, failure := range failures {
		fmt.Fprintf(
			&summary,
			"\n  FAILED: %s(%s:%d) err=%v",
			failure.name,
			failure.host,
			failure.port,
			failure.err,
		)
	}
	return summary.String()
}

type layerStatus string

const (
	layerSuccess layerStatus = "SUCCESS"
	layerFailed  layerStatus = "FAILED"
	layerNotRun  layerStatus = "NOT_RUN"
)

type onlineDDLLayer string

const (
	backendLayer onlineDDLLayer = "backend"
	spiderLayer  onlineDDLLayer = "spider"
	tdbctlLayer  onlineDDLLayer = "tdbctl"
)

var onlineDDLLayerOrder = []onlineDDLLayer{backendLayer, spiderLayer, tdbctlLayer}

type layerExecution struct {
	status layerStatus
	total  int
	err    error
}

func formatTendbClusterOnlineDDLSummary(
	db string,
	table string,
	statement string,
	layers map[onlineDDLLayer]layerExecution,
) string {
	var summary strings.Builder
	fmt.Fprintf(
		&summary,
		"tendbcluster online ddl summary:\n  database=%s\n  table=%s\n  statement=%s",
		db,
		table,
		statement,
	)
	for _, layer := range onlineDDLLayerOrder {
		execution := layers[layer]
		fmt.Fprintf(&summary, "\n  %s: %s", layer, execution.status)
		if execution.status != layerNotRun {
			fmt.Fprintf(&summary, " total=%d", execution.total)
		}
	}
	for _, layer := range onlineDDLLayerOrder {
		execution := layers[layer]
		if execution.status == layerFailed {
			fmt.Fprintf(&summary, "\n  FAILED: %s err=%v", layer, execution.err)
		}
	}
	return summary.String()
}
