/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package ghost_test

import (
	"testing"

	"github.com/stretchr/testify/require"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/ghost"
)

func TestParseDDL(t *testing.T) {
	var ss []string
	ss, err := ghost.ParseDDL("ALTER TABLE `dbm`.`t1` ADD COLUMN `c1` varchar(255) NOT NULL DEFAULT ''")
	require.NoError(t, err)
	require.Equal(t, []string{"add column c1 varchar(255) not null default ''"}, ss)
	ss, err = ghost.ParseDDL("ALTER TABLE `dbm`.`t1` ADD COLUMN `c1` varchar(255), add index `idx1` (`c1`)")
	require.NoError(t, err)
	require.Equal(t, []string{"add column c1 varchar(255)", "add key idx1 (c1)"}, ss)
	ss, err = ghost.ParseDDL("ALTER TABLE t1 engine=innodb;")
	require.NoError(t, err)
	require.Equal(t, []string{"engine innodb"}, ss)
}

func TestParseSQLFile(t *testing.T) {
	// nolint
	sqlContent := `alter table t1 add column c1 int(11) not null default '';alter table db1.t3 add addr varchar(100);`
	ss, err := ghost.ParseSQLFile(sqlContent)
	require.NoError(t, err)
	require.Len(t, ss, 2)
	require.Equal(t, "alter table t1 add column c1 int(11) not null default ''", ss[0])
	require.Equal(t, "alter table db1.t3 add addr varchar(100)", ss[1])
}

func TestParseTable(t *testing.T) {
	testStatement := "alter table db1.t1 add c1 int(11)"
	db, tb, err := ghost.ParseSqlSchemaInfo(testStatement)
	require.NoError(t, err)
	require.Equal(t, db, `db1`)
	require.Equal(t, tb, `t1`)
	testStatement = "alter table `db1.c1`.`t1.t3`"
	db, tb, err = ghost.ParseSqlSchemaInfo(testStatement)
	require.NoError(t, err)
	require.Equal(t, db, `db1.c1`)
	require.Equal(t, tb, `t1.t3`)
	testStatement = "alter table `t1` add c3 int(11)"
	db, tb, err = ghost.ParseSqlSchemaInfo(testStatement)
	require.NoError(t, err)
	require.Equal(t, db, "")
	require.Equal(t, tb, `t1`)
}
