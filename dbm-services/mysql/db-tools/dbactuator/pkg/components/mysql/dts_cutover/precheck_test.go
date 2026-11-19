/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"strings"
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/dtsutil"

	"github.com/stretchr/testify/require"
)

func TestPreCheckSourceConnectFailFast(t *testing.T) {
	c := &Comp{Params: &Params{
		DtsMasterAddr: "127.0.0.2:18301",
		TaskName:      "task-a",
		SourceEndpoints: []dtsutil.Endpoint{
			{Host: "127.0.0.1", Port: 1, User: "u", Password: "p", SourceName: "src1"},
			{Host: "127.0.0.1", Port: 2, User: "u", Password: "p", SourceName: "src2"},
		},
		SyncScope:      &dtsutil.SyncScope{DoDBs: []string{"app"}, DoTables: []dtsutil.TableItem{{Schema: "*", Table: "*"}}},
		ChecksumPassed: true,
	}}
	err := c.PreCheck()
	require.Error(t, err)
	require.Contains(t, err.Error(), "预检连接源端")
	require.Contains(t, err.Error(), "src1")
	require.False(t, strings.Contains(err.Error(), "src2"), "fail-fast 不应继续到第二源")
}
