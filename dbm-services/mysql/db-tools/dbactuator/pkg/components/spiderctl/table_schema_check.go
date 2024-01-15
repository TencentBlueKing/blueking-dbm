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
	"context"
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// TableSchemaCheckComp TODO
type TableSchemaCheckComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       TableSchemaCheckParam
	tableSchemaCheckCtx
}

// TableSchemaCheckParam TODO
type TableSchemaCheckParam struct {
	Host         string        `json:"host" validate:"required,ip"`
	Port         int           `json:"port" validate:"required,lt=65536,gte=3306"`
	CheckObjects []CheckObject `json:"check_objects"`
	// 检查所有非系统库表
	CheckAll               bool `json:"check_all"`
	InconsistencyThrowsErr bool `json:"inconsistency_throws_err"`
}

// CheckObject TODO
type CheckObject struct {
	DbName string   `json:"dbname"`
	Tables []string `json:"tables"`
}
type tableSchemaCheckCtx struct {
	tdbCtlConn *native.TdbctlDbWork
	version    string
}

// TsccSchemaChecksum TODO
var TsccSchemaChecksum = `CREATE TABLE if not exists infodba_schema.tscc_schema_checksum(
	db char(64) NOT NULL,
	tbl char(64) NOT NULL,
	status char(32) NOT NULL DEFAULT "" COMMENT "检查结果,一致:ok,不一致:inconsistent",
	checksum_result json COMMENT "差异表结构信息,tdbctl checksum table 的结果",
	update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (db,tbl)
);`

// Example useage
func (r *TableSchemaCheckComp) Example() interface{} {
	return &TableSchemaCheckComp{
		Params: TableSchemaCheckParam{
			Host:     "127.0.0.1",
			Port:     26000,
			CheckAll: true,
			CheckObjects: []CheckObject{
				{
					DbName: "test",
					Tables: []string{"t1", "t2"},
				},
			},
		},
	}
}

// Init TODO
func (r *TableSchemaCheckComp) Init() (err error) {
	var conn *native.DbWorker
	// connection central control
	conn, err = native.InsObject{
		Host: r.Params.Host,
		Port: r.Params.Port,
		User: r.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect tdbctl error: %v", err)
		return err
	}
	r.tdbCtlConn = &native.TdbctlDbWork{DbWorker: *conn}
	// init checksum table schema
	if _, err = r.tdbCtlConn.ExecMore([]string{"set tc_admin = 0;", "use infodba_schema;",
		TsccSchemaChecksum}); err != nil {
		logger.Error("init tscc_schema_checksum error: %v", err)
		return
	}
	r.version, err = r.tdbCtlConn.SelectVersion()
	if err != nil {
		logger.Error("get version error: %v", err)
		return
	}
	return err
}

// Run Command Run
func (r *TableSchemaCheckComp) Run() (err error) {
	switch {
	case r.Params.CheckAll:
		err = r.checkAll()
	default:
		err = r.checkSpecial()
	}
	return
}

// checkSpecial 校验指定对象
func (r *TableSchemaCheckComp) checkSpecial() (err error) {
	for _, checkObject := range r.Params.CheckObjects {
		if len(checkObject.Tables) <= 0 {
			return r.atomUpdateDbTables(checkObject.DbName)
		}
		if err = r.atomUpdateTables(checkObject.DbName, checkObject.Tables); err != nil {
			logger.Error("check %s tables failed: %v", checkObject.DbName, err)
			return err
		}
	}
	return nil
}

func (r *TableSchemaCheckComp) checkAll() (err error) {
	dbs, err := r.tdbCtlConn.ShowDatabases()
	if err != nil {
		logger.Error("exec show database failed: %s", err.Error())
		return err
	}
	for _, db := range util.FilterOutStringSlice(dbs, cmutil.GetMysqlSystemDatabases(r.version)) {
		if err = r.atomUpdateDbTables(db); err != nil {
			return err
		}
	}
	return nil
}

func (r *TableSchemaCheckComp) atomUpdateDbTables(dbName string) (err error) {
	xconn, err := r.tdbCtlConn.GetSqlxDb().Connx(context.Background())
	if err != nil {
		return err
	}
	defer xconn.Close()
	xconn.ExecContext(context.Background(), "set tc_admin = 1;")
	var result native.SchemaCheckResults
	if err = xconn.SelectContext(context.Background(), &result, fmt.Sprintf("TDBCTL CHECK DATABASE `%s`;",
		dbName)); err != nil {
		logger.Error("check table schema: %s", err.Error())
		return err
	}
	inconsistentItems := result.CheckResult()
	if len(inconsistentItems) <= 0 {
		logger.Info("完成校验%s库,暂未发现差异表", dbName)
		return nil
	}
	inconsistentMap := make(map[string]native.SchemaCheckResults)
	for _, item := range inconsistentItems {
		inconsistentMap[item.Table] = append(inconsistentMap[item.Table], item)
	}
	for tbName, results := range inconsistentMap {
		if err = r.atomUpdateCheckResult(dbName, tbName, results); err == nil {
			logger.Info("update %s.%s checkresult ok", dbName, tbName)
		}
	}
	if r.Params.InconsistencyThrowsErr {
		for tbName, results := range inconsistentMap {
			logger.Warn("the table %s there is an inconsistency in the table schema", tbName)
			logger.Warn("details of the difference:\n")
			for _, diffItem := range results {
				logger.Warn("diff item %v\n", diffItem)
			}
		}
		return fmt.Errorf("校验完成,存在表结构不一致的情况")
	}
	return nil
}

func (r *TableSchemaCheckComp) atomUpdateTables(dbName string, tables []string) (err error) {
	if len(tables) <= 0 {
		return nil
	}
	xconn, err := r.tdbCtlConn.GetSqlxDb().Connx(context.Background())
	if err != nil {
		return err
	}
	defer xconn.Close()
	xconn.ExecContext(context.Background(), "set tc_admin = 1;")
	for _, table := range tables {
		// check table schema
		var result native.SchemaCheckResults
		if err = xconn.SelectContext(context.Background(), &result, fmt.Sprintf("tdbctl check `%s`.`%s`;", dbName,
			table)); err != nil {
			logger.Error("check table schema error: %s", err.Error())
			return err
		}
		if err = r.atomUpdateCheckResult(dbName, table, result.CheckResult()); err == nil {
			logger.Info("update %s.%s checkresult ok", dbName, table)
		}
	}
	return nil
}

func (r *TableSchemaCheckComp) atomUpdateCheckResult(db, tbl string, inconsistentItems []native.SchemaCheckResult) (
	err error) {
	r.tdbCtlConn.Exec("set tc_admin=0;")
	status := native.SchemaCheckOk
	checkResult := []byte("{}")
	if len(inconsistentItems) > 0 {
		logger.Warn("tabel %s.%s has inconsistent items", db, tbl)
		status = ""
		checkResult, err = json.Marshal(inconsistentItems)
		if err != nil {
			logger.Error("json marshal failed %s", err.Error())
			return
		}
	}
	if _, err = r.tdbCtlConn.Exec("replace into infodba_schema.tscc_schema_checksum values(?,?,?,?,?)", db,
		tbl, status,
		checkResult,
		time.Now()); err != nil {
		logger.Error("replace checksum record failed", err)
		return
	}
	return
}
