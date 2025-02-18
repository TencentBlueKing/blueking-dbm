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

	"github.com/github/gh-ost/go/logic"
	"github.com/stretchr/testify/require"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/ghost"
)

func TestGhostMigrator(t *testing.T) {
	ds := ghost.DataSource{
		Host:     "",
		Port:     3306,
		User:     "",
		Password: "",
	}
	// nolint
	ddlStatments := []string{"alter table t1 add c11 int(11);"}
	True := true
	migrationContext, err := ghost.NewMigrationContext(ds, ghost.UserGhostFlag{
		AllowOnMaster: &True,
	}, 1, 0, "test", "t1", ddlStatments, false)
	require.NoError(t, err)
	migrator := logic.NewMigrator(migrationContext, "bb")
	err = migrator.Migrate()
	require.NoError(t, err)
}
