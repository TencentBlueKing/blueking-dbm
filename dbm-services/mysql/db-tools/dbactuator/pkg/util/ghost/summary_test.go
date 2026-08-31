/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package ghost

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestFormatOnlineDDLSummary(t *testing.T) {
	failures := []backendMigrationFailure{
		{
			serverName: "SPT0",
			host:       "127.0.0.2",
			port:       20000,
			dbName:     "job_execute_0",
			err:        errors.New("migration failed"),
		},
	}

	summary := formatOnlineDDLSummary(2, "job_execute", "t1", failures)

	require.Contains(t, summary, "online ddl summary: total=2 success=1 failed=1 db=job_execute table=t1")
	require.Contains(t, summary, "FAILED: SPT0(127.0.0.2:20000) db=job_execute_0 err=migration failed")
}
