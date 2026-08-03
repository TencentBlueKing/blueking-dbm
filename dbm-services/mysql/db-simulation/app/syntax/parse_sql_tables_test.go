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
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseIncludeTableLines(t *testing.T) {
	workdir := t.TempDir()
	sqlFile := "sample.sql"
	outName := sqlFile + ".json"
	content := "" +
		`{"query_id":1,"command":"change_db","db_name":"db1","table_name":"","error_line":0}` + "\n" +
		`{"query_id":2,"command":"update","db_name":"db1","table_name":"t1","error_line":0}` + "\n" +
		`{"query_id":3,"command":"delete","db_name":"","table_name":"t2","error_line":0}` + "\n"
	require.NoError(t, os.WriteFile(filepath.Join(workdir, outName), []byte(content), 0600))

	tp := &TmysqlParse{
		BaseWorkdir: workdir,
		tmpWorkdir:  workdir,
	}
	queries, err := tp.parseIncludeTableLines(sqlFile, "")
	require.NoError(t, err)
	require.Len(t, queries, 3)
	assert.Equal(t, "change_db", queries[0].Command)
	assert.Equal(t, "db1", queries[0].DbName)
	assert.Equal(t, "update", queries[1].Command)
	assert.Equal(t, "t1", queries[1].TableName)
	assert.Equal(t, "delete", queries[2].Command)
	assert.Equal(t, "t2", queries[2].TableName)
}
