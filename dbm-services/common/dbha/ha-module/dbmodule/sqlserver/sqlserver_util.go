/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"context"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/log"

	_ "github.com/denisenkom/go-mssqldb" // go-mssqldb TODO
	"github.com/jmoiron/sqlx"
)

// 执行切换sp的模板SQL
var (
	EXEC_SWITCH_SP_TMEP_SQL = `
		declare @msg varchar(1000)
		declare @exitcode int
		exec @exitcode = MONITOR.DBO.%s %s @msg output
		select @msg as msg, @exitcode as exitcode
		`
)

// execResult todo
type execResult struct {
	Msg      string `db:"msg"`
	ExitCode int    `db:"exitcode"`
}

// DbWorker TODO
type DbWorker struct {
	Dsn string
	Db  *sqlx.DB
}

// NewDbWorker 初始化SQLserver实例对象
func NewDbWorker(user string, pass string, server string, port int, timeout int) (dbw *DbWorker, err error) {
	dsn := fmt.Sprintf(
		"server=%s;port=%d;user id=%s;password=%s;database=Monitor;encrypt=disable;collation=utf8mb4_unicode_ci",
		server, port, user, pass,
	)
	dbw = &DbWorker{
		Dsn: dsn,
	}
	dbw.Db, err = sqlx.Open("mssql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	// check connect with timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()
	if err := dbw.Db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping context failed, err:%w", err)
	}
	return dbw, nil
}

// ExecMore 执行mssql命令
func (h *DbWorker) ExecMore(sqls []string) (rowsAffectedCount int64, err error) {
	var c int64
	sqlStr := strings.Join(sqls, ";")
	ret, err := h.Db.Exec(sqlStr)
	if err != nil {
		return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
	}
	if c, err = ret.RowsAffected(); err != nil {
		return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
	}
	rowsAffectedCount += c
	return
}

// queryxs 查询mssql命令
func (h *DbWorker) Queryxs(data interface{}, query string) error {
	if err := h.Db.Select(data, query); err != nil {
		return err
	}
	return nil
}

// exec_switch_sp todo
func ExecSwitchSP(db *DbWorker, spName string, paramStr string) error {
	cmd := fmt.Sprintf(EXEC_SWITCH_SP_TMEP_SQL, spName, paramStr)
	log.Logger.Info(cmd)
	var ret []execResult
	if err := db.Queryxs(&ret, cmd); err != nil {
		log.Logger.Error("exec %s failed", spName)
		return err
	}
	if ret[0].ExitCode != 1 {
		log.Logger.Error("exec %s failed", spName)
		return fmt.Errorf(ret[0].Msg)
	}
	log.Logger.Info(ret[0].Msg)
	return nil
}
