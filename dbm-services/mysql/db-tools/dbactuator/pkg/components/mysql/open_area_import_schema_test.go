/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"strings"
	"testing"
)

func TestCheckImportErrFileNameLength(t *testing.T) {
	t.Parallel()

	comp := &OpenAreaImportSchemaComp{
		Params: OpenAreaImportSchemaParam{
			OpenAreaParam: []OneOpenAreaImportSchema{
				{Schema: "db1", NewDB: "db1_1001"},
			},
		},
	}
	if err := comp.checkImportErrFileNameLength(); err != nil {
		t.Fatalf("short names should pass: %v", err)
	}

	// {schema}.sql.{newdb}.new.{newdb}.{ts}.err 超限：schema=100, newdb=64
	longSchema := strings.Repeat("s", 100)
	longNewDB := strings.Repeat("d", 64)
	comp.Params.OpenAreaParam = []OneOpenAreaImportSchema{
		{Schema: longSchema, NewDB: longNewDB},
	}
	if err := comp.checkImportErrFileNameLength(); err == nil {
		t.Fatal("expected error for overlong open-area schema err file name")
	} else if !strings.Contains(err.Error(), "err log 文件名过长") {
		t.Fatalf("unexpected error: %v", err)
	}
}
