/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package tscc TODO
package tscc

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var name = "spider-table-schema-consistency"

// 记录未执行检查的表
var schemas = []string{
	`create table if not exists infodba_schema.tscc_pending_execute_tbl(
		db  varchar(64) NOT NULL DEFAULT '',
		tbl varchar(64) NOT NULL,
		create_time datetime DEFAULT NULL,
		PRIMARY KEY (db,tbl)
	);`,
	`CREATE TABLE if not exists infodba_schema.tscc_schema_checksum(
		db char(64) NOT NULL,
		tbl char(64) NOT NULL,
		status char(32) NOT NULL DEFAULT "" COMMENT "检查结果,一致:ok,不一致:inconsistent",
		checksum_result json COMMENT "差异表结构信息,tdbctl checksum table 的结果",
		update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
		PRIMARY KEY (db,tbl)
	);`}
var ignoreDbs = []string{"sys", "information_schema", "mysql", "performance_schema", "infodba_schema", "test"}

const (
	// SchemaCheckOk TODO
	SchemaCheckOk = "OK"
)

type tableSchemaConsistencyCheck struct {
	ctldb *sqlx.DB
}

// Name TODO
func (c *tableSchemaConsistencyCheck) Name() string {
	return name
}

// TsccPendingExecuteTbl TODO
type TsccPendingExecuteTbl struct {
	Db         string    `db:"db"`
	Tbl        string    `db:"tbl"`
	CreateTime time.Time `db:"create_time"`
}

// SchemaCheckResult TODO
type SchemaCheckResult struct {
	ServerName string `json:"Server_name" db:"Server_name"`
	Db         string `json:"Db" db:"Db"`
	Table      string `json:"Table" db:"Table"`
	Status     string `json:"Status" db:"Status"`
	Message    string `json:"Message" db:"Message"`
}

// PrimaryCtlInfo TODO
type PrimaryCtlInfo struct {
	ServerName   string `db:"SERVER_NAME"`
	Host         string `db:"HOST"`
	Port         int    `db:"PORT"`
	IsThisServer int    `db:"IS_THIS_SERVER"`
}

// SchemaCheckResults TODO
type SchemaCheckResults []SchemaCheckResult

// CheckResult TODO
func (rs SchemaCheckResults) CheckResult() (inconsistencyItems []SchemaCheckResult) {
	for _, r := range rs {
		if strings.Compare(strings.ToUpper(r.Status), SchemaCheckOk) == 0 {
			continue
		}
		inconsistencyItems = append(inconsistencyItems, r)
	}
	return
}

// Run TODO
func (c *tableSchemaConsistencyCheck) Run() (msg string, err error) {
	slog.Info("start check cluster schema ....")
	defer c.ctldb.Close()
	// 如果不是主节点,无需运行
	var ps PrimaryCtlInfo
	err = c.ctldb.Get(&ps, "TDBCTL GET PRIMARY")
	if err != nil {
		slog.Error("execute TDBCTL GET PRIMARY  failed", slog.String("error", err.Error()))
		return
	}
	if ps.IsThisServer == 0 {
		slog.Info("is not primary tdbctl,no need to run")
		return "", nil
	}
	initSQLs := []string{"set tc_admin = 0;", "use infodba_schema;"}
	initSQLs = append(initSQLs, schemas...)
	for _, sqlStr := range initSQLs {
		if _, err = c.ctldb.Exec(sqlStr); err != nil {
			slog.Error("exec init sql:", sqlStr, "err: %v", sqlStr, err)
			return
		}
	}
	var count int
	err = c.ctldb.Get(&count, "select count(*) from tscc_pending_execute_tbl")
	if err != nil {
		slog.Error("query pending execute  check table failed", slog.String("error", err.Error()))
		return
	}
	if count < 10 {
		query, args, err := sqlx.In(
			"insert ignore into tscc_pending_execute_tbl select TABLE_SCHEMA,TABLE_NAME,CREATE_TIME from information_schema.tables where TABLE_SCHEMA not in (?) ", ignoreDbs)
		if err != nil {
			slog.Error("get check tables failed", slog.String("error", err.Error()))
			return msg, err
		}
		_, err = c.ctldb.Exec(c.ctldb.Rebind(query), args...)
		if err != nil {
			return msg, err
		}
	}
	finish := time.After(2 * time.Hour)
	errChan := make(chan struct{}, 1)
	stopsignal := 0
	var errCnt int
	for {
		select {
		case <-finish:
			stopsignal = 1
			// return "", nil
		case <-errChan:
			errCnt++
			if errCnt >= 100 {
				return "there are too many exceptions quit ", nil
			}
		default:
			if stopsignal == 1 {
				slog.Info("the run time has been used up,bye ~")
				return "", nil
			}
			var tblRows []TsccPendingExecuteTbl
			err = c.ctldb.Select(&tblRows, "select  * from  tscc_pending_execute_tbl limit 500")
			if err != nil {
				slog.Error("failed to query the table to be verified", slog.String("error", err.Error()))
				return
			}
			if len(tblRows) < 1 {
				return "done", nil
			}
			for _, tblRow := range tblRows {
				var result SchemaCheckResults
				c.ctldb.Exec("set tc_admin = 1;")
				err = c.ctldb.Select(&result, fmt.Sprintf("tdbctl check `%s`.`%s`;", tblRow.Db, tblRow.Tbl))
				if err != nil {
					errChan <- struct{}{}
					slog.Error("exec tdbctl check table failed", slog.String("error", err.Error()))
					continue
				}
				c.ctldb.Exec("set tc_admin = 0;")
				inconsistentItems := result.CheckResult()
				if err = c.atomUpdateCheckResult(tblRow.Db, tblRow.Tbl, inconsistentItems); err == nil {
					slog.Info("update checkresult ok")
				}
				time.Sleep(200 * time.Millisecond)
			}
		}
	}
}

func (c *tableSchemaConsistencyCheck) atomUpdateCheckResult(db, tbl string, inconsistentItems []SchemaCheckResult) (
	err error) {
	var status string
	status = SchemaCheckOk
	tx, err := c.ctldb.Begin()
	if err != nil {
		return err
	}
	checkResult := []byte("{}")
	if len(inconsistentItems) != 0 {
		checkResult, err = json.Marshal(inconsistentItems)
		if err != nil {
			slog.Error("json marshal failed %s", slog.String("error", err.Error()))
			return
		}
		status = ""
	}
	_, err = tx.Exec("replace into infodba_schema.tscc_schema_checksum values(?,?,?,?,?)", db, tbl, status,
		checkResult,
		time.Now())
	if err != nil {
		slog.Error("replace checksum record failed", slog.String("error", err.Error()))
		return
	}
	_, err = tx.Exec("delete from infodba_schema.tscc_pending_execute_tbl where db = ? and tbl = ? ", db, tbl)
	if err != nil {
		slog.Warn("delete pending tbl record failed", slog.String("error", err.Error()))
		return
	}
	if err = tx.Commit(); err != nil {
		slog.Warn("commit error: ", slog.String("error", err.Error()))
		return
	}
	return
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &tableSchemaConsistencyCheck{ctldb: cc.CtlDB}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
