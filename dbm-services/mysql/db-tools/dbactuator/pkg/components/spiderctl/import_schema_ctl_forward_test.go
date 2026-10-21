/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRewriteCreateTableIfNotExists(t *testing.T) {
	raw := "" +
		"CREATE TABLE `orders` (\n" +
		"  `id` int(11) NOT NULL,\n" +
		"  PRIMARY KEY (`id`)\n" +
		") ENGINE=InnoDB DEFAULT CHARSET=utf8;\n" +
		"CREATE TABLE IF NOT EXISTS `users` (\n" +
		"  `id` int(11) NOT NULL\n" +
		") ENGINE=InnoDB;\n" +
		"CREATE TABLESPACE `ts1` ADD DATAFILE 'ts1.ibd';\n"

	got := rewriteCreateTableIfNotExists(raw)

	require.Contains(t, got, "CREATE TABLE IF NOT EXISTS `orders` (")
	require.Equal(t, 1, strings.Count(got, "CREATE TABLE IF NOT EXISTS `users` ("))
	require.NotContains(t, got, "CREATE TABLE IF NOT EXISTS IF NOT EXISTS")
	require.Contains(t, got, "  `id` int(11) NOT NULL,")
	require.Contains(t, got, "CREATE TABLESPACE `ts1` ADD DATAFILE 'ts1.ibd';")
}

func TestRewriteCreateTableKeepsVersionComment(t *testing.T) {
	raw := "/*!50001 CREATE TABLE `v` (\n  `id` int\n);\n"
	got := rewriteCreateTableIfNotExists(raw)
	require.Equal(t, raw, got)
}

func TestPrepareCtlForwardSchemaFileRejectsDropTable(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "db_0.sql")
	raw := "CREATE TABLE `orders` (\n  `id` int\n);\nDROP TABLE `orders`;\n"
	require.NoError(t, os.WriteFile(path, []byte(raw), 0o644))

	err := prepareCtlForwardSchemaFile(path)
	require.Error(t, err)

	left, readErr := os.ReadFile(path)
	require.NoError(t, readErr)
	require.Equal(t, raw, string(left))
}

func TestChooseDumpDbsDisasterRecoverIgnoresPartialSpiderList(t *testing.T) {
	got, err := chooseDumpDbs(true, []string{"game"}, []string{"game", "log"}, nil)
	require.NoError(t, err)
	require.Equal(t, []string{"game", "log"}, got)
}

func TestChooseDumpDbsDisasterRecoverFailsWhenShard0Empty(t *testing.T) {
	got, err := chooseDumpDbs(true, []string{"game"}, nil, nil)
	require.Error(t, err)
	require.Nil(t, got)
}

func TestChooseDumpDbsDisasterRecoverFailsWhenShard0Unreachable(t *testing.T) {
	backendErr := errors.New("connect backend shard0: refused")
	got, err := chooseDumpDbs(true, []string{"game"}, nil, backendErr)
	require.ErrorIs(t, err, backendErr)
	require.Nil(t, got)
}

func TestCreateDatabaseSQLQuotesHyphenatedName(t *testing.T) {
	got := createDatabaseSQL(true, "order-center", "utf8mb4")
	require.Contains(t, got, "CREATE DATABASE IF NOT EXISTS `order-center`")
	require.NotContains(t, got, "CREATE DATABASE IF NOT EXISTS order-center ")

	plain := createDatabaseSQL(false, "order", "utf8")
	require.Contains(t, plain, "CREATE DATABASE `order`")
	require.NotContains(t, plain, "IF NOT EXISTS")
}

func TestCreateDatabaseSQLEscapesBacktick(t *testing.T) {
	got := createDatabaseSQL(true, "a`b", "utf8")
	require.Contains(t, got, "CREATE DATABASE IF NOT EXISTS `a``b`")
}

func TestChooseDumpDbsAppendDeployKeepsSpiderList(t *testing.T) {
	got, err := chooseDumpDbs(false, []string{"game"}, []string{"game", "log"}, errors.New("should not be used"))
	require.NoError(t, err)
	require.Equal(t, []string{"game"}, got)
}

func TestPrepareCtlForwardSchemaFileRejectsCommentedDrop(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "db_0.sql")
	raw := "/*!50001 DROP TABLE IF EXISTS `orders`*/;\nCREATE TABLE `orders` (\n  `id` int\n);\n"
	require.NoError(t, os.WriteFile(path, []byte(raw), 0o644))

	err := prepareCtlForwardSchemaFile(path)
	require.Error(t, err)
}
