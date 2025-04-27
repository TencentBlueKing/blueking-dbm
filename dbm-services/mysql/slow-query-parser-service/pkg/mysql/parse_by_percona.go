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
	"regexp"
	"strings"

	pq "github.com/percona/go-mysql/query"

	"dbm-services/common/go-pubpkg/cmutil"
)

const (
	// MAX_LENGTH_QUERY_STRING TODO
	MAX_LENGTH_QUERY_STRING = 65535
)

// parseByPercona digest
func parseByPercona(db, query string) (*Response, error) {
	pq.ReplaceNumbersInWords = false
	resp := &Response{
		QueryString: query,
		QueryLength: len(query),
	}
	digestText := pq.Fingerprint(query)
	resp.QueryDigestText = digestText
	resp.QueryDigestMd5 = pq.Id(digestText)
	resp.Command = parseCommandFromQuery(digestText)
	resp.TableReferences = parseTableNameFromQuery(db, query)

	// 优先取第一个表名
	for _, dbt := range resp.TableReferences {
		if resp.DbName == "" {
			resp.DbName = dbt.DbName
		}
		resp.TableName = dbt.TableName
		break
	}

	return resp, nil
}

// parseTableNameFromQuery TODO need unique
func parseTableNameFromQuery(db, query string) []*TableRef {
	var tables []*TableRef
	reTable := regexp.MustCompile(`(?i)(from|join|into|table)\s+([a-zA-Z0-9_.\-]+)`)
	query = strings.Replace(strings.Replace(query, "`", "", -1), "\n", "", -1)
	res := reTable.FindAllStringSubmatch(query, -1)
	var err error
	for _, dbt := range res {
		tb := &TableRef{}
		if strings.Contains(dbt[2], ".") {
			tb.DbName, tb.TableName, err = cmutil.GetDbTableName(dbt[2])
		} else {
			tb.TableName = dbt[2]
			tb.DbName = db
		}
		if err != nil {
			continue
		}

		tables = append(tables, tb)
	}
	return tables
}

func parseCommandFromQuery(query string) string {
	if len(query) > 20 {
		query = query[:20]
	}
	query = strings.ToLower(query)
	if strings.Contains(query, "select") {
		return SELECT
	} else if strings.Contains(query, "insert") {
		return INSERT
	} else if strings.Contains(query, "update") {
		return UPDATE
	} else if strings.Contains(query, "delete") {
		return DELETE
	} else if strings.Contains(query, "replace") {
		return REPLACE
	} else {
		return "other"
	}
}

const (
	SELECT               = "select"
	UPDATE               = "update"
	DELETE               = "delete"
	INSERT               = "insert"
	REPLACE              = "replace"
	CREATE_DATABASE      = "create_db"
	CREATE_TABLE         = "create_table"
	ALTER_TABLE          = "alter_table"
	DROP_DATABASE        = "drop_db"
	DROP_TABLE           = "drop_table"
	SHOW_DATABASES       = "SHOW DATABASES"
	SHOW_TABLES          = "SHOW TABLES"
	SHOW_CREATE_DATABASE = "SHOW CREATE DATABASE"
	SHOW_CREATE_TABLE    = "SHOW CREATE TABLE"
	SHOW_INDEXES         = "SHOW INDEXES"
	SHOW_VARIABLES       = "SHOW VARIABLES"
	SHOW_STATUS          = "SHOW STATUS"
	SHOW_MASTER_STATUS   = "SHOW MASTER STATUS"
	SHOW_SLAVE_STATUS    = "SHOW SLAVE STATUS"
	SHOW_PROCESSLIST     = "SHOW PROCESSLIST"
	SET                  = "SET"
	USE                  = "change_db"
	KILL                 = "KILL"
	SHUTDOWN             = "SHUTDOWN"
	EXPLAIN              = "EXPLAIN"
	DESCRIBE             = "DESCRIBE"
	HELP                 = "HELP"
	SET_PASSWORD         = "SET PASSWORD"
	FLUSH                = "FLUSH"
	RELOAD               = "RELOAD"
	REPAIR               = "REPAIR"
	OPTIMIZE             = "OPTIMIZE"
	BINLOG_DUMP          = "BINLOG_DUMP"
	BINLOG_DUMP_GTID     = "BINLOG_DUMP_GTID"
	BEGIN                = "BEGIN"
	GRANT                = "grant"
)
