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
	"testing"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"

	_ "github.com/denisenkom/go-mssqldb"
)

func Test(t *testing.T) {
	checkCmd := "SELECT count(0) FROM SYS.SYSPROCESSES WHERE 1!=1"

	var dbWork *sqlserver.DbWorker
	var err error
	var cnt int
	if dbWork, err = sqlserver.NewDbWorker(
		"xxx",
		"xxx",
		"xxx",
		1433,
	); err != nil {
		t.Log(err)
		return
	}
	// 到最后回收db连接
	defer dbWork.Stop()

	if err := dbWork.Queryxs(&cnt, checkCmd); err != nil {
		t.Log(err)
	}
	t.Log(cnt)

}
