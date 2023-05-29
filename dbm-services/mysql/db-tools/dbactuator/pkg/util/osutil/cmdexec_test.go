/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package osutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func TestExecShellCommand(t *testing.T) {
	t.Log("start..")
	out, err := osutil.StandardShellCommand(false, "usermod -d /home/mysql  mysql")
	if err != nil {
		t.Fatal(err)
	}
	t.Log(out)
}

func TestComplexCommand(t *testing.T) {
	t.Log("start test complex command")
	c := osutil.ComplexCommand{
		Command:     "mysqlcheck  -uxx -pxx  --check-upgrade --grace-print --all-databases --skip-write-binlog ",
		Logger:      false,
		WriteStdout: true,
		StdoutFile:  "./test.out",
	}
	if err := c.Run(); err != nil {
		t.Fatal(err.Error())
	}
	t.Log("end test complex command")
}
