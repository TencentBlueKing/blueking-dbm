/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil_test

import (
	"database/sql"
	"fmt"
	"sync"
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"

	_ "github.com/go-sql-driver/mysql"
)

func TestExcutePartitionByMySQLClient(t *testing.T) {
	host := "1.1.1.1"
	port := 20000
	user := "xfan"
	pwd := "xfan"
	param := ""
	tcpdsn := fmt.Sprintf("%s:%d", host, port)
	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s)/?charset=utf8&parseTime=True&loc=Local&timeout=30s&readTimeout=30s&lock_wait_timeout=5%s", user,
		pwd,
		tcpdsn, param,
	)
	sqlDB, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatal("数据库连接失败！", err.Error())
	}
	partitionsql := "alter table `db1`.`tb1` drop partition p20230217,p20230218,p20230219,p20230220"
	lock := &sync.Mutex{}
	e := mysqlutil.ExecuteSqlAtLocal{
		WorkDir: "/data/install/partition",
		ErrFile: "partitionTest.err",
	}
	err = e.ExcutePartitionByMySQLClient(sqlDB, partitionsql, lock)
	if err != nil {
		t.Fatal("分区执行失败！", err.Error())
	}
	t.Log("分区执行成功！")
}

func TestExcuteInitPartition(t *testing.T) {
	e := mysqlutil.ExecuteSqlAtLocal{
		ErrFile: "/data/install/partition/partitionTest.err",
	}
	sql := "--alter \"partition by RANGE (TO_DAYS(b)) (partition p20230221 values less than (to_days('2023-02-22')))\" D=db1,t=tb000 --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=0 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_db1_tb000 --execute"
	command := fmt.Sprintf("%s/%s %s", cst.DBAToolkitPath, "percona-toolkit-3.5.0", sql)
	err := e.ExcuteCommand(command)
	if err != nil {
		t.Fatal("初始化分区失败！", err.Error())
	}
	t.Log("初始化分区成功！")
}

func TestExcuteCommand(t *testing.T) {
	e := mysqlutil.ExecuteSqlAtLocal{
		ErrFile: "/data/install/partition/commandTest.err",
	}
	command := "df -h"
	err := e.ExcuteCommand(command)
	if err != nil {
		t.Fatal("命令执行失败！", err.Error())
	}
	t.Log("命令执行成功！")
}
