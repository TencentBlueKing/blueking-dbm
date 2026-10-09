/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const alterEngineBanPhrase = "Tendbcluster集群暂不允许 ALTER TABLE 修改存储引擎"

func TestSpiderAlterTableForbidsEngineChange(t *testing.T) {
	requireAlterTableCheckerRules(t)

	innodb := alterTableWithEngine("t1", "innodb")
	cr := innodb.spiderCheckWithClusterEngines("5.7", nil)
	require.NotNil(t, cr)
	require.Contains(t, cr.BanWarns,
		"【平台限制】：表名:t1  Tendbcluster集群暂不允许 ALTER TABLE 修改存储引擎 ENGINE=InnoDB")

	rocks := alterTableWithEngine("t1", "rocksdb")
	cr = rocks.spiderCheckWithClusterEngines("5.7", nil)
	require.NotNil(t, cr)
	require.Contains(t, cr.BanWarns,
		"【平台限制】：表名:t1  Tendbcluster集群暂不允许 ALTER TABLE 修改存储引擎 ENGINE=RocksDB")

	addCol := AlterTableResult{
		TableName: "t1",
		AlterCommands: []AlterCommand{
			{Type: AlterTypeAddColumn, ColDef: ColDef{ColName: "c1"}},
		},
	}
	cr = addCol.spiderCheckWithClusterEngines("5.7", nil)
	require.NotNil(t, cr)
	assert.NotContains(t, strings.Join(cr.BanWarns, "\n"), alterEngineBanPhrase)

	mysqlPath := alterTableWithEngine("t1", "innodb")
	cr = mysqlPath.checkWithClusterEngines("5.7", nil)
	require.NotNil(t, cr)
	assert.NotContains(t, strings.Join(cr.BanWarns, "\n"), alterEngineBanPhrase)
}

func TestSpiderCreateTableAllowsEngine(t *testing.T) {
	requireCreateTableCheckerRules(t)
	if SR == nil || SR.SpiderCreateTableRule.CreateWithSelect == nil {
		t.Skip("spider create table rules not loaded")
	}

	created := newCreateTableWithEngine("InnoDB")
	cr := created.spiderCheckWithClusterEngines("5.7", nil)
	require.NotNil(t, cr)
	assert.NotContains(t, strings.Join(cr.BanWarns, "\n"), alterEngineBanPhrase)
}

func alterTableWithEngine(tableName, engine string) AlterTableResult {
	return AlterTableResult{
		TableName: tableName,
		AlterCommands: []AlterCommand{
			{
				Type: AlterTypeTableOptions,
				TableOptions: []TableOption{
					{Key: "engine", Value: engine},
				},
			},
		},
	}
}
