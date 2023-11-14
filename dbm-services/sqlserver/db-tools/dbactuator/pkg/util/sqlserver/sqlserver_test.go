/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver_test

import (
	"fmt"
	"testing"

	mssql "github.com/denisenkom/go-mssqldb"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

func Test(t *testing.T) {

	checkCmd := "select password_hash from master.sys.sql_logins"

	type LoginInfo struct {
		PasswordHash mssql.VarChar `db:"password_hash"`
	}
	var dbWork *sqlserver.DbWorker
	var err error
	if dbWork, err = sqlserver.NewDbWorker(
		"xxx",
		"xxx!",
		"xxx",
		1433,
	); err != nil {
		t.Log(err)
		return
	}
	var getJobs []LoginInfo
	if err := dbWork.Queryxs(&getJobs, checkCmd); err != nil {
		t.Log(err)
		return
	}
	fmt.Printf("%+v\n", getJobs)

}
