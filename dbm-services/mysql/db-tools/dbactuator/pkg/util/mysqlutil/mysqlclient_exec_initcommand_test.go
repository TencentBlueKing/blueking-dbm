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
	"strings"
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func TestCreateLoadSQLCommandDefaultHasNoInitCommand(t *testing.T) {
	t.Parallel()
	cmd := mysqlutil.ExecuteSqlAtLocal{
		MySQLBinPath: "/usr/bin/mysql",
		User:         "admin",
		Password:     "pwd",
		Host:         "127.0.0.1",
		Port:         3306,
	}.CreateLoadSQLCommand()
	if strings.Contains(cmd, "--init-command") {
		t.Fatalf("default command should not contain --init-command, got %s", cmd)
	}
	if !strings.Contains(cmd, "-vvv") {
		t.Fatalf("command should contain -vvv, got %s", cmd)
	}
	if !strings.Contains(cmd, "-h127.0.0.1") {
		t.Fatalf("tcp command should contain host, got %s", cmd)
	}
}

func TestCreateLoadSQLCommandSocketDefaultHasNoInitCommand(t *testing.T) {
	t.Parallel()
	cmd := mysqlutil.ExecuteSqlAtLocal{
		MySQLBinPath: cst.MySQLClientPath,
		User:         "admin",
		Socket:       "/tmp/mysql.sock",
	}.CreateLoadSQLCommand()
	if strings.Contains(cmd, "--init-command") {
		t.Fatalf("default socket command should not contain --init-command, got %s", cmd)
	}
	if !strings.Contains(cmd, "--socket=/tmp/mysql.sock") {
		t.Fatalf("socket command should contain socket, got %s", cmd)
	}
	if !strings.Contains(cmd, "-vvv") {
		t.Fatalf("command should contain -vvv, got %s", cmd)
	}
}

func TestCreateLoadSQLCommandForceKeepsFlag(t *testing.T) {
	t.Parallel()
	cmd := mysqlutil.ExecuteSqlAtLocal{
		MySQLBinPath: "/usr/bin/mysql",
		User:         "admin",
		Host:         "127.0.0.1",
		Port:         3306,
		IsForce:      true,
	}.CreateLoadSQLCommand()
	if !strings.Contains(cmd, " -f ") {
		t.Fatalf("force command should contain -f, got %s", cmd)
	}
}

func TestCreateLoadSQLCommandWithInitCommand(t *testing.T) {
	t.Parallel()
	cmd := mysqlutil.ExecuteSqlAtLocal{
		MySQLBinPath: "/usr/bin/mysql",
		User:         "admin",
		Host:         "127.0.0.1",
		Port:         3306,
		InitCommand:  "SET SESSION tc_admin=1",
	}.CreateLoadSQLCommand()
	want := "--init-command='SET SESSION tc_admin=1'"
	if !strings.Contains(cmd, want) {
		t.Fatalf("command should contain %s, got %s", want, cmd)
	}
	if !strings.Contains(cmd, "-vvv") {
		t.Fatalf("command should still contain -vvv, got %s", cmd)
	}
}

func TestCreateLoadSQLCommandSocketWithInitCommand(t *testing.T) {
	t.Parallel()
	cmd := mysqlutil.ExecuteSqlAtLocal{
		MySQLBinPath: cst.MySQLClientPath,
		User:         "admin",
		Socket:       "/tmp/mysql.sock",
		InitCommand:  "SET SESSION tc_admin=1",
	}.CreateLoadSQLCommand()
	if !strings.Contains(cmd, "--socket=/tmp/mysql.sock") {
		t.Fatalf("socket command should contain socket, got %s", cmd)
	}
	if !strings.Contains(cmd, "--init-command='SET SESSION tc_admin=1'") {
		t.Fatalf("socket command should contain init-command, got %s", cmd)
	}
}
