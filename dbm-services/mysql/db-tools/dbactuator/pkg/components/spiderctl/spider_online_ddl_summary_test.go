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
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestFormatSpiderSchemaApplySummary(t *testing.T) {
	failures := []schemaApplyFailure{
		{name: "SPIDER0", host: "127.0.0.10", port: 25000, err: errors.New("ddl failed")},
	}

	summary := formatSchemaApplySummary("spider", 2, "job_execute", failures)

	require.Equal(
		t,
		"spider schema apply summary: total=2 success=1 failed=1 db=job_execute\n"+
			"  FAILED: SPIDER0(127.0.0.10:25000) err=ddl failed",
		summary,
	)
}

func TestFormatTdbctlSchemaApplySummary(t *testing.T) {
	failures := []schemaApplyFailure{
		{name: "TDBCTL", host: "127.0.0.20", port: 26000, err: errors.New("execute failed")},
	}

	summary := formatSchemaApplySummary("tdbctl", 1, "job_execute", failures)

	require.Equal(
		t,
		"tdbctl schema apply summary: total=1 success=0 failed=1 db=job_execute\n"+
			"  FAILED: TDBCTL(127.0.0.20:26000) err=execute failed",
		summary,
	)
}

func TestFormatTendbClusterOnlineDDLSummary(t *testing.T) {
	layers := map[onlineDDLLayer]layerExecution{
		backendLayer: {status: layerSuccess, total: 2},
		spiderLayer:  {status: layerFailed, total: 2, err: errors.New("SPIDER0 failed")},
		tdbctlLayer:  {status: layerNotRun},
	}

	summary := formatTendbClusterOnlineDDLSummary(
		"job_execute",
		"task",
		"alter table task add column c int",
		layers,
	)

	require.Equal(
		t,
		"tendbcluster online ddl summary:\n"+
			"  database=job_execute\n"+
			"  table=task\n"+
			"  statement=alter table task add column c int\n"+
			"  backend: SUCCESS total=2\n"+
			"  spider: FAILED total=2\n"+
			"  tdbctl: NOT_RUN\n"+
			"  FAILED: spider err=SPIDER0 failed",
		summary,
	)
}
